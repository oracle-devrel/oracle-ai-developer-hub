# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import argparse
import os

try:
    from .session_token import (
        DEFAULT_TOKEN_LIFETIME_MINUTES,
        MAX_TOKEN_LIFETIME_MINUTES,
        encode_session_token,
    )
except ImportError:  # Support running this tutorial file directly.
    from session_token import (  # type: ignore[no-redef]
        DEFAULT_TOKEN_LIFETIME_MINUTES,
        MAX_TOKEN_LIFETIME_MINUTES,
        encode_session_token,
    )


def _jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError(
            "JWT_SECRET must be set before creating OAM_MCP_TOKEN. Generate one with "
            "'openssl rand -hex 32', then use the same value when starting the MCP "
            "server."
        )
    return secret


def _token_lifetime(value: str) -> int:
    try:
        minutes = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be an integer number of minutes") from None
    if not 1 <= minutes <= MAX_TOKEN_LIFETIME_MINUTES:
        raise argparse.ArgumentTypeError(
            f"must be between 1 and {MAX_TOKEN_LIFETIME_MINUTES} minutes"
        )
    return minutes


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create a short-lived bearer token for the Codex Memory MCP server."
    )
    parser.add_argument(
        "--user-id",
        required=True,
        help="Authenticated user identifier whose memory scope the token may access.",
    )
    parser.add_argument(
        "--agent-id",
        required=True,
        help="Agent identifier whose memory scope the token may access.",
    )
    parser.add_argument(
        "--session-id",
        default="",
        help=(
            "Bind the token to one Codex conversation. If omitted, it may access any "
            "conversation for the same user and agent."
        ),
    )
    parser.add_argument(
        "--expires-in-minutes",
        type=_token_lifetime,
        default=DEFAULT_TOKEN_LIFETIME_MINUTES,
        metavar=f"1..{MAX_TOKEN_LIFETIME_MINUTES}",
        help=f"Token lifetime (default: {DEFAULT_TOKEN_LIFETIME_MINUTES} minutes).",
    )

    args = parser.parse_args()
    print(
        encode_session_token(
            args.user_id,
            args.agent_id,
            args.session_id,
            _jwt_secret(),
            lifetime_minutes=args.expires_in_minutes,
        )
    )
