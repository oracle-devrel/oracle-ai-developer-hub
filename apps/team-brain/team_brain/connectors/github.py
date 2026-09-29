"""GitHub connector — README, issues, PRs, and code chunks.

Built on httpx against the GitHub REST API (so it's deterministically mockable
in tests). Naive assumption people make: "grep is enough for code." It isn't —
developers search for behavior without knowing the function name, so we embed
code too, chunked by top-level definition.

Cutbacks vs. a production connector (called out for the workshop): issues/PRs
and code files are capped, and code is chunked with a language-agnostic splitter
rather than a real parser (a production connector would use one).
"""

from __future__ import annotations

import base64
import re
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

import httpx

from team_brain.config import GITHUB_TOKEN
from team_brain.schema import Document

API = "https://api.github.com"
_CODE_EXTS = {".py", ".ts", ".js", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb"}
_MAX_ISSUES = 200
_MAX_CODE_FILES = 30
_DEF = re.compile(r"^(def |class |func |function |export |public |private )", re.MULTILINE)


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(UTC)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _chunk_code(text: str, max_chars: int = 1500) -> list[str]:
    """Split on top-level definitions; fall back to fixed windows for long blocks."""
    lines = text.splitlines(keepends=True)
    blocks: list[str] = []
    current: list[str] = []
    for line in lines:
        if _DEF.match(line) and current:
            blocks.append("".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append("".join(current))

    chunks: list[str] = []
    for block in blocks:
        if len(block) <= max_chars:
            if block.strip():
                chunks.append(block)
        else:
            for i in range(0, len(block), max_chars):
                piece = block[i : i + max_chars]
                if piece.strip():
                    chunks.append(piece)
    return chunks


class GitHubConnector:
    source = "github"

    def __init__(
        self,
        repo: str,
        project: str = "default",
        visibility: str = "public",
        acl: list[str] | None = None,
        domains: list[str] | None = None,
    ) -> None:
        if "/" not in repo:
            raise ValueError("repo must be 'owner/name'")
        self.repo = repo
        self.project = project
        self.visibility = visibility
        self.acl = acl or []
        self.domains = domains or []
        self._repo_private = True  # fail closed until GitHub confirms visibility

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json"}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
        return headers

    def fetch(self) -> Iterable[Document]:
        with httpx.Client(base_url=API, headers=self._headers(), timeout=30.0) as client:
            meta = self._get(client, f"/repos/{self.repo}")
            if not isinstance(meta, dict) or not isinstance(meta.get("private"), bool):
                raise ValueError("GitHub repository response has no valid visibility flag")
            self._repo_private = meta["private"]
            default_branch = meta.get("default_branch", "main")
            repo_dt = _parse_dt(meta.get("pushed_at"))

            yield from self._readme(client, repo_dt)
            yield from self._issues(client)
            yield from self._code(client, default_branch, repo_dt)

    def _get(
        self, client: httpx.Client, path: str, *, optional: bool = False, **kwargs: Any
    ) -> Any:
        resp = client.get(path, **kwargs)
        # Only an absent README is a valid empty result. Authentication failures,
        # rate limits, and missing required resources are incomplete snapshots.
        if optional and resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def _doc(self, external_id: str, title: str, body: str, **kw: object) -> Document:
        return Document(
            source=self.source,
            external_id=external_id,
            title=title,
            body=body,
            project=self.project,
            visibility="restricted" if self._repo_private else self.visibility,
            acl=self.acl,
            domains=list(self.domains),
            **kw,  # type: ignore[arg-type]
        )

    def _readme(self, client: httpx.Client, repo_dt: datetime) -> Iterable[Document]:
        data = self._get(client, f"/repos/{self.repo}/readme", optional=True)
        if data is None:
            return
        if not isinstance(data, dict) or "content" not in data:
            raise ValueError("GitHub README response is incomplete")
        content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
        yield self._doc(
            "readme",
            f"{self.repo} README",
            content,
            url=data.get("html_url", ""),
            created_at=repo_dt,
            metadata={"kind": "doc"},
        )

    def _issues(self, client: httpx.Client) -> Iterable[Document]:
        data = self._get(
            client,
            f"/repos/{self.repo}/issues",
            params={"state": "all", "per_page": 100},
        )
        if not isinstance(data, list):
            raise ValueError("GitHub issues response is incomplete")
        for item in data[:_MAX_ISSUES]:
            is_pr = "pull_request" in item
            kind = "pr" if is_pr else "issue"
            number = item.get("number")
            yield self._doc(
                f"{kind}:{number}",
                f"[{kind}] {item.get('title', '')}",
                item.get("body") or "",
                url=item.get("html_url", ""),
                author=(item.get("user") or {}).get("login", ""),
                created_at=_parse_dt(item.get("created_at")),
                metadata={"kind": kind, "number": number, "state": item.get("state")},
            )

    def _code(self, client: httpx.Client, branch: str, repo_dt: datetime) -> Iterable[Document]:
        tree = self._get(
            client, f"/repos/{self.repo}/git/trees/{branch}", params={"recursive": "1"}
        )
        if not isinstance(tree, dict) or not isinstance(tree.get("tree"), list):
            raise ValueError("GitHub tree response is incomplete")
        if tree.get("truncated"):
            raise ValueError("GitHub tree was truncated; refusing an incomplete snapshot")
        files = [
            n
            for n in tree.get("tree", [])
            if n.get("type") == "blob" and any(n.get("path", "").endswith(e) for e in _CODE_EXTS)
        ][:_MAX_CODE_FILES]
        for node in files:
            path = node["path"]
            blob = self._get(client, f"/repos/{self.repo}/contents/{path}", params={"ref": branch})
            if not isinstance(blob, dict) or "content" not in blob:
                raise ValueError(f"GitHub content response is incomplete for {path}")
            text = base64.b64decode(blob["content"]).decode("utf-8", errors="replace")
            for i, chunk in enumerate(_chunk_code(text)):
                yield self._doc(
                    f"code:{path}:{i}",
                    f"{path} (part {i + 1})",
                    chunk,
                    url=blob.get("html_url", ""),
                    created_at=repo_dt,
                    metadata={"kind": "code", "path": path, "part": i},
                )
