# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any

import oracledb
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_request
from mcp.types import CallToolResult, TextContent

from oracleagentmemory.core import OracleAgentMemory
from oracleagentmemory.core.dbschemapolicy import SchemaPolicy
from oracleagentmemory.core.embedders.embedder import Embedder
from oracleagentmemory.core.llms.llm import Llm

try:
    from .session_token import MAX_ID_CHARS, MIN_SECRET_BYTES, decode_session_token
except ImportError:  # Support running this tutorial file directly.
    from session_token import (  # type: ignore[no-redef]
        MAX_ID_CHARS,
        MIN_SECRET_BYTES,
        decode_session_token,
    )

load_dotenv(Path(__file__).parent / ".env")


JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET must be set before starting the MCP server. Generate one with "
        "'openssl rand -hex 32' before creating OAM_MCP_TOKEN, then configure the "
        "same value for the server."
    )
if len(JWT_SECRET.encode("utf-8")) < MIN_SECRET_BYTES:
    raise RuntimeError(f"JWT_SECRET must contain at least {MIN_SECRET_BYTES} bytes")
# Keep this tutorial server reachable only from the same machine.
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
# Namespace derived thread IDs so they cannot collide with IDs from other integrations.
THREAD_ID_DOMAIN = b"oracle-ai-agent-memory-codex"
MAX_TOOL_TEXT_CHARS = 256 * 1024
MAX_SEARCH_QUERY_CHARS = 16 * 1024
MAX_SEARCH_RESULTS = 100
MAX_CAPTURED_MESSAGES = 100


def _storage_thread_id(user_id: str, agent_id: str, external_thread_id: str) -> str:
    serialized_scope = json.dumps(
        [user_id, agent_id, external_thread_id],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(THREAD_ID_DOMAIN + serialized_scope).hexdigest()
    return f"codex-{digest}"


def _to_storage_scope(user_info: dict[str, Any]) -> dict[str, Any]:
    storage_scope = dict(user_info)
    external_thread_id = storage_scope.get("thread_id")
    if external_thread_id:
        storage_scope["thread_id"] = _storage_thread_id(
            storage_scope["user_id"],
            storage_scope["agent_id"],
            external_thread_id,
        )
    return storage_scope


def _resolve_external_thread_id(request_thread_id: str, token_thread_id: str | None) -> str:
    if not isinstance(request_thread_id, str):
        raise ValueError("Missing thread id")
    request_thread_id = request_thread_id.strip()
    if len(request_thread_id) > MAX_ID_CHARS:
        raise ValueError("Invalid thread id")

    if token_thread_id:
        # compare_digest accepts arbitrary bytes but only ASCII strings. UTF-8
        # keeps valid Unicode identifiers usable without weakening comparison.
        if request_thread_id and not hmac.compare_digest(
            request_thread_id.encode("utf-8"), token_thread_id.encode("utf-8")
        ):
            raise PermissionError("Thread access denied")
        return token_thread_id

    if not request_thread_id:
        raise ValueError("Missing thread id")
    return request_thread_id


def _get_or_create_scoped_thread(
    memory: OracleAgentMemory,
    user_info: dict[str, Any],
    external_thread_id: str,
) -> Any:
    storage_thread_id = _storage_thread_id(
        user_info["user_id"],
        user_info["agent_id"],
        external_thread_id,
    )
    try:
        thread = memory.get_thread(storage_thread_id)
    except KeyError:
        return memory.create_thread(
            thread_id=storage_thread_id,
            user_id=user_info["user_id"],
            agent_id=user_info["agent_id"],
        )

    if thread.user_id != user_info["user_id"] or thread.agent_id != user_info["agent_id"]:
        raise PermissionError("Thread access denied")
    return thread


def _get_user_info() -> dict[str, Any]:
    request = get_http_request()
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise ValueError("Missing or invalid Authorization header")

    token = auth_header.removeprefix("Bearer ").strip()
    decoded_user_info = decode_session_token(token, JWT_SECRET)
    decoded_user_info["thread_id"] = decoded_user_info.pop("session_id")
    return {k: v for k, v in decoded_user_info.items() if v}


def _bounded_nonblank_text(value: Any, field_name: str, max_chars: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    if len(value) > max_chars:
        raise ValueError(f"{field_name} exceeds the configured size limit")
    return value


def _validated_messages(messages: Any) -> list[dict[str, str]]:
    if not isinstance(messages, list) or not 1 <= len(messages) <= MAX_CAPTURED_MESSAGES:
        raise ValueError("messages must be a non-empty bounded list")

    validated: list[dict[str, str]] = []
    total_chars = 0
    for message in messages:
        if not isinstance(message, dict) or message.get("role") not in {"user", "assistant"}:
            raise ValueError("Each message must have a supported role and content")
        content = _bounded_nonblank_text(
            message.get("content"), "message content", MAX_TOOL_TEXT_CHARS
        )
        total_chars += len(content)
        if total_chars > MAX_TOOL_TEXT_CHARS:
            raise ValueError("messages exceed the configured total size limit")
        validated.append({"role": message["role"], "content": content})
    return validated


async def _add(memory: OracleAgentMemory, content: str) -> CallToolResult:
    content = _bounded_nonblank_text(content, "content", MAX_TOOL_TEXT_CHARS)
    user_info = _get_user_info()
    token_thread_id = user_info.pop("thread_id", None)
    if token_thread_id:
        # Thread-scoped SDK writes require a pre-existing thread. Reopen or
        # create only the thread derived from the authenticated identity.
        thread = _get_or_create_scoped_thread(memory, user_info, token_thread_id)
        await thread.add_memory_async(content)
    else:
        await memory.add_memory_async(content=content, **user_info)
    return CallToolResult(
        content=[TextContent(type="text", text="Memory successfully added.")],
        structuredContent=None,
    )


async def _search(memory: OracleAgentMemory, query: str, max_results: int = 8) -> CallToolResult:
    query = _bounded_nonblank_text(query, "query", MAX_SEARCH_QUERY_CHARS)
    if (
        isinstance(max_results, bool)
        or not isinstance(max_results, int)
        or not 1 <= max_results <= MAX_SEARCH_RESULTS
    ):
        raise ValueError(f"max_results must be between 1 and {MAX_SEARCH_RESULTS}")
    user_info = _to_storage_scope(_get_user_info())
    search_results = await memory.search_async(query=query, max_results=max_results, **user_info)
    formatted_results = [
        {"type": result.record.record_type, "content": result.content} for result in search_results
    ]
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(formatted_results))],
        structuredContent=None,
    )


async def _add_messages(memory: OracleAgentMemory, messages: Any, thread_id: str) -> CallToolResult:
    messages = _validated_messages(messages)
    user_info = _get_user_info()
    token_thread_id = user_info.pop("thread_id", None)
    external_thread_id = _resolve_external_thread_id(thread_id, token_thread_id)
    thread = _get_or_create_scoped_thread(memory, user_info, external_thread_id)

    await thread.add_messages_async(messages)
    return CallToolResult(
        content=[TextContent(type="text", text=f"{len(messages)} messages successfully recorded.")],
        structuredContent=None,
    )


def create_server():
    server = FastMCP(name="Memory")
    memory_store_id = os.environ.get("MEMORY_STORE_ID", "").strip()
    if not memory_store_id:
        raise RuntimeError("MEMORY_STORE_ID must be set to a dedicated store for this plugin")
    if len(memory_store_id) > 16:
        raise RuntimeError("MEMORY_STORE_ID must be at most 16 characters")

    pool = oracledb.SessionPool(
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        dsn=os.environ["DB_CONNECT_STRING"],
    )
    embedder = Embedder(
        model=os.environ["EMBEDDER_MODEL_ID"],
        api_base=os.environ["EMBEDDER_API_BASE"],
        api_key=os.environ["EMBEDDER_API_KEY"],
    )
    llm = Llm(
        model=os.environ["LLM_MODEL_ID"],
        api_base=os.environ["LLM_API_BASE"],
        api_key=os.environ["LLM_API_KEY"],
    )
    memory = OracleAgentMemory(
        connection=pool,
        embedder=embedder,
        llm=llm,
        memory_store_id=memory_store_id,
        schema_policy=SchemaPolicy.CREATE_IF_NECESSARY,
    )

    @server.tool(
        description=(
            "Add a compact, durable Memory entry for future Codex runs. Store only self-contained "
            "project knowledge, decisions, conventions, or lessons worth reusing."
        )
    )
    async def add(content: str) -> CallToolResult:
        return await _add(memory, content)

    @server.tool(
        description=(
            "Search persistent Memory for prior decisions, architecture notes, conventions, "
            "constraints, pitfalls, captured Codex messages, and reusable project knowledge. "
            "Use before substantial repo work and again when the task moves to a new subsystem, "
            "design choice, or debugging problem."
        )
    )
    async def search(query: str, max_results: int = 8) -> CallToolResult:
        return await _search(memory, query, max_results)

    @server.tool(description="Hook-only tool; not enabled for model use by this plugin.")
    async def add_messages(messages: list[dict[str, str]], thread_id: str) -> CallToolResult:
        return await _add_messages(memory, messages, thread_id)

    return server


def main(host: str = "127.0.0.1", port: int = 8000):
    if host not in LOOPBACK_HOSTS:
        raise ValueError("This prototype MCP server only supports loopback hosts")
    if not 1 <= port <= 65535:
        raise ValueError("Port must be between 1 and 65535")

    server = create_server()
    server.run(
        transport="streamable-http",
        show_banner=False,
        host=host,
        port=port,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the loopback-only Codex Memory MCP prototype."
    )

    parser.add_argument("--host", choices=sorted(LOOPBACK_HOSTS), default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()

    main(host=args.host, port=args.port)
