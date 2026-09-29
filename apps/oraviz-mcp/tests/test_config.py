#!/usr/bin/env python
"""
Tests for Oracle Viz MCP configuration handling.
"""

import pytest

from oraviz_mcp.server import (
    MCPServerConfig,
    OracleConfig,
    TransportType,
    _int_env,
    config,
)


class TestTransportType:
    def test_values(self):
        assert set(TransportType.values()) == {"stdio", "http", "sse", "streamable-http"}

    def test_is_str_enum(self):
        assert TransportType.STDIO == "stdio"


class TestMCPServerConfig:
    def test_valid(self):
        cfg = MCPServerConfig(
            mcp_server_transport="stdio", mcp_bind_host="127.0.0.1", mcp_bind_port=8080
        )
        assert cfg.mcp_server_transport == "stdio"

    def test_missing_transport(self):
        with pytest.raises(ValueError, match="TRANSPORT"):
            MCPServerConfig(mcp_server_transport="", mcp_bind_host="127.0.0.1", mcp_bind_port=8080)

    def test_missing_host(self):
        with pytest.raises(ValueError, match="BIND HOST"):
            MCPServerConfig(mcp_server_transport="stdio", mcp_bind_host="", mcp_bind_port=8080)

    def test_missing_port(self):
        with pytest.raises(ValueError, match="BIND PORT"):
            MCPServerConfig(mcp_server_transport="stdio", mcp_bind_host="127.0.0.1", mcp_bind_port=0)


class TestOracleConfig:
    def _config(self, **overrides):
        values = dict(user="scott", password="tiger", host="localhost", port=1521, service="FREEPDB1")
        values.update(overrides)
        return OracleConfig(**values)

    def test_connection_dsn_from_parts(self):
        assert self._config().connection_dsn() == "localhost:1521/FREEPDB1"

    def test_connection_dsn_prefers_explicit_dsn(self):
        assert self._config(dsn="db.example.com:1521/FREEPDB1").connection_dsn() == (
            "db.example.com:1521/FREEPDB1"
        )

    def test_ensure_configured_ok(self):
        self._config().ensure_configured()

    def test_ensure_configured_rejects_missing_user(self):
        with pytest.raises(ValueError, match="ORACLE_USER"):
            self._config(user="").ensure_configured()

    def test_ensure_configured_rejects_missing_password(self):
        with pytest.raises(ValueError, match="ORACLE_USER"):
            self._config(password="").ensure_configured()

    def test_context_defaults(self):
        cfg = self._config()
        assert cfg.max_rows == 500
        assert cfg.preview_rows == 25
        assert cfg.max_cell_chars == 500
        assert cfg.connect_timeout == 10
        assert cfg.call_timeout == 60

    def test_repr_hides_secrets(self):
        cfg = self._config(password="tiger", wallet_password="wallet-secret")
        assert "tiger" not in repr(cfg)
        assert "wallet-secret" not in repr(cfg)


class TestIntEnv:
    def test_reads_integer(self, monkeypatch):
        monkeypatch.setenv("ORAVIZ_TEST_INT", "42")
        assert _int_env("ORAVIZ_TEST_INT", 7) == 42

    def test_defaults_when_unset(self, monkeypatch):
        monkeypatch.delenv("ORAVIZ_TEST_INT", raising=False)
        assert _int_env("ORAVIZ_TEST_INT", 7) == 7

    def test_defaults_when_blank(self, monkeypatch):
        monkeypatch.setenv("ORAVIZ_TEST_INT", "   ")
        assert _int_env("ORAVIZ_TEST_INT", 7) == 7

    def test_defaults_when_invalid(self, monkeypatch):
        monkeypatch.setenv("ORAVIZ_TEST_INT", "not-a-number")
        assert _int_env("ORAVIZ_TEST_INT", 7) == 7

    def test_minimum_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("ORAVIZ_TEST_INT", "-5")
        assert _int_env("ORAVIZ_TEST_INT", 7, minimum=1) == 7

    def test_minimum_accepts_the_boundary(self, monkeypatch):
        monkeypatch.setenv("ORAVIZ_TEST_INT", "0")
        assert _int_env("ORAVIZ_TEST_INT", 7, minimum=0) == 0

    def test_module_config_is_wired(self):
        assert isinstance(config.port, int)
        assert isinstance(config.max_rows, int)
        assert config.mcp_server_config is not None
