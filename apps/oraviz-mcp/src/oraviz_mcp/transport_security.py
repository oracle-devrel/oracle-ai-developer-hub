"""Fail-closed authentication for all network MCP transports.

Operators must set ORACLE_MCP_AUTH_ISSUER, ORACLE_MCP_AUTH_AUDIENCE,
ORACLE_MCP_AUTH_JWKS_URL and ORACLE_MCP_AUTH_REQUIRED_SCOPES (space-separated,
for example ``oraviz:read``). Issuer and JWKS URLs must use HTTPS. Optional
ORACLE_MCP_AUTH_BASE_URL is the public HTTPS server base URL, including any
proxy mount prefix but excluding /mcp or /sse; it enables OAuth discovery.
Tokens must use RS256 and include an expiry and a nonblank string subject.
TLS for incoming connections is
the deployment's responsibility, typically at a trusted reverse proxy.

Stdio retains the local operating-system identity boundary. An unconfigured
stdio app carries a denying HTTP provider, so programmatic or CLI transport
overrides cannot silently expose it. All authenticated network callers share
the configured Oracle account and its database grants:
token identity and scopes do not provide per-user row authorization.
"""

from __future__ import annotations

import logging
import math
import os
import re
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

from fastmcp.server.auth import AccessToken, AuthProvider, RemoteAuthProvider, TokenVerifier
from fastmcp.server.auth.providers.jwt import JWTVerifier
from pydantic import AnyHttpUrl

NETWORK_TRANSPORTS = frozenset({"http", "sse", "streamable-http"})


class TransportSecurityError(ValueError):
    """Invalid operator configuration; messages never contain supplied values."""


class _SafeVerifierLogger(logging.LoggerAdapter):
    """Discard upstream messages containing token claims or raw exceptions."""

    def log(self, level, msg, *args, **kwargs):
        super().log(level, "Bearer token verification did not succeed")


@dataclass(frozen=True)
class _AuthSettings:
    issuer: str
    audience: str
    jwks_url: str
    required_scopes: tuple[str, ...]
    base_url: str | None


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise TransportSecurityError(f"Network transports require {name}")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise TransportSecurityError(f"Invalid characters in {name}")
    return value


def _https_url(name: str, value: str) -> str:
    try:
        parsed = urlsplit(value)
        valid = (
            parsed.scheme == "https"
            and parsed.hostname
            and parsed.username is None
            and parsed.password is None
            and not parsed.query
            and not parsed.fragment
            and not any(char.isspace() for char in value)
            and "\\" not in value
            and (parsed.port is None or 1 <= parsed.port <= 65535)
        )
        if valid:
            AnyHttpUrl(value)
            return value
    except ValueError:
        pass
    raise TransportSecurityError(
        f"{name} must be an HTTPS URL without credentials, query, or fragment"
    ) from None


def _settings(transport: str) -> _AuthSettings:
    if transport not in NETWORK_TRANSPORTS:
        raise TransportSecurityError("Unsupported ORACLE_MCP_SERVER_TRANSPORT")
    issuer = _https_url("ORACLE_MCP_AUTH_ISSUER", _required("ORACLE_MCP_AUTH_ISSUER"))
    audience = _required("ORACLE_MCP_AUTH_AUDIENCE")
    jwks_url = _https_url("ORACLE_MCP_AUTH_JWKS_URL", _required("ORACLE_MCP_AUTH_JWKS_URL"))
    scopes = tuple(_required("ORACLE_MCP_AUTH_REQUIRED_SCOPES").split())
    # RFC 6749 scope-token syntax also keeps challenges safe to put in headers.
    if any(re.fullmatch(r'[\x21\x23-\x5b\x5d-\x7e]+', scope) is None for scope in scopes):
        raise TransportSecurityError("Invalid ORACLE_MCP_AUTH_REQUIRED_SCOPES")
    base_url = None
    if "ORACLE_MCP_AUTH_BASE_URL" in os.environ:
        base_url = _https_url("ORACLE_MCP_AUTH_BASE_URL", _required("ORACLE_MCP_AUTH_BASE_URL"))
    return _AuthSettings(issuer, audience, jwks_url, scopes, base_url)


class _NetworkAuth(TokenVerifier):
    """Delegate JWT crypto to FastMCP and scope enforcement to its middleware."""

    def __init__(self, settings: _AuthSettings):
        super().__init__(base_url=settings.base_url, required_scopes=list(settings.required_scopes))
        self.settings = settings
        # Scopes belong on this provider so valid, under-scoped tokens get 403.
        self.token_verifier = JWTVerifier(
            issuer=settings.issuer,
            audience=settings.audience,
            jwks_uri=settings.jwks_url,
            algorithm="RS256",
        )
        self.token_verifier.logger = _SafeVerifierLogger(logging.getLogger(__name__), {})

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            verified = await self.token_verifier.verify_token(token)
        except OverflowError:
            # The upstream verifier converts exp to int; infinity is invalid.
            return None
        if verified is None or verified.expires_at is None:
            return None
        subject = verified.claims.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            # client_id/azp and the upstream "unknown" fallback do not identify
            # the user or agent to whom this token was issued.
            return None
        expires = verified.claims.get("exp")
        if (
            isinstance(expires, bool)
            or not isinstance(expires, (int, float))
            or (isinstance(expires, float) and not math.isfinite(expires))
            or expires <= time.time()
        ):
            return None
        # FastMCP 4.0.3 verifies exp when present but does not enforce nbf.
        # Examine only claims whose signatures have already been verified.
        not_before = verified.claims.get("nbf")
        if not_before is not None and (
            isinstance(not_before, bool)
            or not isinstance(not_before, (int, float))
            or not_before > time.time()
            or (isinstance(not_before, float) and not math.isfinite(not_before))
        ):
            return None
        return verified

    def get_routes(self, mcp_path: str | None = None) -> list:
        if self.base_url is None:
            return []
        # Use native RFC 9728 routes rather than implementing discovery.
        return RemoteAuthProvider(
            token_verifier=self,
            authorization_servers=[AnyHttpUrl(self.settings.issuer)],
            base_url=self.base_url,
        ).get_routes(mcp_path)


class _StdioOnlyAuth(TokenVerifier):
    """Stdio ignores HTTP auth, but a later network transport must deny access."""

    async def verify_token(self, token: str) -> None:
        return None


def build_auth(transport: str) -> AuthProvider:
    """Build auth during FastMCP construction, including direct app imports.

    Network transports cannot opt out. Stdio uses configured network auth when
    available, otherwise a denying provider; FastMCP does not apply it to stdio.
    No keys are fetched until a token arrives. Normalize transport names first.
    """
    if transport == "stdio":
        try:
            settings = _settings("http")
        except TransportSecurityError:
            return _StdioOnlyAuth()
        return _NetworkAuth(settings)
    settings = _settings(transport)
    return _NetworkAuth(settings)


def validate_auth(transport: str, auth: AuthProvider | None) -> None:
    """Validate the already-built provider without constructing another verifier."""
    if transport == "stdio":
        return
    settings = _settings(transport)
    if (
        not isinstance(auth, _NetworkAuth)
        or auth.settings != settings
        or auth.required_scopes != list(settings.required_scopes)
    ):
        raise TransportSecurityError(
            "Network authentication is not configured for this application; restart with the required environment"
        )
