"""Security policy tests using real FastMCP client/server dispatch and workers."""

import asyncio
import io
import json
import logging
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import anyio
import pytest
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError, ValidationError
from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.tools import ToolResult
from mcp import types
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser, authorization_context
from mcp.server.sse import SseServerTransport
from mcp.server.streamable_http import StreamableHTTPServerTransport
from mcp.shared.exceptions import MCPError
from starlette.requests import Request
from starlette.testclient import TestClient

from oraviz_mcp import tool_policy as policy


@pytest.fixture
def events(monkeypatch):
    entries = []

    class Capture(logging.Handler):
        def emit(self, record):
            assert record.levelno == logging.INFO
            assert record.exc_info is None
            entries.append(json.loads(record.getMessage()))

    handler = Capture()
    policy.audit_logger.addHandler(handler)
    monkeypatch.setattr(policy, "get_access_token", lambda: None)
    monkeypatch.setattr(policy.getpass, "getuser", lambda: "local-operator")
    try:
        yield entries
    finally:
        policy.audit_logger.removeHandler(handler)


def make_server(*, allowed=("execute_query",), max_concurrent=4):
    middleware = policy.ToolPolicyMiddleware(
        allowed, database_user="db-reader", max_concurrent=max_concurrent
    )
    app = FastMCP("policy-tests", middleware=[middleware], strict_input_validation=True)
    calls = []

    @app.tool(name="execute_query")
    def query(sql: str, limit: int = 1) -> str:
        calls.append((sql, limit, policy.request_id.get()))
        return "RESULT_SECRET"

    @app.tool
    def list_tables() -> list[str]:
        calls.append("list_tables")
        return ["demo"]

    @app.tool
    def future_tool() -> str:
        calls.append("future_tool")
        return "future"

    return app, middleware, calls


def context_for(app, arguments=None, name="execute_query"):
    return MiddlewareContext(
        message=types.CallToolRequestParams(
            name=name, arguments=arguments if arguments is not None else {"sql": "SELECT 1"}
        ),
        method="tools/call",
        fastmcp_context=SimpleNamespace(fastmcp=app),
    )


def assert_pair(events, outcome):
    before, after = events[-2:]
    assert before["phase"] == "before"
    assert before["outcome"] == "started"
    assert after["phase"] == "after"
    assert after["outcome"] == outcome
    assert before["request_id"] == after["request_id"]
    assert str(UUID(after["request_id"])) == after["request_id"]
    assert before["duration_ms"] == 0
    assert after["duration_ms"] >= 0
    return after


def test_default_allowlist_is_explicit(monkeypatch):
    monkeypatch.delenv("ORACLE_MCP_ALLOWED_TOOLS", raising=False)
    assert policy.load_allowed_tools() == frozenset(
        {
            "execute_query", "list_tables", "get_table_schema", "sample_table_data",
            "get_table_details", "profile_table", "create_chart",
        }
    )


@pytest.mark.parametrize("value", ["", "  ", ",", "execute_query,", ",list_tables", "unknown", "EXECUTE_QUERY"])
def test_invalid_allowlist_fails_without_echoing_config(monkeypatch, value):
    monkeypatch.setenv("ORACLE_MCP_ALLOWED_TOOLS", value)
    with pytest.raises(ValueError, match="known tool names"):
        policy.load_allowed_tools()


def test_allowlist_is_startup_snapshot(monkeypatch):
    monkeypatch.setenv("ORACLE_MCP_ALLOWED_TOOLS", " execute_query, list_tables,execute_query ")
    selected = policy.load_allowed_tools()
    assert selected == frozenset({"execute_query", "list_tables"})
    source = set(selected)
    middleware = policy.ToolPolicyMiddleware(source)
    source.add("create_chart")
    monkeypatch.setenv("ORACLE_MCP_ALLOWED_TOOLS", "create_chart")
    assert middleware.allowed_tools == selected
    with pytest.raises(AttributeError):
        middleware.allowed_tools = frozenset({"create_chart"})


@pytest.mark.parametrize("value", [0, -1, True, 1.5, "4", None])
def test_invalid_concurrency_fails_startup(value):
    with pytest.raises(ValueError, match="positive integer"):
        policy.ToolPolicyMiddleware({"execute_query"}, max_concurrent=value)


@pytest.mark.parametrize("value", [set(), {"future_tool"}, {""}])
def test_constructor_validates_allowlist(value):
    with pytest.raises(ValueError):
        policy.ToolPolicyMiddleware(value)


@pytest.mark.asyncio
async def test_client_lists_and_calls_only_enabled_tools(events):
    app, middleware, calls = make_server()
    async with Client(app) as client:
        assert [tool.name for tool in await client.list_tools()] == ["execute_query"]
        assert events == []
        result = await client.call_tool("execute_query", {"sql": "SELECT SECRET"})
        assert result.content[0].text == "RESULT_SECRET"
        success = assert_pair(events, "success")
        assert calls == [("SELECT SECRET", 1, success["request_id"])]
        assert success["database_user"] == "db-reader"
        assert success["subject"] == "local-operator"
        assert success["principal_source"] == "local"
        for name in ("list_tables", "future_tool", "GUESS_SECRET\nforged-log"):
            result = await client.call_tool(name, {}, raise_on_error=False)
            assert result.is_error
            denied = assert_pair(events, "denied")
            assert denied["tool"] == ("list_tables" if name == "list_tables" else "unknown")
            assert denied["request_id"] in result.content[0].text
        assert len(calls) == 1
        assert len(events) == 8
    assert policy.request_id.get() is None
    serialized = json.dumps(events)
    for secret in ("SELECT SECRET", "RESULT_SECRET", "GUESS_SECRET"):
        assert secret not in serialized


@pytest.mark.parametrize(
    "arguments",
    [
        {}, {"sql": 12}, {"sql": "VALUE_SECRET", "limit": "123"},
        {"sql": "VALUE_SECRET", "limit": True},
        {"sql": "VALUE_SECRET", "unexpected": "EXTRA_SECRET"},
    ],
)
@pytest.mark.asyncio
async def test_schema_rejections_precede_framework_and_execution(events, arguments, monkeypatch):
    app, middleware, calls = make_server()
    framework_log = logging.getLogger("fastmcp.server.server")
    warning = []
    monkeypatch.setattr(framework_log, "warning", lambda *args, **kwargs: warning.append(args))
    async with Client(app) as client:
        result = await client.call_tool("execute_query", arguments, raise_on_error=False)
    assert result.is_error
    assert_pair(events, "denied")
    assert calls == []
    assert warning == []
    assert "VALUE_SECRET" not in result.content[0].text + json.dumps(events)


@pytest.mark.asyncio
async def test_allowlisted_but_unregistered_tool_is_denied(events):
    app, middleware, calls = make_server(allowed={"create_chart"})
    async with Client(app) as client:
        assert await client.list_tools() == []
        result = await client.call_tool("create_chart", {}, raise_on_error=False)
    assert result.is_error
    assert_pair(events, "denied")


@pytest.mark.asyncio
async def test_json_argument_byte_boundary_and_aggregate_limit(events):
    app, middleware, calls = make_server()
    overhead = len(json.dumps({"sql": ""}, separators=(",", ":")).encode())
    async with Client(app) as client:
        await client.call_tool("execute_query", {"sql": "a" * (65536 - overhead)})
        assert_pair(events, "success")
        for arguments in (
            {"sql": "a" * (65537 - overhead)},
            {"sql": "é" * 32764},
            {"sql": "a" * 65520, "limit": 123456789},
        ):
            result = await client.call_tool("execute_query", arguments, raise_on_error=False)
            assert result.is_error
            assert_pair(events, "denied")
    assert len(calls) == 1


@pytest.mark.parametrize("arguments", [[], "secret", {"a": float("nan")}, {"a": object()}, {"a": "\ud800"}])
def test_non_json_arguments_are_rejected(arguments):
    assert not policy._arguments_fit(arguments)


def test_json_none_and_recursive_values():
    assert policy._arguments_fit(None)
    circular = {}
    circular["self"] = circular
    assert not policy._arguments_fit(circular)


@pytest.mark.asyncio
async def test_pipeline_exceptions_are_generic_and_release_slots(events):
    app, middleware, calls = make_server(max_concurrent=1)
    for error, outcome in (
        (RuntimeError("ERROR_SECRET DSN_SECRET SELECT_SECRET"), "failure"),
        (ToolError("TOOL_ERROR_SECRET"), "failure"),
        (ValidationError("VALIDATION_SECRET"), "denied"),
    ):
        callback = AsyncMock(side_effect=error)
        with pytest.raises(ToolError) as caught:
            await middleware.on_call_tool(context_for(app), callback)
        after = assert_pair(events, outcome)
        assert str(caught.value) == f"Tool call failed (request {after['request_id']})."
        assert caught.value.__suppress_context__
        assert policy.request_id.get() is None
    result = ToolResult(content="UNCHANGED_RESULT_SECRET")
    assert await middleware.on_call_tool(context_for(app), AsyncMock(return_value=result)) is result
    assert_pair(events, "success")
    assert "SECRET" not in json.dumps(events)


@pytest.mark.asyncio
async def test_result_error_flag_is_audited_without_content_rewriting(events):
    app, middleware, calls = make_server()
    result = ToolResult(content="already-safe error", is_error=True)
    assert await middleware.on_call_tool(context_for(app), AsyncMock(return_value=result)) is result
    assert_pair(events, "failure")


@pytest.mark.asyncio
async def test_framework_exception_logs_do_not_expose_values(events, monkeypatch):
    app, middleware, calls = make_server()

    @app.tool(name="execute_query")
    def failing(sql: str) -> str:
        raise RuntimeError("RAW_ERROR_SECRET DSN_SECRET " + sql)

    sink = io.StringIO()
    handler = logging.StreamHandler(sink)
    loggers = [logging.getLogger(name) for name in (
        "fastmcp.server.server", "fastmcp.server.mixins.mcp_operations"
    )]
    for logger in loggers:
        monkeypatch.setattr(logger, "level", logging.DEBUG)
        logger.addHandler(handler)
    try:
        async with Client(app) as client:
            result = await client.call_tool("execute_query", {"sql": "SQL_SECRET"}, raise_on_error=False)
    finally:
        for logger in loggers:
            logger.removeHandler(handler)
    assert result.is_error
    after = assert_pair(events, "failure")
    combined = sink.getvalue() + result.content[0].text + json.dumps(events)
    assert "SECRET" not in combined
    assert after["request_id"] in sink.getvalue()
    assert "Traceback" not in sink.getvalue()


@pytest.mark.asyncio
async def test_principal_is_read_per_call_without_token_or_other_claims(events, monkeypatch):
    app, middleware, calls = make_server()
    current = None
    monkeypatch.setattr(policy, "get_access_token", lambda: current)
    for subject in ("alice", "bob"):
        current = AccessToken(
            token="TOKEN_SECRET", client_id="CLIENT_SECRET", scopes=[],
            subject="fallback-subject",
            claims={"sub": subject, "iss": "https://issuer.example", "private": "CLAIM_SECRET"},
        )
        await middleware.on_call_tool(context_for(app), AsyncMock(return_value=ToolResult(content="ok")))
        after = assert_pair(events, "success")
        assert after["subject"] == subject
        assert after["issuer"] == "https://issuer.example"
        assert after["principal_source"] == "token"
        assert "uid" not in after
    assert len({entry["request_id"] for entry in events}) == 2
    assert "SECRET" not in json.dumps(events)


def test_token_subject_fallback_and_no_local_identity_for_http(monkeypatch):
    token = AccessToken(token="secret", client_id="client", scopes=[], subject="verified-sub")
    monkeypatch.setattr(policy, "get_access_token", lambda: token)
    assert policy._principal()["subject"] == "verified-sub"
    token.subject = None
    assert policy._principal()["subject"] is None
    monkeypatch.setattr(policy, "get_access_token", lambda: None)
    monkeypatch.setattr(policy, "get_http_request", lambda: Request({"type": "http"}))
    assert policy._principal() == {
        "principal_source": "unauthenticated", "subject": None, "issuer": None
    }


@pytest.mark.asyncio
async def test_audit_is_json_stderr_at_info_despite_error_log_level(events, monkeypatch, capsys):
    monkeypatch.setenv("LOG_LEVEL", "ERROR")
    monkeypatch.setattr(logging.getLogger(), "level", logging.ERROR)
    app, middleware, calls = make_server()
    async with Client(app) as client:
        await client.call_tool("execute_query", {"sql": "SQL_SECRET"})
    captured = capsys.readouterr()
    assert captured.out == ""
    lines = [json.loads(line) for line in captured.err.splitlines() if line.startswith('{"request_id"')]
    assert len(lines) == 2
    assert_pair(lines, "success")
    assert policy.audit_logger.level == logging.INFO
    assert not policy.audit_logger.propagate


@pytest.mark.asyncio
async def test_capacity_rejects_immediately_and_recovers(events):
    app, middleware, calls = make_server(max_concurrent=1)
    entered = asyncio.Event()
    release = asyncio.Event()

    async def blocked(context):
        entered.set()
        await release.wait()
        return ToolResult(content="ok")

    task = asyncio.create_task(middleware.on_call_tool(context_for(app), blocked))
    await asyncio.wait_for(entered.wait(), 3)
    callback = AsyncMock(return_value=ToolResult(content="ok"))
    try:
        with pytest.raises(ToolError):
            await asyncio.wait_for(middleware.on_call_tool(context_for(app), callback), 1)
        callback.assert_not_awaited()
        assert_pair(events, "denied")
    finally:
        release.set()
        await task
    await middleware.on_call_tool(context_for(app), callback)
    assert_pair(events, "success")


@pytest.mark.asyncio
async def test_async_cancellation_audits_and_restores_request_context(events):
    app, middleware, calls = make_server(max_concurrent=1)
    entered = asyncio.Event()

    async def blocked(context):
        entered.set()
        await asyncio.Event().wait()

    task = asyncio.create_task(middleware.on_call_tool(context_for(app), blocked))
    await asyncio.wait_for(entered.wait(), 3)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert_pair(events, "cancellation")
    assert policy.request_id.get() is None
    await middleware.on_call_tool(context_for(app), AsyncMock(return_value=ToolResult(content="ok")))
    assert_pair(events, "success")


@pytest.mark.asyncio
async def test_real_client_cancellation_holds_slot_until_sync_worker_finishes(events):
    app, middleware, calls = make_server(max_concurrent=1)
    entered = threading.Event()
    release = threading.Event()
    finished = threading.Event()

    @app.tool(name="execute_query")
    def blocked(sql: str) -> str:
        entered.set()
        try:
            assert release.wait(5), "test failed to release worker"
            return "ok"
        finally:
            finished.set()

    async with Client(app) as client:
        task = asyncio.create_task(client.call_tool("execute_query", {"sql": "SECRET"}))
        try:
            assert await anyio.to_thread.run_sync(entered.wait, 3)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            result = await client.call_tool("execute_query", {"sql": "second"}, raise_on_error=False)
            assert result.is_error
            assert_pair(events, "denied")
            assert not finished.is_set()
            release.set()
            with anyio.fail_after(3):
                while not any(event["outcome"] == "cancellation" for event in events):
                    await anyio.sleep(0.01)
            assert finished.is_set()
            await client.call_tool("execute_query", {"sql": "third"})
            assert_pair(events, "success")
        finally:
            release.set()
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_malformed_raw_envelope_is_audited_and_never_dispatched(events):
    app, middleware, calls = make_server()
    callback = AsyncMock(side_effect=ValueError("RAW_PARAMS_SECRET"))
    context = MiddlewareContext(
        message={"name": "execute_query", "arguments": ["RAW_PARAMS_SECRET"]},
        method="tools/call",
    )
    with pytest.raises(MCPError):
        await middleware.on_request(context, callback)
    callback.assert_not_awaited()
    assert_pair(events, "denied")
    assert "RAW_PARAMS_SECRET" not in json.dumps(events)


@pytest.mark.parametrize("params", [
    {"name": "execute_query", "arguments": ["RAW_PARAMS_SECRET"]},
    {"name": ["RAW_NAME_SECRET"]},
    {},
])
@pytest.mark.asyncio
async def test_client_malformed_envelope_is_safe(events, params, capsys):
    app, middleware, calls = make_server()
    async with Client(app) as client:
        request = types.Request[dict, str](method="tools/call", params=params)
        with pytest.raises(MCPError) as caught:
            await client.session.send_request(request, types.CallToolResult)
    after = assert_pair(events, "denied")
    assert after["tool"] == ("execute_query" if params.get("name") == "execute_query" else "unknown")
    assert caught.value.error.code == types.INVALID_PARAMS
    assert after["request_id"] in str(caught.value)
    assert calls == []
    captured = capsys.readouterr()
    assert "SECRET" not in captured.err + str(caught.value)
    assert "Traceback" not in captured.err


@pytest.mark.asyncio
async def test_identity_failure_is_audited_and_restores_enclosing_context(events, monkeypatch):
    app, middleware, calls = make_server()

    def failing_identity():
        raise RuntimeError("IDENTITY_SECRET")

    monkeypatch.setattr(policy, "get_access_token", failing_identity)
    outer_token = policy.request_id.set("outer-request")
    callback = AsyncMock()
    try:
        with pytest.raises(ToolError):
            await middleware.on_call_tool(context_for(app), callback)
        assert policy.request_id.get() == "outer-request"
    finally:
        policy.request_id.reset(outer_token)
    callback.assert_not_awaited()
    assert_pair(events, "failure")
    assert events[-1]["principal_source"] == "unavailable"
    assert "IDENTITY_SECRET" not in json.dumps(events)


def test_local_identity_lookup_failure_and_framework_logs_outside_calls(monkeypatch):
    def missing_user():
        raise OSError("USER_SECRET")

    monkeypatch.setattr(policy, "get_access_token", lambda: None)
    monkeypatch.setattr(policy.getpass, "getuser", missing_user)
    assert policy._principal()["subject"] is None
    record = logging.LogRecord("fastmcp.server.server", logging.INFO, __file__, 1, "startup", (), None)
    assert policy._SafeToolLogs().filter(record)
    assert record.getMessage() == "startup"


@pytest.mark.asyncio
async def test_unrelated_request_is_unchanged(events):
    app, middleware, calls = make_server()
    sentinel = object()
    callback = AsyncMock(return_value=sentinel)
    context = MiddlewareContext(message={}, method="ping")
    assert await middleware.on_request(context, callback) is sentinel
    callback.assert_awaited_once_with(context)
    assert events == []


@pytest.mark.asyncio
async def test_real_client_reads_verified_principal_for_each_call(events, monkeypatch):
    monkeypatch.setattr(policy, "get_access_token", get_access_token)
    current_subject = "alice"

    class VerifiedIdentity(Middleware):
        async def on_call_tool(self, context, call_next):
            # Emulate the auth provider's already-verified SDK identity context.
            token = AccessToken(
                token="BEARER_SECRET", client_id="CLIENT_SECRET", scopes=[],
                claims={"sub": current_subject, "iss": "https://verified.example"},
            )
            previous = auth_context_var.set(AuthenticatedUser(token))
            try:
                return await call_next(context)
            finally:
                auth_context_var.reset(previous)

    middleware = policy.ToolPolicyMiddleware({"list_tables"})
    app = FastMCP(
        "verified-principals", middleware=[VerifiedIdentity(), middleware],
        strict_input_validation=True,
    )

    @app.tool
    def list_tables() -> str:
        return "tables"

    async with Client(app) as client:
        for subject in ("alice", "bob"):
            current_subject = subject
            await client.call_tool("list_tables", {})
            event = assert_pair(events, "success")
            assert event["subject"] == subject
            assert event["issuer"] == "https://verified.example"
            assert event["principal_source"] == "token"
    assert len(events) == 4
    assert "SECRET" not in json.dumps(events)


@pytest.mark.parametrize("malformed", [False, True])
@pytest.mark.parametrize("level", [logging.DEBUG, logging.ERROR])
def test_authenticated_sse_transport_never_logs_payloads(
    events, monkeypatch, caplog, malformed, level
):
    access_token = AccessToken(
        token="BEARER_SECRET", client_id="test-client", subject="test-user",
        scopes=["read"], claims={"sub": "test-user", "iss": "https://issuer.example"},
    )

    class TestVerifier(TokenVerifier):
        async def verify_token(self, token):
            return access_token if token == access_token.token else None

    transport = SseServerTransport("/messages/")
    session_id = uuid4()
    # Seed an established session; HTTP bearer/scope checks and the real SSE
    # parser still run. The writer records dispatch without opening a stream.
    writer = AsyncMock()
    transport._read_stream_writers[session_id] = writer
    transport._session_owners[session_id] = authorization_context(AuthenticatedUser(access_token))
    monkeypatch.setattr("fastmcp.server.http.SseServerTransport", lambda *a, **kw: transport)
    middleware = policy.ToolPolicyMiddleware({"execute_query"})
    app = FastMCP(
        "sse-log-test", auth=TestVerifier(required_scopes=["read"]),
        middleware=[middleware],
    ).http_app(transport="sse")
    message = {
        "jsonrpc": "2.0", "id": 1,
        "method": ["SQL_SECRET", "TOKEN_SECRET"] if malformed else "tools/call",
        "params": {"name": "execute_query", "arguments": {"sql": "SELECT 'SQL_SECRET'"}},
    }
    assert policy.request_id.get() is None
    with TestClient(app) as client, caplog.at_level(level, logger="mcp.server.sse"):
        url = f"/messages/?session_id={session_id.hex}"
        assert client.post(url, json=message).status_code == 401
        writer.send.assert_not_awaited()
        response = client.post(
            url, json=message, headers={"authorization": f"Bearer {access_token.token}"}
        )
    assert response.status_code == (400 if malformed else 202)
    writer.send.assert_awaited_once()
    delivered = writer.send.call_args.args[0]
    if malformed:
        assert isinstance(delivered, Exception)
        assert "SQL_SECRET" in str(delivered)  # The sensitive parse error really occurred.
    else:
        assert delivered.message.params["arguments"]["sql"] == "SELECT 'SQL_SECRET'"
    records = [record for record in caplog.records if record.name == "mcp.server.sse"]
    if malformed or level == logging.DEBUG:
        assert records
    if malformed:
        assert any(record.levelno == logging.ERROR for record in records)
    for record in records:
        assert record.getMessage() == "MCP transport event"
        assert record.exc_info is record.exc_text is record.stack_info is None
    assert "SECRET" not in "\n".join(record.getMessage() for record in records)
    assert "Traceback" not in caplog.text
    assert events == []  # Rejected/queued before any tool middleware is entered.
    assert policy.request_id.get() is None


@pytest.mark.asyncio
async def test_streamable_http_body_read_failure_is_sanitized_before_middleware(caplog):
    policy.ToolPolicyMiddleware({"execute_query"})
    transport = StreamableHTTPServerTransport(None, is_json_response_enabled=True)
    writer = AsyncMock()
    transport._read_stream_writer = writer
    scope = {
        "type": "http", "method": "POST", "path": "/mcp", "query_string": b"",
        "headers": [(b"content-type", b"application/json"), (b"accept", b"application/json")],
    }
    receive = AsyncMock(side_effect=RuntimeError("BODY_READ_SECRET"))
    send = AsyncMock()
    assert policy.request_id.get() is None
    with caplog.at_level(logging.ERROR, logger="mcp.server.streamable_http"):
        await transport.handle_request(scope, receive, send)
    assert send.call_args_list[0].args[0]["status"] == 500
    writer.send.assert_awaited_once()
    assert "BODY_READ_SECRET" in str(writer.send.call_args.args[0])
    records = [r for r in caplog.records if r.name == "mcp.server.streamable_http"]
    assert len(records) == 1
    assert records[0].getMessage() == "MCP transport event"
    assert records[0].exc_info is None
    assert "BODY_READ_SECRET" not in caplog.text
    assert "Traceback" not in caplog.text


@pytest.mark.parametrize("name", [
    "mcp.server.sse", "mcp.server.streamable_http", "mcp.server._streamable_http_modern",
    "mcp.server.streamable_http_manager", "mcp.server.runner", "mcp.shared.jsonrpc_dispatcher",
])
def test_transport_filters_scrub_cached_errors_without_request_context(name, caplog):
    policy.ToolPolicyMiddleware({"execute_query"})
    policy.ToolPolicyMiddleware({"execute_query"})
    logger = logging.getLogger(name)
    assert sum(isinstance(f, policy._SafeTransportLogs) for f in logger.filters) == 1
    assert policy.request_id.get() is None
    record = logging.LogRecord(
        name, logging.ERROR, __file__, 1, "PAYLOAD_SECRET %s", ("ARG_SECRET",),
        (ValueError, ValueError("ERROR_SECRET"), None), sinfo="STACK_SECRET",
    )
    record.exc_text = "CACHED_TRACEBACK_SECRET"
    with caplog.at_level(logging.ERROR, logger=name):
        logger.handle(record)
    assert record.getMessage() == "MCP transport event"
    assert record.levelno == logging.ERROR
    assert record.exc_info is record.exc_text is record.stack_info is None
    assert record.args == ()
    assert "SECRET" not in caplog.text


def test_transport_filter_does_not_change_unrelated_logging(caplog):
    policy.ToolPolicyMiddleware({"execute_query"})
    logger = logging.getLogger("unrelated.application")
    with caplog.at_level(logging.WARNING, logger=logger.name):
        logger.warning("Application diagnostic %s", "preserved")
    assert caplog.records[-1].getMessage() == "Application diagnostic preserved"
