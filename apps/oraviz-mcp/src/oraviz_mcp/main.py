#!/usr/bin/env python
"""Validate configuration before starting the Oracle Viz MCP server.

Network tokens authorize access to the shared configured Oracle account, not
per-user database rows. Stdio uses the local operating-system identity model.
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType

import dotenv
import structlog

from oraviz_mcp.transport_security import NETWORK_TRANSPORTS, TransportSecurityError, validate_auth

logger = structlog.get_logger()


def _load_server() -> ModuleType:
    # Delay import so invalid import-time auth/configuration receives a clean
    # CLI error, while direct server imports still fail closed.
    dotenv.load_dotenv()
    return importlib.import_module("oraviz_mcp.server")


def setup_environment(server: ModuleType | None = None) -> bool:
    """Validate database, transport and the existing authentication provider."""
    try:
        server = server if server is not None else _load_server()
        config = server.config
        if not config.user:
            logger.error("Missing required configuration", variable="ORACLE_USER")
            return False
        if not config.password:
            logger.error("Missing required configuration", variable="ORACLE_PASSWORD")
            return False
        try:
            config.ensure_configured()
        except ValueError:
            logger.error(
                "Invalid Oracle configuration; require a non-administrative account and positive ORACLE_CALL_TIMEOUT"
            )
            return False

        mcp_config = config.mcp_server_config
        if mcp_config is None:
            logger.error("Missing MCP transport configuration")
            return False
        transport = mcp_config.mcp_server_transport
        if transport not in server.TransportType.values():
            logger.error("Invalid MCP transport", variable="ORACLE_MCP_SERVER_TRANSPORT")
            return False
        if transport in NETWORK_TRANSPORTS:
            try:
                port = int(mcp_config.mcp_bind_port)
                if (
                    isinstance(mcp_config.mcp_bind_port, (bool, float))
                    or not 1 <= port <= 65535
                ):
                    raise ValueError
            except (TypeError, ValueError):
                logger.error(
                    "Invalid MCP port",
                    variable="ORACLE_MCP_BIND_PORT",
                    expected="integer between 1 and 65535",
                )
                return False
        validate_auth(transport, server.mcp.auth)
    except TransportSecurityError as error:
        # This exception type contains only static messages and variable names.
        logger.error("Invalid MCP security configuration", reason=str(error))
        return False
    except (TypeError, ValueError):
        logger.error("Invalid server configuration; check operator environment variables")
        return False

    logger.info("Oracle configuration loaded", max_rows=config.max_rows)
    return True


def run_server() -> None:
    """Start the configured transport, with sanitized configuration failures."""
    # Configure stderr before importing server: its import may fail before its
    # own logging setup. stdout is reserved for the stdio MCP protocol.
    structlog.configure(logger_factory=structlog.PrintLoggerFactory(file=sys.stderr))
    try:
        server = _load_server()
    except TransportSecurityError as error:
        logger.error("Invalid MCP security configuration", reason=str(error))
        raise SystemExit(1) from None
    except (TypeError, ValueError):
        logger.error("Invalid server configuration; check operator environment variables")
        raise SystemExit(1) from None

    if not setup_environment(server):
        logger.error("Environment setup failed, exiting")
        raise SystemExit(1)

    mcp_config = server.config.mcp_server_config
    transport = mcp_config.mcp_server_transport
    logger.info("Starting Oracle Viz MCP Server", transport=transport)
    if transport in NETWORK_TRANSPORTS:
        server.mcp.run(
            transport=transport,
            host=mcp_config.mcp_bind_host,
            port=int(mcp_config.mcp_bind_port),
        )
    else:
        server.mcp.run(transport=transport)


if __name__ == "__main__":
    run_server()
