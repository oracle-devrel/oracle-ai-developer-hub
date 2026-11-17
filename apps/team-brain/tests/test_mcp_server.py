"""MCP server exercised over REAL protocol clients — not imports.

Proves: primitives return raw evidence rows (not answers), search_code is
code-only, restricted/domain-scoped content is absent for a non-member
identity, whoami reflects the resolved token, and an invalid token is denied
inside the database (fail closed).

Transports verified over the real protocol in this file:
  * stdio      — every functional test below. A prior concern that an
    in-process stdio client hangs on Windows with no output did NOT
    reproduce here (verified manually before writing these tests); every
    call is still wrapped in `asyncio.wait_for(..., 60)` as a hard backstop.
  * streamable-http — one dedicated smoke test (`test_streamable_http_whoami`)
    that spawns `python -m team_brain.mcp_server` with
    `TEAM_BRAIN_TRANSPORT=streamable-http` on a free port and connects with
    `mcp.client.streamable_http.streamablehttp_client`, sending the token as
    `Authorization: Bearer <token>`.

The MCP subprocess runs with the DEFAULT retrieval backend (the LangChain
legs). An earlier version of this suite had to force `RETRIEVAL_BACKEND=sql`
because the first `search` over stdio hung: the LangChain package (and
numpy's native extension) was being imported lazily inside the tool call and
deadlocked in `create_module` on Windows. The server now imports the legs
eagerly at startup (see team_brain/langchain_legs.py), which is what this
module exercises.
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from typing import Any

import pytest

from team_brain.config import REPO_DIR
from team_brain.db import DocumentDB
from team_brain.ingest import ingest

pytestmark = pytest.mark.asyncio

_TIMEOUT = 60


async def test_shipped_stdio_config_resolves_jeff(tokens: dict[str, str]) -> None:
    """Exercise the portable project config that a fresh checkout actually ships."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    config = json.loads((REPO_DIR / ".mcp.json.example").read_text(encoding="utf-8"))
    server = config["mcpServers"]["team-brain"]
    assert server["env"]["TEAM_BRAIN_TOKEN"] == tokens["jeff"]
    params = StdioServerParameters(
        command=server["command"],
        args=server["args"],
        env={**_server_env(None), **server["env"]},
        cwd=str(REPO_DIR),
    )

    async def run() -> None:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("whoami", {})
                assert not result.isError
                assert _rows_dict(result)["username"] == "jeff"

    await asyncio.wait_for(run(), timeout=_TIMEOUT)


def _rows(result: Any) -> list[dict[str, Any]]:
    sc = getattr(result, "structuredContent", None)
    if isinstance(sc, dict) and "result" in sc:
        return sc["result"]
    # Fallback: the first text block is the JSON-serialized return value.
    return json.loads(result.content[0].text)


def _rows_dict(result: Any) -> dict[str, Any]:
    """Extract a dict return value (e.g. whoami) from a tool result."""
    sc = getattr(result, "structuredContent", None)
    if isinstance(sc, dict):
        return sc["result"] if "result" in sc and isinstance(sc["result"], dict) else sc
    data: dict[str, Any] = json.loads(result.content[0].text)
    return data


def _server_env(token: str | None) -> dict[str, str]:
    env = dict(os.environ)  # carries ORACLE_USER=TEAMBRAIN_TEST + blanked LLM keys
    env.setdefault("ORACLE_USER", "TEAMBRAIN_TEST")
    env.pop("RETRIEVAL_BACKEND", None)  # the default (LangChain) legs
    if token is not None:
        env["TEAM_BRAIN_TOKEN"] = token
    else:
        env.pop("TEAM_BRAIN_TOKEN", None)
    return env


def _server_params(token: str | None) -> Any:
    from mcp import StdioServerParameters

    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "team_brain.mcp_server"],
        env=_server_env(token),
        cwd=str(REPO_DIR),
    )


async def _call(tool: str, args: dict[str, Any], token: str | None = None) -> list[dict[str, Any]]:
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client

    async def _run() -> list[dict[str, Any]]:
        async with stdio_client(_server_params(token)) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool, args)
                return _rows(result)

    return await asyncio.wait_for(_run(), timeout=_TIMEOUT)


async def _call_raw(tool: str, args: dict[str, Any], token: str | None = None) -> Any:
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client

    async def _run() -> Any:
        async with stdio_client(_server_params(token)) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.call_tool(tool, args)

    return await asyncio.wait_for(_run(), timeout=_TIMEOUT)


async def test_search_returns_evidence_rows(
    db: DocumentDB, seed_docs: str, slack_export: str
) -> None:
    ingest("markdown", [seed_docs])
    ingest("slack", ["--export", slack_export])

    rows = await _call("search", {"query": "how do we deploy billing"})
    assert rows and isinstance(rows, list)
    row = rows[0]
    # raw evidence row, not a synthesized answer
    assert {"source", "title", "snippet", "score"} <= set(row)
    assert "answer" not in row


async def test_search_code_is_code_only(db: DocumentDB) -> None:
    from datetime import UTC, datetime

    from team_brain.schema import Document

    db.upsert_document(
        Document(
            "github",
            "code:app.py:0",
            "app.py",
            "def refund(): pass",
            datetime.now(UTC),
            metadata={"kind": "code"},
        )
    )
    db.upsert_document(
        Document(
            "markdown", "note", "Refund policy", "our refund policy is 30 days", datetime.now(UTC)
        )
    )
    db.commit()

    rows = await _call("search_code", {"query": "refund"})
    assert rows
    assert all(r["source"] == "github" for r in rows)


async def test_who_knows_returns_authors(db: DocumentDB, seed_docs: str, slack_export: str) -> None:
    ingest("slack", ["--export", slack_export])
    rows = await _call("who_knows", {"topic": "onnxruntime pin"})
    assert rows
    assert "author" in rows[0]


async def test_mcp_does_not_leak_restricted(db: DocumentDB, slack_export: str) -> None:
    ingest("slack", ["--export", slack_export])  # includes private security thread (acl=[bob])
    rows = await _call("search", {"query": "leaked password prod outage hunter2"})
    # server identity is anonymous (not a member) → secret must be absent
    assert all("hunter2" not in r["snippet"] for r in rows)
    assert all(r.get("title") != "Postmortem" for r in rows)


async def test_mcp_token_identity_enforces_domain(
    db: DocumentDB, tokens: dict[str, str], domain_slack_export: str
) -> None:
    ingest("slack", ["--export", domain_slack_export])  # ops / marketing / sales channels
    q = {"query": "enterprise discount ceiling VP approval deal desk sales"}

    # Jeff's token grants ops only — the sales policy must be absent.
    jeff_rows = await _call("search", q, token=tokens["jeff"])
    assert all("deal desk" not in r["snippet"].lower() for r in jeff_rows)
    assert all(r["source"] != "slack" or "sales-team" not in r.get("url", "") for r in jeff_rows)

    # Brian's token is all-domains — the sales policy is visible.
    brian_rows = await _call("search", q, token=tokens["brian"])
    assert any("sales-team" in r.get("url", "") for r in brian_rows)


async def test_mcp_whoami_reflects_token(db: DocumentDB, tokens: dict[str, str]) -> None:
    me = await _call_raw("whoami", {}, token=tokens["jeff"])
    payload = _rows_dict(me)
    assert payload["username"] == "jeff"
    assert payload["domains"] == ["ops"]


async def test_mcp_invalid_token_is_denied(db: DocumentDB, tokens: dict[str, str]) -> None:
    result = await _call_raw("search", {"query": "anything"}, token="tb_not_a_real_token")
    # A supplied-but-invalid token must fail closed: the tool errors, no rows.
    assert result.isError
    text = result.content[0].text if result.content else ""
    assert "denied" in text.lower() or "unknown token" in text.lower()


# --- streamable-http: one dedicated transport smoke test --------------------


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


async def test_streamable_http_whoami(tokens: dict[str, str]) -> None:
    import httpx
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    port = _free_port()
    env = _server_env(None)
    env["TEAM_BRAIN_TRANSPORT"] = "streamable-http"
    env["TEAMBRAIN_MCP_PORT"] = str(port)
    proc = subprocess.Popen(
        [sys.executable, "-m", "team_brain.mcp_server"],
        cwd=str(REPO_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        url = f"http://127.0.0.1:{port}/mcp"
        headers = {"Authorization": f"Bearer {tokens['jeff']}"}

        async def _try_once() -> dict[str, Any]:
            async with httpx.AsyncClient(headers=headers) as http_client:
                async with streamable_http_client(url, http_client=http_client) as (
                    read,
                    write,
                    _get_sid,
                ):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool("whoami", {})
                        return _rows_dict(result)

        deadline = time.monotonic() + 20
        last_exc: Exception | None = None
        payload: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            try:
                payload = await asyncio.wait_for(_try_once(), timeout=10)
                break
            except Exception as exc:  # noqa: BLE001 - server still starting up
                last_exc = exc
                await asyncio.sleep(0.5)
        if payload is None:
            pytest.fail(f"streamable-http server never became ready: {last_exc}")
        assert payload["username"] == "jeff"
        assert payload["domains"] == ["ops"]
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


async def test_get_document_returns_full_text_and_respects_policy(
    db: DocumentDB, tokens: dict[str, str], domain_slack_export: str
) -> None:
    ingest("slack", ["--export", domain_slack_export])
    jeff = tokens["jeff"]
    rows = await _call("search", {"query": "batch cluster autoscaler"}, token=jeff)
    assert rows, "jeff should find the ops thread"
    row_id = rows[0]["id"]
    full = _rows_dict(await _call_raw("get_document", {"row_id": row_id}, token=jeff))
    assert full["found"] is True
    assert len(full["text"]) > len(rows[0]["snippet"]) - 3, "full text, not the snippet"
    # The same row by id, as sales: not found (the policy hides it, indistinguishably)
    hidden = _rows_dict(await _call_raw("get_document", {"row_id": row_id}, token=tokens["sam"]))
    assert hidden["found"] is False


async def test_streamable_http_no_header_is_anonymous(tokens: dict[str, str]) -> None:
    """The HTTP transport never inherits the process token: no bearer header -> anonymous."""
    import httpx
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    port = _free_port()
    env = _server_env(tokens["brian"])  # exported for stdio; must be ignored over HTTP
    env["TEAM_BRAIN_TRANSPORT"] = "streamable-http"
    env["TEAMBRAIN_MCP_PORT"] = str(port)
    proc = subprocess.Popen(
        [sys.executable, "-m", "team_brain.mcp_server"],
        cwd=str(REPO_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        url = f"http://127.0.0.1:{port}/mcp"

        async def _try_once() -> dict[str, Any]:
            async with httpx.AsyncClient() as http_client:
                async with streamable_http_client(url, http_client=http_client) as (
                    read,
                    write,
                    _get_sid,
                ):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        return _rows_dict(await session.call_tool("whoami", {}))

        deadline = time.monotonic() + 20
        last_exc: Exception | None = None
        payload: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            try:
                payload = await asyncio.wait_for(_try_once(), timeout=10)
                break
            except Exception as exc:  # noqa: BLE001 - server still starting up
                last_exc = exc
                await asyncio.sleep(0.5)
        if payload is None:
            pytest.fail(f"streamable-http server never became ready: {last_exc}")
        assert payload["username"] == "anonymous"
        assert payload["domains"] == []
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
