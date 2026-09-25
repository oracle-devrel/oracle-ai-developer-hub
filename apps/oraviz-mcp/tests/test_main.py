"""Entry-point validation without database connections or listening sockets."""

import os
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from oraviz_mcp import main
from oraviz_mcp.transport_security import TransportSecurityError, build_auth


@pytest.fixture
def server(monkeypatch):
    for name in list(os.environ):
        if name.startswith("ORACLE_MCP_AUTH_"):
            monkeypatch.delenv(name)
    server = SimpleNamespace(
        config=SimpleNamespace(
            user="database-user-secret",
            password="database-password-secret",
            dsn="database-dsn-secret",
            max_rows=500,
            ensure_configured=MagicMock(),
            mcp_server_config=SimpleNamespace(
                mcp_server_transport="stdio", mcp_bind_host="127.0.0.1", mcp_bind_port=8080
            ),
        ),
        mcp=MagicMock(auth=None),
        TransportType=SimpleNamespace(values=lambda: ["stdio", "http", "sse", "streamable-http"]),
    )
    monkeypatch.setattr(main, "_load_server", lambda: server)
    return server


def configure_network(monkeypatch, server, transport="http"):
    for name, value in {
        "ISSUER": "https://identity.example.com",
        "AUDIENCE": "oraviz",
        "JWKS_URL": "https://identity.example.com/jwks",
        "REQUIRED_SCOPES": "oraviz:read",
    }.items():
        monkeypatch.setenv(f"ORACLE_MCP_AUTH_{name}", value)
    server.config.mcp_server_config.mcp_server_transport = transport
    server.mcp.auth = build_auth(transport)


class TestSetupEnvironment:
    def test_success(self, server):
        assert main.setup_environment() is True
        server.config.ensure_configured.assert_called_once_with()

    def test_database_security_validation_is_sanitized(self, monkeypatch, server):
        server.config.ensure_configured.side_effect = ValueError("database-secret")
        recorder = MagicMock()
        monkeypatch.setattr(main, "logger", recorder)
        assert main.setup_environment() is False
        assert "database-secret" not in repr(recorder.mock_calls)
        assert "non-administrative" in repr(recorder.mock_calls)

    @pytest.mark.parametrize("field", ["user", "password"])
    def test_missing_database_configuration(self, server, field):
        setattr(server.config, field, "")
        assert main.setup_environment() is False

    def test_missing_transport_config(self, server):
        server.config.mcp_server_config = None
        assert main.setup_environment() is False

    def test_invalid_transport(self, server):
        server.config.mcp_server_config.mcp_server_transport = "carrier-pigeon-secret"
        assert main.setup_environment() is False

    @pytest.mark.parametrize("port", [0, -1, 65536, None, "port-secret", True, 8080.5])
    def test_invalid_network_port(self, monkeypatch, server, port):
        configure_network(monkeypatch, server)
        server.config.mcp_server_config.mcp_bind_port = port
        assert main.setup_environment() is False

    def test_stdio_needs_no_network_port(self, server):
        server.config.mcp_server_config.mcp_bind_port = None
        assert main.setup_environment() is True

    @pytest.mark.parametrize("transport", ["http", "sse", "streamable-http"])
    def test_network_auth_configuration_required(self, server, transport):
        server.config.mcp_server_config.mcp_server_transport = transport
        assert main.setup_environment() is False

    def test_missing_auth_instance_fails_closed(self, monkeypatch, server):
        configure_network(monkeypatch, server)
        server.mcp.auth = None
        assert main.setup_environment() is False

    def test_changed_auth_environment_requires_restart(self, monkeypatch, server):
        configure_network(monkeypatch, server)
        monkeypatch.setenv("ORACLE_MCP_AUTH_AUDIENCE", "another-resource")
        assert main.setup_environment() is False

    def test_logs_no_credentials_or_dsn(self, monkeypatch, server):
        recorder = MagicMock()
        monkeypatch.setattr(main, "logger", recorder)
        assert main.setup_environment() is True
        recorder.info.assert_called_once_with("Oracle configuration loaded", max_rows=500)
        assert "secret" not in repr(recorder.mock_calls)

    def test_invalid_config_values_are_not_logged(self, monkeypatch, server):
        configure_network(monkeypatch, server)
        recorder = MagicMock()
        monkeypatch.setattr(main, "logger", recorder)
        server.config.mcp_server_config.mcp_bind_port = "port-secret"
        assert main.setup_environment() is False
        assert "secret" not in repr(recorder.mock_calls)


class TestRunServer:
    def test_stdio_transport(self, server):
        main.run_server()
        server.mcp.run.assert_called_once_with(transport="stdio")

    @pytest.mark.parametrize("transport", ["http", "sse", "streamable-http"])
    def test_network_reuses_existing_auth(self, monkeypatch, server, transport):
        configure_network(monkeypatch, server, transport)
        from oraviz_mcp import transport_security

        constructor = MagicMock(side_effect=AssertionError("must reuse auth"))
        monkeypatch.setattr(transport_security, "JWTVerifier", constructor)
        main.run_server()
        constructor.assert_not_called()
        server.mcp.run.assert_called_once_with(transport=transport, host="127.0.0.1", port=8080)

    def test_failed_setup_exits_before_run(self, server):
        server.config.password = ""
        with pytest.raises(SystemExit) as error:
            main.run_server()
        assert error.value.code == 1
        server.mcp.run.assert_not_called()

    @pytest.mark.parametrize("transport", ["http", "sse", "streamable-http"])
    def test_no_unauthenticated_listener(self, server, transport):
        server.config.mcp_server_config.mcp_server_transport = transport
        with pytest.raises(SystemExit):
            main.run_server()
        server.mcp.run.assert_not_called()

    @pytest.mark.parametrize(
        "error",
        [TransportSecurityError("Network transports require ORACLE_MCP_AUTH_ISSUER"),
         ValueError("database-password-secret"), TypeError("database-dsn-secret")],
    )
    def test_import_configuration_errors_are_sanitized(self, monkeypatch, error):
        monkeypatch.setattr(main, "_load_server", MagicMock(side_effect=error))
        recorder = MagicMock()
        monkeypatch.setattr(main, "logger", recorder)
        with pytest.raises(SystemExit) as stopped:
            main.run_server()
        assert stopped.value.code == 1
        assert "secret" not in repr(recorder.mock_calls)
        assert main.setup_environment() is False


def test_environment_loaded_before_server_import(monkeypatch):
    events = []
    monkeypatch.setattr(main.dotenv, "load_dotenv", lambda: events.append("dotenv"))
    monkeypatch.setattr(main.importlib, "import_module", lambda name: events.append(name))
    main._load_server()
    assert events == ["dotenv", "oraviz_mcp.server"]


def test_package_exports_remain_available():
    import oraviz_mcp
    from oraviz_mcp.server import config, mcp

    assert oraviz_mcp.config is config
    assert oraviz_mcp.mcp is mcp
    assert {"config", "mcp", "__version__"} <= set(dir(oraviz_mcp))
    with pytest.raises(AttributeError, match="has no attribute"):
        getattr(oraviz_mcp, "missing_export")


def test_package_import_does_not_construct_server():
    environment = {key: value for key, value in os.environ.items() if not key.startswith("ORACLE_MCP_AUTH_")}
    environment["ORACLE_MCP_SERVER_TRANSPORT"] = "http"
    result = subprocess.run(
        [sys.executable, "-c", "import sys, oraviz_mcp; assert 'oraviz_mcp.server' not in sys.modules"],
        env=environment, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == result.stderr == ""
