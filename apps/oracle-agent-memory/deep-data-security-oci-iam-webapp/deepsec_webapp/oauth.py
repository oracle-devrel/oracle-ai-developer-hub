# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Small OAuth 2.0 Authorization Code and Client Credentials client."""

import base64
import hashlib
import json
import math
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from threading import Lock
from typing import Any

from deepsec_webapp.config import RuntimeConfig

# OAuth token responses are small. This limit avoids buffering an unbounded
# response from a misconfigured or compromised endpoint.
_MAX_TOKEN_RESPONSE_BYTES = 64 * 1024


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Refuse redirects so a client secret cannot be forwarded to another origin."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


_TOKEN_OPENER = urllib.request.build_opener(_NoRedirectHandler())


class OAuthError(RuntimeError):
    """Report a sanitized OCI IAM OAuth failure."""


@dataclass(frozen=True)
class AuthorizationRequest:
    """Values kept server-side while a browser authorization is in progress."""

    url: str
    state: str
    code_verifier: str


@dataclass(frozen=True)
class EndUserToken:
    """End-user access token returned by the authorization code flow."""

    access_token: str
    username: str
    expires_at: float


def _basic_authorization(client_id: str, client_secret: str) -> str:
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode("ascii")
    return f"Basic {credentials}"


def _token_request(config: RuntimeConfig, form: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{config.domain_url}/oauth2/v1/token",
        data=urllib.parse.urlencode(form).encode(),
        headers={
            "Authorization": _basic_authorization(
                config.oauth_client_id,
                config.oauth_client_secret,
            ),
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        },
        method="POST",
    )
    try:
        # A single socket timeout is sufficient for this small learning client;
        # production applications should also enforce an end-to-end deadline.
        with _TOKEN_OPENER.open(request, timeout=30) as response:
            if response.headers.get_content_type() != "application/json":
                raise OAuthError("OCI IAM returned an invalid token response.")
            body = response.read(_MAX_TOKEN_RESPONSE_BYTES + 1)
            if len(body) > _MAX_TOKEN_RESPONSE_BYTES:
                raise OAuthError("OCI IAM returned an invalid token response.")
            payload = json.loads(body)
    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise OAuthError("OCI IAM token request failed.") from exc
    if not isinstance(payload, dict):
        raise OAuthError("OCI IAM returned an invalid token response.")
    return payload


def _required_access_token(payload: dict[str, Any]) -> tuple[str, float]:
    access_token = payload.get("access_token")
    expires_in = payload.get("expires_in", 3600)
    if not isinstance(access_token, str) or not access_token:
        raise OAuthError("OCI IAM token response did not include an access token.")
    if (
        isinstance(expires_in, bool)
        or not isinstance(expires_in, int | float)
        or not math.isfinite(expires_in)
        or expires_in <= 0
    ):
        raise OAuthError("OCI IAM token response included an invalid expiration.")
    return access_token, time.time() + float(expires_in)


def _display_username(access_token: str) -> str:
    """Read the unverified subject claim for display, never authorization."""
    try:
        encoded_payload = access_token.split(".")[1]
        padding = "=" * (-len(encoded_payload) % 4)
        payload = json.loads(base64.urlsafe_b64decode(encoded_payload + padding))
    except (IndexError, ValueError, json.JSONDecodeError) as exc:
        raise OAuthError("OCI IAM returned an invalid end-user token.") from exc
    if not isinstance(payload, dict):
        raise OAuthError("OCI IAM returned an invalid end-user token.")
    username = payload.get("sub")
    if not isinstance(username, str) or not username:
        raise OAuthError("OCI IAM end-user token did not include a subject.")
    return username


# .. start-deepsec-oauth-authorization
def start_authorization(config: RuntimeConfig) -> AuthorizationRequest:
    """Build a state-bound Authorization Code request with PKCE."""
    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    query = urllib.parse.urlencode(
        {
            "client_id": config.oauth_client_id,
            "response_type": "code",
            "redirect_uri": config.redirect_uri,
            "scope": config.end_user_scope,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    return AuthorizationRequest(
        url=f"{config.domain_url}/oauth2/v1/authorize?{query}",
        state=state,
        code_verifier=code_verifier,
    )


def exchange_authorization_code(
    config: RuntimeConfig,
    code: str,
    code_verifier: str,
) -> EndUserToken:
    """Exchange one browser authorization code for an end-user token."""
    payload = _token_request(
        config,
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config.redirect_uri,
            "code_verifier": code_verifier,
        },
    )
    access_token, expires_at = _required_access_token(payload)
    return EndUserToken(
        access_token=access_token,
        username=_display_username(access_token),
        expires_at=expires_at,
    )


# .. end-deepsec-oauth-authorization


class DatabaseTokenProvider:
    """Cache the application's client-credentials token until near expiration."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._token: str | None = None
        self._expires_at = 0.0

    # .. start-deepsec-oauth-database-token
    def get(self, config: RuntimeConfig) -> str:
        """Return a current database-access token."""
        with self._lock:
            if self._token is not None and time.time() < self._expires_at - 60:
                return self._token
            payload = _token_request(
                config,
                {
                    "grant_type": "client_credentials",
                    "scope": config.database_access_scope,
                },
            )
            self._token, self._expires_at = _required_access_token(payload)
            return self._token

    # .. end-deepsec-oauth-database-token
