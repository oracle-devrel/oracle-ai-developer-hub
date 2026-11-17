# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import json
import os
import sys
from pathlib import Path
from typing import Any

import requests

MCP_CONFIG_PATH = Path(__file__).parent / ".mcp.json"
MCP_TOOL_NAME = "add_messages"
MCP_BASE_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}
# Requests interprets this tuple as (connection timeout, response read timeout),
# in seconds. The hook makes three sequential requests, so these per-request
# limits leave headroom under the 30-second outer timeout in hooks/hooks.json.
MCP_REQUEST_TIMEOUT = (2, 5)
# Bound untrusted hook input before JSON decoding to limit memory use. This is a
# prototype limit; deployments should select limits from their own threat model.
MAX_HOOK_EVENT_BYTES = 1024 * 1024
MAX_CAPTURED_MESSAGE_CHARS = 256 * 1024
MAX_SESSION_ID_CHARS = 256


def _load_mcp_info() -> tuple[str, str]:
    with open(MCP_CONFIG_PATH) as f:
        config = json.load(f)

    url = config["mcpServers"]["memory"]["url"]
    bearer_token_env_var = config["mcpServers"]["memory"]["bearer_token_env_var"]
    token = os.environ[bearer_token_env_var]
    return url, token


def _mcp_response_payloads(response: requests.Response) -> list[Any]:
    """Decode a JSON or Server-Sent Events MCP response without exposing its body."""
    content_type = response.headers.get("Content-Type", "").partition(";")[0].strip().lower()
    try:
        if content_type == "application/json":
            payload = response.json()
            return payload if isinstance(payload, list) else [payload]
        if content_type == "text/event-stream":
            return [
                json.loads(line.removeprefix("data:").strip())
                for line in response.text.splitlines()
                if line.startswith("data:") and line.removeprefix("data:").strip()
            ]
    except ValueError as exc:
        raise RuntimeError("MCP server returned an invalid response") from exc
    raise RuntimeError("MCP server returned an unsupported response type")


def _require_mcp_result(response: requests.Response, request_id: int) -> None:
    """Require one successful JSON-RPC result for the expected request ID."""
    _require_success_status(response)
    matches = [
        payload
        for payload in _mcp_response_payloads(response)
        if isinstance(payload, dict) and payload.get("id") == request_id
    ]
    if len(matches) != 1 or "error" in matches[0] or "result" not in matches[0]:
        raise RuntimeError("MCP request failed")


def _require_success_status(response: requests.Response) -> None:
    """Reject redirects as well as HTTP errors without exposing response details."""
    response.raise_for_status()
    if not 200 <= response.status_code < 300:
        raise RuntimeError("MCP request failed")


def _add_messages(messages: list[dict[str, str]], session_id: str, url: str, token: str) -> None:
    headers = {**MCP_BASE_HEADERS, "Authorization": f"Bearer {token}"}
    with requests.Session() as session:
        request = session.post(
            url,
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "minimal-client", "version": "0.1"},
                },
            },
            timeout=MCP_REQUEST_TIMEOUT,
            allow_redirects=False,
        )
        _require_mcp_result(request, 1)

        if "mcp-session-id" in request.headers:
            headers["mcp-session-id"] = request.headers["mcp-session-id"]

        # initialized notification
        notification = session.post(
            url,
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            },
            timeout=MCP_REQUEST_TIMEOUT,
            allow_redirects=False,
        )
        _require_success_status(notification)

        # call tool
        request = session.post(
            url,
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": MCP_TOOL_NAME,
                    "arguments": {"messages": messages, "thread_id": session_id},
                },
            },
            timeout=MCP_REQUEST_TIMEOUT,
            allow_redirects=False,
        )
        _require_mcp_result(request, 2)


def _capture_message(event: dict[str, Any]) -> bool | None:
    hook_event_name = event.get("hook_event_name")
    if hook_event_name == "UserPromptSubmit":
        role = "user"
        raw_content = event.get("prompt")
    elif hook_event_name == "Stop":
        role = "assistant"
        raw_content = event.get("last_assistant_message")
    else:
        return None

    if (
        not isinstance(raw_content, str)
        or not raw_content.strip()
        or len(raw_content) > MAX_CAPTURED_MESSAGE_CHARS
    ):
        return None

    session_id = event.get("session_id")
    if not isinstance(session_id, str):
        return None
    session_id = session_id.strip()
    if not session_id or len(session_id) > MAX_SESSION_ID_CHARS:
        return None

    url, token = _load_mcp_info()
    messages = [{"role": role, "content": raw_content}]

    _add_messages(messages=messages, session_id=session_id, url=url, token=token)
    return True


def main() -> int:
    try:
        raw_event = sys.stdin.buffer.read(MAX_HOOK_EVENT_BYTES + 1)
        if len(raw_event) > MAX_HOOK_EVENT_BYTES:
            raise ValueError("Hook event exceeds the configured size limit")
        event = json.loads(raw_event or b"{}")
        if not isinstance(event, dict):
            raise ValueError("Hook event must be a JSON object")
        captured = _capture_message(event)
    except Exception:
        # Do not echo exception details: HTTP, configuration, and parser errors
        # can contain tokens, URLs, prompts, or other sensitive input.
        print("Memory hook capture skipped.", file=sys.stderr)
        return 0
    if captured and "OAM_HOOK_DEBUG" in os.environ and os.environ["OAM_HOOK_DEBUG"]:
        print("Memory hook captured one message.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
