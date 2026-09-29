"""Hermetic JWT and real ASGI middleware tests; no external IdP or Oracle."""

import logging
import os
import subprocess
import sys
import time
from unittest.mock import AsyncMock

import pytest
from fastmcp import Client, FastMCP
from fastmcp.client.transports import StdioTransport
from fastmcp.server.auth.providers.jwt import RSAKeyPair
from joserfc import jwk, jwt
from starlette.testclient import TestClient

from oraviz_mcp.transport_security import TransportSecurityError, build_auth, validate_auth

AUTH_ENV = {
    "ORACLE_MCP_AUTH_ISSUER": "https://identity.example.com",
    "ORACLE_MCP_AUTH_AUDIENCE": "oraviz",
    "ORACLE_MCP_AUTH_JWKS_URL": "https://identity.example.com/jwks",
    "ORACLE_MCP_AUTH_REQUIRED_SCOPES": "oraviz:read",
}
TRANSPORTS = ["http", "sse", "streamable-http"]
CALL = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "read_data", "arguments": {}}}
HEADERS = {"accept": "application/json, text/event-stream"}


@pytest.fixture(autouse=True)
def clean_auth_environment(monkeypatch):
    for name in list(os.environ):
        if name.startswith("ORACLE_MCP_AUTH_"):
            monkeypatch.delenv(name)


@pytest.fixture
def configured(monkeypatch):
    for name, value in AUTH_ENV.items():
        monkeypatch.setenv(name, value)


@pytest.fixture(scope="module")
def keys():
    return RSAKeyPair.generate()


def token(keys, **overrides):
    options = {
        "issuer": AUTH_ENV["ORACLE_MCP_AUTH_ISSUER"],
        "audience": AUTH_ENV["ORACLE_MCP_AUTH_AUDIENCE"],
        "scopes": ["oraviz:read"],
        "kid": "test-key",
    }
    options.update(overrides)
    return keys.create_token(**options)


def auth_with_keys(monkeypatch, keys, transport="http"):
    auth = build_auth(transport)
    public_jwk = jwk.import_key(keys.public_key, "RSA").as_dict()
    public_jwk["kid"] = "test-key"
    monkeypatch.setattr(auth.token_verifier, "_fetch_jwks", AsyncMock(return_value={"keys": [public_jwk]}))
    return auth


def protected_app(auth, transport):
    executions = []
    server = FastMCP("Authentication test", auth=auth)

    @server.tool
    def read_data() -> str:
        executions.append("read")
        return "authorized result"

    app = server.http_app(transport=transport, stateless_http=True, json_response=True)
    return app, executions


@pytest.mark.parametrize("transport", TRANSPORTS)
@pytest.mark.parametrize("missing", AUTH_ENV)
def test_all_network_transports_require_every_setting(monkeypatch, configured, transport, missing):
    monkeypatch.delenv(missing)
    with pytest.raises(TransportSecurityError, match=missing):
        build_auth(transport)


@pytest.mark.asyncio
async def test_stdio_keeps_local_identity_and_denies_network_overrides(monkeypatch):
    monkeypatch.setenv("ORACLE_MCP_AUTH_JWKS_URL", "invalid")
    auth = build_auth("stdio")
    assert await auth.verify_token("any-token") is None
    validate_auth("stdio", auth)


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_stdio_app_network_override_denies_without_config(transport):
    app, executions = protected_app(build_auth("stdio"), transport)
    with TestClient(app) as client:
        for headers in [HEADERS, {**HEADERS, "authorization": "Bearer anything"}]:
            if transport == "sse":
                assert client.get("/sse", headers=headers).status_code == 401
                response = client.post("/messages/", headers=headers, json=CALL)
            else:
                response = client.post("/mcp", headers=headers, json=CALL)
            assert response.status_code == 401
    assert executions == []


@pytest.mark.asyncio
async def test_stdio_app_uses_network_auth_when_configured(monkeypatch, configured, keys):
    auth = auth_with_keys(monkeypatch, keys, "stdio")
    assert await auth.verify_token(token(keys)) is not None
    validate_auth("http", auth)


def test_unknown_transport_fails_without_echoing_input():
    with pytest.raises(TransportSecurityError) as error:
        build_auth("invalid-secret")
    assert "invalid-secret" not in str(error.value)


@pytest.mark.parametrize("name", AUTH_ENV)
@pytest.mark.parametrize("value", ["", "  ", "value\r\nsecret"])
def test_blank_and_control_character_config_rejected(monkeypatch, configured, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(TransportSecurityError, match=name):
        build_auth("http")


@pytest.mark.parametrize("name", ["ISSUER", "JWKS_URL", "BASE_URL"])
@pytest.mark.parametrize("value", [
    "http://identity.example.com", "https:///missing-host", "https://user:secret@example.com",
    "https://identity.example.com/jwks?secret=credential", "https://identity.example.com/#secret",
    "https://identity.example.com:bad", "https://identity.example.com:0", "https://[bad",
    "https://identity.example.com\\@elsewhere.example", "https://identity .example.com",
])
def test_unsafe_urls_rejected_without_echo(monkeypatch, configured, name, value):
    variable = f"ORACLE_MCP_AUTH_{name}"
    monkeypatch.setenv(variable, value)
    with pytest.raises(TransportSecurityError, match=variable) as error:
        build_auth("http")
    assert value not in str(error.value)


@pytest.mark.parametrize("value", ['read"injected', "read\\injected", "réad"])
def test_invalid_scope_syntax_rejected(monkeypatch, configured, value):
    monkeypatch.setenv("ORACLE_MCP_AUTH_REQUIRED_SCOPES", value)
    with pytest.raises(TransportSecurityError, match="REQUIRED_SCOPES"):
        build_auth("http")


def test_scope_list_and_fixed_algorithm(monkeypatch, configured):
    monkeypatch.setenv("ORACLE_MCP_AUTH_REQUIRED_SCOPES", "oraviz:read reports:read")
    auth = build_auth("http")
    assert auth.required_scopes == ["oraviz:read", "reports:read"]
    assert auth.token_verifier.algorithm == "RS256"
    validate_auth("http", auth)
    auth.required_scopes = []
    with pytest.raises(TransportSecurityError):
        validate_auth("http", auth)


def invalid_token(keys, failure):
    if failure == "malformed":
        return "not-a-jwt-secret"
    if failure == "signature":
        return token(RSAKeyPair.generate())
    if failure == "issuer":
        return token(keys, issuer="untrusted-issuer-secret")
    if failure == "audience":
        return token(keys, audience="untrusted-audience-secret")
    if failure == "expired":
        return token(keys, expires_in_seconds=-60)
    if failure == "missing_scope":
        return token(keys, scopes=[])
    if failure == "wrong_scope":
        return token(keys, scopes=["unrelated:read"])
    if failure == "future_nbf":
        return token(keys, additional_claims={"nbf": int(time.time()) + 600})
    if failure == "invalid_nbf":
        return token(keys, additional_claims={"nbf": "invalid-secret"})
    if failure == "infinite_exp":
        return token(keys, additional_claims={"exp": float("inf")})
    if failure == "nan_exp":
        return token(keys, additional_claims={"exp": float("nan")})
    if failure == "boolean_exp":
        return token(keys, additional_claims={"exp": True})
    if failure == "invalid_exp":
        return token(keys, additional_claims={"exp": "invalid-secret"})
    if failure == "numeric_string_exp":
        return token(keys, additional_claims={"exp": str(int(time.time()) + 600)})
    if failure == "null_exp":
        return token(keys, additional_claims={"exp": None})
    if failure == "nan_nbf":
        return token(keys, additional_claims={"nbf": float("nan")})
    if failure == "boolean_nbf":
        return token(keys, additional_claims={"nbf": False})
    claims = {"iss": AUTH_ENV["ORACLE_MCP_AUTH_ISSUER"], "aud": "oraviz",
              "scope": "oraviz:read", "sub": "test", "exp": int(time.time()) + 600}
    if failure.startswith("missing_"):
        del claims[{"missing_exp": "exp", "missing_issuer": "iss", "missing_audience": "aud"}[failure]]
    elif failure == "algorithm":
        return jwt.encode({"alg": "HS256", "kid": "test-key"}, claims,
                          jwk.OctKey.generate_key(256), algorithms=["HS256"])
    else:
        raise AssertionError(f"Unknown test case: {failure}")
    return jwt.encode({"alg": "RS256", "kid": "test-key"}, claims,
                      jwk.import_key(keys.private_key.get_secret_value(), "RSA"), algorithms=["RS256"])


@pytest.mark.parametrize("transport", TRANSPORTS)
@pytest.mark.parametrize("failure,status", [
    ("absent", 401), ("malformed", 401), ("signature", 401), ("issuer", 401),
    ("audience", 401), ("expired", 401), ("missing_scope", 403), ("wrong_scope", 403),
    ("missing_exp", 401), ("missing_issuer", 401), ("missing_audience", 401),
    ("future_nbf", 401), ("invalid_nbf", 401), ("algorithm", 401),
    ("infinite_exp", 401), ("nan_nbf", 401), ("boolean_nbf", 401),
    ("nan_exp", 401), ("boolean_exp", 401), ("invalid_exp", 401),
    ("numeric_string_exp", 401), ("null_exp", 401),
])
def test_http_middleware_rejects_before_tool_execution(
    monkeypatch, configured, keys, transport, failure, status,
):
    auth = auth_with_keys(monkeypatch, keys, transport)
    app, executions = protected_app(auth, transport)
    headers = dict(HEADERS)
    if failure != "absent":
        headers["authorization"] = f"Bearer {invalid_token(keys, failure)}"
    with TestClient(app) as client:
        if transport == "sse":
            response = client.get("/sse", headers=headers)
            assert response.status_code == status
            response = client.post("/messages/?session_id=does-not-exist", headers=headers, json=CALL)
        else:
            response = client.post("/mcp", headers=headers, json=CALL)
        assert response.status_code == status
        assert 'scope="oraviz:read"' in response.headers["www-authenticate"]
        if status == 403:
            assert response.json()["error"] == "insufficient_scope"
    assert executions == []


@pytest.mark.parametrize("transport", TRANSPORTS)
@pytest.mark.parametrize("subject", [
    pytest.param(..., id="missing"), pytest.param(None, id="null"),
    pytest.param("", id="empty"), pytest.param(" \t\n", id="whitespace"),
    pytest.param(123, id="number"), pytest.param(True, id="boolean"),
    pytest.param(["agent"], id="array"), pytest.param({"id": "agent"}, id="object"),
])
def test_signed_token_requires_attributable_subject(
    monkeypatch, configured, keys, transport, subject,
):
    claims = {
        "iss": AUTH_ENV["ORACLE_MCP_AUTH_ISSUER"], "aud": "oraviz",
        "scope": "oraviz:read", "exp": int(time.time()) + 600,
        "client_id": "client-id-is-not-a-subject", "azp": "authorized-party",
    }
    if subject is not ...:
        claims["sub"] = subject
    signed = jwt.encode(
        {"alg": "RS256", "kid": "test-key"}, claims,
        jwk.import_key(keys.private_key.get_secret_value(), "RSA"), algorithms=["RS256"],
    )
    app, executions = protected_app(auth_with_keys(monkeypatch, keys, transport), transport)
    headers = {**HEADERS, "authorization": f"Bearer {signed}"}
    with TestClient(app) as client:
        if transport == "sse":
            assert client.get("/sse", headers=headers).status_code == 401
            response = client.post("/messages/", headers=headers, json=CALL)
        else:
            response = client.post("/mcp", headers=headers, json=CALL)
        assert response.status_code == 401
    assert executions == []


@pytest.mark.asyncio
async def test_verified_subject_is_preserved_for_audit(monkeypatch, configured, keys):
    auth = auth_with_keys(monkeypatch, keys)
    verified = await auth.verify_token(token(
        keys, subject="agent:123", additional_claims={"client_id": "oauth-client"},
    ))
    assert verified is not None
    assert verified.subject == "agent:123"
    assert verified.claims["sub"] == "agent:123"


@pytest.mark.parametrize("transport", ["http", "streamable-http"])
def test_authorized_tool_call(monkeypatch, configured, keys, transport):
    auth = auth_with_keys(monkeypatch, keys, transport)
    app, executions = protected_app(auth, transport)
    headers = {**HEADERS, "authorization": f"Bearer {token(keys)}"}
    with TestClient(app) as client:
        response = client.post("/mcp", headers=headers, json=CALL)
        assert response.status_code == 200
        assert response.json()["result"]["content"][0]["text"] == "authorized result"
    assert executions == ["read"]
    auth.token_verifier._fetch_jwks.assert_awaited_once()


@pytest.mark.parametrize("transport", ["http", "streamable-http"])
@pytest.mark.parametrize("method", ["GET", "DELETE"])
def test_session_endpoints_require_auth(configured, transport, method):
    app = FastMCP("Session auth", auth=build_auth(transport)).http_app(transport=transport)
    with TestClient(app) as client:
        response = client.request(method, "/mcp", headers=HEADERS)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_scopes_in_scp_and_multiple_audiences(monkeypatch, configured, keys):
    auth = auth_with_keys(monkeypatch, keys)
    verified = await auth.verify_token(token(
        keys, scopes=[], audience=["another-resource", "oraviz"],
        additional_claims={"scp": ["oraviz:read"], "nbf": int(time.time()) - 10},
    ))
    assert verified is not None
    assert verified.scopes == ["oraviz:read"]


@pytest.mark.parametrize("transport,path", [("http", "/mcp"), ("streamable-http", "/mcp"), ("sse", "/sse")])
def test_native_authorization_discovery(monkeypatch, configured, transport, path):
    monkeypatch.setenv("ORACLE_MCP_AUTH_BASE_URL", "https://oraviz.example.com")
    app, executions = protected_app(build_auth(transport), transport)
    with TestClient(app) as client:
        response = (client.get(path) if transport == "sse" else client.post(path, json=CALL))
        assert response.status_code == 401
        metadata_path = f"/.well-known/oauth-protected-resource{path}"
        assert f'https://oraviz.example.com{metadata_path}' in response.headers["www-authenticate"]
        metadata = client.get(metadata_path)
        assert metadata.status_code == 200
        assert metadata.json()["resource"] == f"https://oraviz.example.com{path}"
        assert metadata.json()["authorization_servers"] == ["https://identity.example.com/"]
        assert metadata.json()["scopes_supported"] == ["oraviz:read"]
    assert executions == []


@pytest.mark.asyncio
async def test_jwks_failure_is_closed_and_logs_no_raw_exception(monkeypatch, configured, keys, caplog):
    auth = auth_with_keys(monkeypatch, keys)
    auth.token_verifier._fetch_jwks.side_effect = ValueError("raw-exception-secret")
    with caplog.at_level(logging.DEBUG):
        assert await auth.verify_token(token(keys)) is None
    assert "raw-exception-secret" not in caplog.text
    assert "Bearer token verification did not succeed" in caplog.text


@pytest.mark.asyncio
async def test_untrusted_claims_are_not_logged(monkeypatch, configured, keys, caplog):
    auth = auth_with_keys(monkeypatch, keys)
    with caplog.at_level(logging.DEBUG):
        assert await auth.verify_token(token(keys, issuer="untrusted-issuer-secret")) is None
    assert "untrusted-issuer-secret" not in caplog.text


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_direct_server_import_requires_auth(transport):
    environment = {key: value for key, value in os.environ.items() if not key.startswith("ORACLE_MCP_AUTH_")}
    environment["ORACLE_MCP_SERVER_TRANSPORT"] = transport
    result = subprocess.run(
        [sys.executable, "-c", "import dotenv; dotenv.load_dotenv = lambda: False; import oraviz_mcp.server"],
        env=environment, capture_output=True, text=True, timeout=20,
    )
    assert result.returncode != 0
    assert "ORACLE_MCP_AUTH_ISSUER" in result.stderr


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_cli_import_error_is_clean_and_uses_stderr(transport):
    environment = {key: value for key, value in os.environ.items() if not key.startswith("ORACLE_MCP_AUTH_")}
    environment["ORACLE_MCP_SERVER_TRANSPORT"] = transport
    result = subprocess.run(
        [sys.executable, "-c", "import dotenv; dotenv.load_dotenv = lambda: False; from oraviz_mcp.main import run_server; run_server()"],
        env=environment, capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert "ORACLE_MCP_AUTH_ISSUER" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_real_app_network_override_requires_auth(transport):
    environment = {key: value for key, value in os.environ.items() if not key.startswith("ORACLE_MCP_AUTH_")}
    environment["ORACLE_MCP_SERVER_TRANSPORT"] = "stdio"
    script = f"""
import dotenv
dotenv.load_dotenv = lambda: False
from starlette.testclient import TestClient
from oraviz_mcp.server import mcp
with TestClient(mcp.http_app(transport={transport!r})) as client:
    response = client.get('/sse') if {transport!r} == 'sse' else client.post('/mcp', json={CALL!r})
    assert response.status_code == 401, response.status_code
"""
    result = subprocess.run(
        [sys.executable, "-c", script], env=environment, capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.asyncio
async def test_stdio_protocol_remains_usable_without_network_auth():
    script = """
from fastmcp import FastMCP
from oraviz_mcp.transport_security import build_auth
app = FastMCP('Local identity', auth=build_auth('stdio'))
@app.tool
def local_read() -> str:
    return 'local access'
app.run(transport='stdio', show_banner=False)
"""
    transport = StdioTransport(command=sys.executable, args=["-c", script], keep_alive=False)
    async with Client(transport, timeout=10) as client:
        result = await client.call_tool("local_read")
        assert result.content[0].text == "local access"
