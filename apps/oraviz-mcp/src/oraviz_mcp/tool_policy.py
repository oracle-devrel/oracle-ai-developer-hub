"""Operator tool policy and metadata-only auditing for FastMCP 4.0.3.

Construct once with ``load_allowed_tools()`` and pass in ``FastMCP.middleware``.
The server must also enable ``strict_input_validation=True``. Sync tools must
retain FastMCP's default non-abandoning AnyIO worker execution: a cancelled MCP
request keeps its slot until that worker returns. Arbitrarily detached work
and direct ``asyncio.Task.cancel()`` of worker hosts are outside this contract.
"""

from __future__ import annotations

import getpass
import json
import logging
import os
import sys
import threading
from collections.abc import Iterable, Sequence
from contextvars import ContextVar
from datetime import datetime, timezone
from time import monotonic
from typing import Any
from uuid import uuid4

import anyio
from fastmcp.exceptions import ToolError, ValidationError
from fastmcp.server.dependencies import get_access_token, get_http_request
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools import Tool, ToolResult
from jsonschema.validators import validator_for
from mcp.shared.exceptions import MCPError
from mcp.types import INVALID_PARAMS, CallToolRequestParams, ListToolsRequest


KNOWN_TOOLS = frozenset(
    {
        "execute_query",
        "list_tables",
        "get_table_schema",
        "sample_table_data",
        "get_table_details",
        "profile_table",
        "create_chart",
    }
)
MAX_ARGUMENT_BYTES = 65536
request_id: ContextVar[str | None] = ContextVar("oraviz_request_id", default=None)
audit_logger = logging.getLogger("oraviz_mcp.audit")


def _validate_allowed_tools(names: Iterable[str]) -> frozenset[str]:
    allowed = frozenset(names)
    if not allowed or not allowed <= KNOWN_TOOLS:
        # Do not reflect an accidentally pasted credential in a config error.
        raise ValueError("ORACLE_MCP_ALLOWED_TOOLS must contain known tool names")
    return allowed


def load_allowed_tools() -> frozenset[str]:
    """Read a comma-separated operator allowlist; an unset value enables seven tools.

    An explicit empty value, empty entry, or unknown name fails startup. The
    immutable result is a snapshot, independent of later environment changes.
    """
    raw = os.environ.get("ORACLE_MCP_ALLOWED_TOOLS")
    if raw is None:
        return KNOWN_TOOLS
    return _validate_allowed_tools(name.strip() for name in raw.split(","))


class _AuditStderrHandler(logging.StreamHandler):
    def emit(self, record: logging.LogRecord) -> None:
        # Follow stderr redirection without ever falling back to MCP stdout.
        self.stream = sys.stderr
        super().emit(record)


class _SafeToolLogs(logging.Filter):
    """Remove framework validation values/tracebacks before any handler sees them."""

    def filter(self, record: logging.LogRecord) -> bool:
        # FastMCP logs this argument-bearing debug record before middleware runs.
        if (
            record.name == "fastmcp.server.mixins.mcp_operations"
            and isinstance(record.msg, str)
            and "Handler called: call_tool" in record.msg
        ):
            return False
        current_id = request_id.get()
        if current_id is not None:
            record.msg = "Tool pipeline event (request %s)"
            record.args = (current_id,)
            record.exc_info = None
            record.exc_text = None
            record.stack_info = None
        return True


class _SafeTransportLogs(logging.Filter):
    """Sanitize SDK transport logs even before a tool request context exists."""

    def filter(self, record: logging.LogRecord) -> bool:
        # These loggers interpolate bodies, protocol messages, caller-controlled
        # IDs, and parse errors. Keep the emitting source and severity, never the
        # payload or traceback (including a previously formatted exception).
        record.msg = "MCP transport event"
        record.args = ()
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
        return True


def _configure_logging() -> None:
    audit_logger.setLevel(logging.INFO)
    audit_logger.disabled = False
    audit_logger.propagate = False
    if not any(isinstance(h, _AuditStderrHandler) for h in audit_logger.handlers):
        handler = _AuditStderrHandler()
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(message)s"))
        audit_logger.addHandler(handler)
    # Filters belong on emitting loggers: parent logger filters are not applied
    # to propagated records. Never toggle a global level around concurrent calls.
    for name in (
        "fastmcp.server.server",
        "fastmcp.server.mixins.mcp_operations",
        "fastmcp.tools.function_tool",
        "fastmcp.tools.base",
    ):
        logger = logging.getLogger(name)
        if not any(isinstance(f, _SafeToolLogs) for f in logger.filters):
            logger.addFilter(_SafeToolLogs())
    # SDK parsing/session failures occur outside the tool pipeline. The shared
    # JSON-RPC dispatcher can also log exceptions yielded by the SSE transport.
    # Filter only these known emitting loggers, independently of request_id.
    for name in (
        "mcp.server.sse",
        "mcp.server.streamable_http",
        "mcp.server._streamable_http_modern",
        "mcp.server.streamable_http_manager",
        "mcp.server.runner",
        "mcp.shared.jsonrpc_dispatcher",
    ):
        logger = logging.getLogger(name)
        if not any(isinstance(f, _SafeTransportLogs) for f in logger.filters):
            logger.addFilter(_SafeTransportLogs())


def _principal() -> dict[str, Any]:
    """Read verified request identity anew; never inspect a bearer token string."""
    token = get_access_token()
    if token is not None:
        subject = token.claims.get("sub") or token.subject
        issuer = token.claims.get("iss")
        return {
            "principal_source": "token",
            "subject": subject if isinstance(subject, str) else None,
            "issuer": issuer if isinstance(issuer, str) else None,
        }
    try:
        get_http_request()
    except RuntimeError:
        # In stdio there is no network caller; report the local process identity.
        try:
            username = getpass.getuser()
        except (KeyError, OSError):
            username = None
        return {
            "principal_source": "local",
            "subject": username,
            "issuer": None,
            "uid": os.getuid() if hasattr(os, "getuid") else None,
        }
    return {"principal_source": "unauthenticated", "subject": None, "issuer": None}


def _arguments_fit(arguments: Any) -> bool:
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        return False
    encoder = json.JSONEncoder(ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    size = 0
    try:
        for chunk in encoder.iterencode(arguments):
            size += len(chunk.encode("utf-8"))
            if size > MAX_ARGUMENT_BYTES:
                return False
    except (TypeError, ValueError, OverflowError, RecursionError, UnicodeError):
        return False
    return True


def _audit(fields: dict[str, Any], *, phase: str, outcome: str, duration_ms: float) -> None:
    audit_logger.info(
        json.dumps(
            {
                **fields,
                "event": "tool_call",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "phase": phase,
                "outcome": outcome,
                "duration_ms": round(duration_ms, 3),
            },
            ensure_ascii=True,
            separators=(",", ":"),
        )
    )


class ToolPolicyMiddleware(Middleware):
    """Hide and deny disabled tools, bound admission, and audit each tool call.

    ``allowed_tools`` is copied once; ``max_concurrent`` is a positive integer
    supplied by startup configuration. Admission never waits or creates a queue.
    Tool results pass through unchanged; output trust instructions belong to the
    server. Error results are audited as failures, while exceptions are replaced.
    """

    def __init__(
        self,
        allowed_tools: Iterable[str],
        *,
        database_user: str = "",
        max_concurrent: int = 4,
    ) -> None:
        self._allowed_tools = _validate_allowed_tools(allowed_tools)
        if type(max_concurrent) is not int or max_concurrent < 1:
            raise ValueError("max_concurrent must be a positive integer")
        self._database_user = database_user
        self._slots = threading.BoundedSemaphore(max_concurrent)
        _configure_logging()

    @property
    def allowed_tools(self) -> frozenset[str]:
        return self._allowed_tools

    async def on_list_tools(
        self,
        context: MiddlewareContext[ListToolsRequest],
        call_next: CallNext[ListToolsRequest, Sequence[Tool]],
    ) -> Sequence[Tool]:
        return [tool for tool in await call_next(context) if tool.name in self._allowed_tools]

    async def on_request(self, context: MiddlewareContext, call_next: CallNext) -> Any:
        # 4.0.3 routes malformed tools/call envelopes only through the outer
        # hooks. Typed requests continue to on_call_tool and get exactly one pair.
        if context.method == "tools/call" and not isinstance(
            context.message, CallToolRequestParams
        ):
            try:
                return await self.on_call_tool(context, call_next)
            except ToolError as exc:
                # This outer path has no FastMCP tool-error adapter. Use a safe
                # protocol error so the SDK does not log an unhandled traceback.
                raise MCPError(code=INVALID_PARAMS, message=str(exc)) from None
        return await call_next(context)

    async def on_call_tool(
        self,
        context: MiddlewareContext[CallToolRequestParams],
        call_next: CallNext[CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        message = context.message
        malformed = not isinstance(message, CallToolRequestParams)
        if malformed:
            name = message.get("name") if isinstance(message, dict) else None
            arguments = message.get("arguments") if isinstance(message, dict) else None
        else:
            name, arguments = message.name, message.arguments
        safe_name = name if isinstance(name, str) and name in KNOWN_TOOLS else "unknown"
        call_id = str(uuid4())
        context_token = request_id.set(call_id)
        started = monotonic()
        fields = {
            "request_id": call_id,
            "tool": safe_name,
            "database_user": self._database_user,
            "principal_source": "unavailable",
            "subject": None,
            "issuer": None,
        }
        outcome = "failure"
        acquired = False
        try:
            try:
                fields.update(_principal())
            finally:
                # Even an identity-provider failure has a before/after pair.
                _audit(fields, phase="before", outcome="started", duration_ms=0)
            if safe_name not in self._allowed_tools or malformed:
                outcome = "denied"
                raise ToolError("Tool call rejected")
            if not _arguments_fit(arguments):
                outcome = "denied"
                raise ToolError("Tool call rejected")
            acquired = self._slots.acquire(blocking=False)
            if not acquired:
                outcome = "denied"
                raise ToolError("Tool call rejected")
            # Public lookup does not dispatch middleware. Validate before the
            # framework's tool runner, whose warning includes rejected values.
            tool = (
                await context.fastmcp_context.fastmcp.get_tool(name)
                if context.fastmcp_context is not None
                else None
            )
            schema = {**tool.parameters, "additionalProperties": False} if tool else None
            if schema is None or not validator_for(schema)(schema).is_valid(arguments or {}):
                outcome = "denied"
                raise ToolError("Tool call rejected")
            try:
                result = await call_next(context)
            except ValidationError:
                outcome = "denied"
                raise
            # AnyIO shields sync workers until completion. Observe pending MCP
            # cancellation now, before recording success and releasing the slot.
            await anyio.lowlevel.checkpoint_if_cancelled()
            # Count both MCP text representations: structured results can also
            # be mirrored in text content. Never truncate JSON into invalid data.
            text_size = sum(len(getattr(block, "text", "")) for block in result.content)
            if result.structured_content is not None:
                text_size += len(json.dumps(result.structured_content, ensure_ascii=False))
            if text_size > 256_000:
                raise ToolError("Tool result exceeds the output budget")
            outcome = "failure" if result.is_error else "success"
            return result
        except anyio.get_cancelled_exc_class():
            outcome = "cancellation"
            raise
        except Exception:
            raise ToolError(f"Tool call failed (request {call_id}).") from None
        finally:
            try:
                if acquired:
                    self._slots.release()
                _audit(
                    fields,
                    phase="after",
                    outcome=outcome,
                    duration_ms=(monotonic() - started) * 1000,
                )
            finally:
                request_id.reset(context_token)
