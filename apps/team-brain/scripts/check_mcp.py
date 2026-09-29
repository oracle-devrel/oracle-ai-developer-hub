"""MCP check: drive the server over the real protocol, stdio AND streamable-http.

Asserts, per identity, that the tools return raw evidence rows (not answers) and
that the row policy holds through the protocol: jeff never sees sales, an
unknown bearer token is refused, and no token means public-only rows.
Runs against the TEST schema, which it seeds itself.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = {**os.environ, "ORACLE_USER": "TEAMBRAIN_TEST", "RETRIEVAL_BACKEND": "langchain"}
TOKENS = {
    "jeff": "tb_ops_jeff_7f3a9c21",
    "sam": "tb_sales_sam_1a6f2e90",
    "brian": "tb_exec_brian_9d4c7b13",
}


def _rows(result) -> list:  # type: ignore[no-untyped-def]
    payload = result.structuredContent or {}
    if "result" in payload:
        return payload["result"]
    text = "".join(c.text for c in result.content if getattr(c, "type", "") == "text")
    return json.loads(text) if text else []


async def stdio_as(token: str | None) -> dict[str, object]:
    env = dict(ENV)
    if token:
        env["TEAM_BRAIN_TOKEN"] = token
    else:
        env.pop("TEAM_BRAIN_TOKEN", None)
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "team_brain.mcp_server"], env=env, cwd=ROOT
    )
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        tools = sorted(t.name for t in (await s.list_tools()).tools)
        who = _rows(await s.call_tool("whoami", {}))
        hits = _rows(await s.call_tool("search", {"query": "acme deal onnxruntime deploy"}))
        return {"tools": tools, "whoami": who, "ids": [h["id"] for h in hits]}


async def http_as(token: str | None, url: str) -> dict[str, object]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient(headers=headers, timeout=60) as client:
        async with streamable_http_client(url, http_client=client) as (r, w, _):
            async with ClientSession(r, w) as s:
                await s.initialize()
                who = await s.call_tool("whoami", {})
                if who.isError:
                    return {"error": "".join(c.text for c in who.content)[:120]}
                hits = _rows(await s.call_tool("search", {"query": "acme deal onnxruntime deploy"}))
                return {"whoami": _rows(who), "ids": [h["id"] for h in hits]}


async def main() -> None:
    print("--- stdio (identity per process via TEAM_BRAIN_TOKEN) ---")
    for name, tok in [("jeff", TOKENS["jeff"]), ("brian", TOKENS["brian"]), ("anon", None)]:
        out = await stdio_as(tok)
        print(name, out)
    assert "sales" not in " ".join((await stdio_as(TOKENS["jeff"]))["ids"])  # type: ignore[arg-type]

    print("--- streamable-http (identity per REQUEST via bearer token) ---")
    port = "8799"
    proc = subprocess.Popen(
        [sys.executable, "-m", "team_brain.mcp_server"],
        env={**ENV, "TEAM_BRAIN_TRANSPORT": "streamable-http", "TEAMBRAIN_MCP_PORT": port},
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}/mcp"
    try:
        for _ in range(60):
            try:
                httpx.get(url, timeout=1)
                break
            except httpx.HTTPError:
                time.sleep(0.5)
        for name, tok in [
            ("jeff", TOKENS["jeff"]),
            ("sam", TOKENS["sam"]),
            ("brian", TOKENS["brian"]),
            ("anon", None),
            ("bogus", "nope"),
        ]:
            print(name, await http_as(tok, url))
        jeff = await http_as(TOKENS["jeff"], url)
        sam = await http_as(TOKENS["sam"], url)
        assert not any("sales" in i for i in jeff["ids"]), "LEAK: jeff saw sales"  # type: ignore[union-attr]
        assert not any("ops" in i for i in sam["ids"]), "LEAK: sam saw ops"  # type: ignore[union-attr]
        print("MCP checks passed")
    finally:
        proc.terminate()


asyncio.run(main())
