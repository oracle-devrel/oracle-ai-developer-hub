# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Shared creation and validation for the prototype's signed session tokens."""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

JWT_ALGORITHM = "HS256"
DEFAULT_TOKEN_LIFETIME_MINUTES = 60
MAX_TOKEN_LIFETIME_MINUTES = 24 * 60
MAX_ID_CHARS = 256
MIN_SECRET_BYTES = 32


def _required_id(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    value = value.strip()
    if len(value) > MAX_ID_CHARS:
        raise ValueError(f"{field_name} must be at most {MAX_ID_CHARS} characters")
    return value


def _optional_session_id(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("session_id must be a string")
    value = value.strip()
    if len(value) > MAX_ID_CHARS:
        raise ValueError(f"session_id must be at most {MAX_ID_CHARS} characters")
    return value


def _required_secret(secret: Any) -> str:
    if not isinstance(secret, str) or len(secret.encode("utf-8")) < MIN_SECRET_BYTES:
        raise ValueError(f"secret must contain at least {MIN_SECRET_BYTES} bytes")
    return secret


def encode_session_token(
    user_id: str,
    agent_id: str,
    session_id: str,
    secret: str,
    *,
    lifetime_minutes: int = DEFAULT_TOKEN_LIFETIME_MINUTES,
) -> str:
    """Create a short-lived token for one identity and, optionally, one session."""
    user_id = _required_id(user_id, "user_id")
    agent_id = _required_id(agent_id, "agent_id")
    session_id = _optional_session_id(session_id)
    secret = _required_secret(secret)
    if (
        isinstance(lifetime_minutes, bool)
        or not isinstance(lifetime_minutes, int)
        or not 1 <= lifetime_minutes <= MAX_TOKEN_LIFETIME_MINUTES
    ):
        raise ValueError(f"lifetime_minutes must be between 1 and {MAX_TOKEN_LIFETIME_MINUTES}")

    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "user_id": user_id,
            "agent_id": agent_id,
            "session_id": session_id,
            "iat": now,
            "exp": now + timedelta(minutes=lifetime_minutes),
        },
        secret,
        algorithm=JWT_ALGORITHM,
    )


def decode_session_token(token: str, secret: str) -> dict[str, str]:
    """Validate a token and return normalized identity fields."""
    if not isinstance(token, str) or not token:
        raise ValueError("Invalid token")
    try:
        secret = _required_secret(secret)
    except ValueError:
        raise ValueError("Invalid token") from None
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "iat", "user_id", "agent_id"]},
        )
    except ExpiredSignatureError:
        raise ValueError("Token has expired") from None
    except InvalidTokenError:
        raise ValueError("Invalid token") from None

    try:
        return {
            "user_id": _required_id(payload["user_id"], "user_id"),
            "agent_id": _required_id(payload["agent_id"], "agent_id"),
            "session_id": _optional_session_id(payload.get("session_id", "")),
        }
    except (KeyError, ValueError):
        raise ValueError("Invalid token") from None
