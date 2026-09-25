"""Slack connector — threads, with enrichment and permission mapping.

Two things make this the centerpiece connector:

  1. Enrichment-before-embedding. A raw thread is mostly noise ("+1", "shipping
     it"). We distill each thread to structured knowledge and embed THAT, so
     retrieval finds the resolution, not the chatter. (See enrich.py.)

  2. Permissions from the source. A private channel becomes a `restricted`
     Document whose `acl` is the channel's members. A public channel is
     `public`. This is what stops the knowledge base from being a data-leak.

Runs in two modes: an offline export file (deterministic, no creds — used by the
workshop + tests) and live via SLACK_BOT_TOKEN.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from team_brain.config import SLACK_BOT_TOKEN
from team_brain.enrich import enrich_thread
from team_brain.schema import VISIBILITY_PUBLIC, VISIBILITY_RESTRICTED, Document

_MAX_THREADS_PER_CHANNEL = 200


def _ts_to_dt(ts: str) -> datetime:
    try:
        return datetime.fromtimestamp(float(ts), tz=UTC)
    except (ValueError, OSError):
        return datetime.now(UTC)


class SlackConnector:
    source = "slack"

    def __init__(
        self,
        export_path: str | None = None,
        project: str = "default",
        principal_map: dict[str, str] | None = None,
    ) -> None:
        self.export_path = export_path
        self.project = project
        self.principal_map = self._validate_principal_map(
            {} if principal_map is None else principal_map
        )
        self._explicit_principal_map = principal_map is not None

    @staticmethod
    def _validate_principal_map(value: object) -> dict[str, str]:
        if not isinstance(value, dict) or any(
            not isinstance(k, str) or not k.strip() or not isinstance(v, str) or not v.strip()
            for k, v in value.items()
        ):
            raise ValueError("principal_map must map nonempty Slack user IDs to principal names")
        return dict(value)

    def fetch(self) -> Iterable[Document]:
        if self.export_path:
            yield from self._fetch_export(Path(self.export_path))
        else:
            yield from self._fetch_live()

    # --- shared thread → Document -------------------------------------------
    def _thread_document(
        self,
        channel_name: str,
        channel_id: str,
        is_private: bool,
        members: list[str],
        thread_ts: str,
        messages: list[dict[str, Any]],
        user_names: dict[str, str],
        domains: list[str] | None = None,
    ) -> Document | None:
        if not messages:
            return None
        lines = []
        for m in messages:
            who = user_names.get(m.get("user", ""), m.get("user", "unknown"))
            lines.append(f"{who}: {m.get('text', '')}")
        body = "\n".join(lines)
        first = messages[0]
        author = user_names.get(first.get("user", ""), first.get("user", ""))

        enriched = enrich_thread(body)
        title = (enriched or {}).get("question") or (first.get("text", "")[:120] or "thread")

        visibility = VISIBILITY_RESTRICTED if is_private else VISIBILITY_PUBLIC
        # Names are display text only. Only an operator-supplied ID mapping
        # may translate a source identity into a Team Brain principal.
        acl = [self.principal_map.get(u, u) for u in members] if is_private else []

        return Document(
            source=self.source,
            external_id=f"{channel_id}:{thread_ts}",
            title=title,
            body=body,
            url=f"slack://{channel_name}/{thread_ts}",
            author=author,
            created_at=_ts_to_dt(thread_ts),
            project=self.project,
            visibility=visibility,
            acl=acl,
            domains=list(domains or []),
            metadata={
                "kind": "thread",
                "channel": channel_name,
                "is_private": is_private,
                "domains": list(domains or []),
                "_enriched": enriched,
            },
        )

    # --- offline export -----------------------------------------------------
    def _fetch_export(self, path: Path) -> Iterable[Document]:
        if not path.exists():
            raise FileNotFoundError(f"slack export not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not self._explicit_principal_map:
            self.principal_map = self._validate_principal_map(data.get("principal_map", {}))
        user_names: dict[str, str] = data.get("users", {})
        for ch in data.get("channels", []):
            for thread in ch.get("threads", [])[:_MAX_THREADS_PER_CHANNEL]:
                doc = self._thread_document(
                    channel_name=ch.get("name", ch.get("id", "")),
                    channel_id=ch.get("id", ch.get("name", "")),
                    is_private=bool(ch.get("is_private", False)),
                    members=ch.get("members", []),
                    thread_ts=thread.get("thread_ts", thread.get("ts", "")),
                    messages=thread.get("messages", []),
                    user_names=user_names,
                    domains=ch.get("domains", []),
                )
                if doc:
                    yield doc

    # --- live ---------------------------------------------------------------
    def _fetch_live(self) -> Iterable[Document]:  # pragma: no cover - needs a live workspace
        if not SLACK_BOT_TOKEN:
            raise ValueError(
                "SlackConnector live mode needs SLACK_BOT_TOKEN "
                "(or pass --export <file> for offline mode)"
            )
        from slack_sdk import WebClient

        client = WebClient(token=SLACK_BOT_TOKEN)
        user_names = self._live_user_names(client)

        cursor = None
        channels: list[dict[str, Any]] = []
        while True:
            resp: Any = client.conversations_list(
                types="public_channel,private_channel", limit=200, cursor=cursor
            )
            channels.extend(resp["channels"])
            cursor = resp.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        for ch in channels:
            members: list[str] = []
            if ch.get("is_private"):
                members = client.conversations_members(channel=ch["id"]).get("members", [])
            history: Any = client.conversations_history(
                channel=ch["id"], limit=_MAX_THREADS_PER_CHANNEL
            )
            for parent in history.get("messages", []):
                thread_ts = parent.get("thread_ts", parent.get("ts"))
                replies = client.conversations_replies(channel=ch["id"], ts=thread_ts)
                doc = self._thread_document(
                    channel_name=ch.get("name", ch["id"]),
                    channel_id=ch["id"],
                    is_private=bool(ch.get("is_private")),
                    members=members,
                    thread_ts=thread_ts,
                    messages=replies.get("messages", []),
                    user_names=user_names,
                )
                if doc:
                    yield doc

    @staticmethod
    def _live_user_names(
        client: Any,
    ) -> dict[str, str]:  # pragma: no cover - needs a live workspace
        names: dict[str, str] = {}
        for m in client.users_list().get("members", []):
            names[m["id"]] = m.get("real_name") or m.get("name", m["id"])
        return names
