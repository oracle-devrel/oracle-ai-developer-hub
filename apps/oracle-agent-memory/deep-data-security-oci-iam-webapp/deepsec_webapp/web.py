# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""HTTP routes for login, visible-memory listing, and memory creation."""

import hmac
from typing import Any

import oracledb
from flask import (
    Blueprint,
    Response,
    current_app,
    redirect,
    render_template,
    request,
    url_for,
)

from deepsec_webapp.config import RuntimeConfig
from deepsec_webapp.database import add_memory, list_visible_memories
from deepsec_webapp.oauth import (
    DatabaseTokenProvider,
    OAuthError,
    exchange_authorization_code,
    start_authorization,
)
from deepsec_webapp.sessions import DemoSession, DemoSessionStore, SessionCapacityError

web = Blueprint("web", __name__)
_SESSION_COOKIE = "oam_demo_session"
_database_tokens = DatabaseTokenProvider()


def _constant_time_text_equal(candidate: str, expected: str) -> bool:
    """Compare arbitrary Unicode request values without compare_digest type errors."""
    return hmac.compare_digest(candidate.encode("utf-8"), expected.encode("utf-8"))


def _extensions() -> tuple[RuntimeConfig, Any, DemoSessionStore]:
    return (
        current_app.extensions["deepsec_config"],
        current_app.extensions["deepsec_pool"],
        current_app.extensions["deepsec_sessions"],
    )


def _session() -> tuple[str | None, DemoSession | None]:
    _, _, sessions = _extensions()
    session_id = request.cookies.get(_SESSION_COOKIE)
    return session_id, sessions.get(session_id)


def _set_session_cookie(response: Response, session_id: str, config: RuntimeConfig) -> None:
    response.set_cookie(
        _SESSION_COOKIE,
        session_id,
        httponly=True,
        samesite="Lax",
        secure=config.secure_browser_transport,
        path="/",
        max_age=3600,
    )


def _security_context(config: RuntimeConfig, session: DemoSession) -> Any:
    if session.end_user_token is None:
        raise OAuthError("Authentication is required.")
    return oracledb.create_end_user_security_context(
        end_user_identity=session.end_user_token.access_token,
        database_access_token=_database_tokens.get(config),
    )


@web.get("/login")
def login() -> Response:
    """Start an OCI IAM Authorization Code flow."""
    config, _, sessions = _extensions()
    session_id, session = _session()
    if session is None:
        try:
            session_id, session = sessions.create()
        except SessionCapacityError:
            return render_template("error.html", message="The application is busy."), 503
    authorization = start_authorization(config)
    session.oauth_state = authorization.state
    session.code_verifier = authorization.code_verifier
    response = redirect(authorization.url)
    _set_session_cookie(response, session_id, config)
    return response


@web.get("/auth/callback")
def auth_callback() -> Response:
    """Validate the callback and retain the end-user token server-side."""
    config, _, sessions = _extensions()
    session_id, session = _session()
    state = request.args.get("state", "")
    code = request.args.get("code", "")
    if (
        session_id is None
        or session is None
        or session.oauth_state is None
        or session.code_verifier is None
        or not state
        or not _constant_time_text_equal(state, session.oauth_state)
        or not code
    ):
        return render_template("error.html", message="The login response was not valid."), 400
    try:
        end_user_token = exchange_authorization_code(
            config,
            code,
            session.code_verifier,
        )
    except OAuthError:
        return render_template("error.html", message="OCI IAM login failed."), 502
    finally:
        session.oauth_state = None
        session.code_verifier = None
    authenticated = sessions.authenticate(session_id, session, end_user_token)
    if authenticated is None:
        return render_template("error.html", message="The login response expired."), 400
    authenticated_session_id, _ = authenticated
    response = redirect(url_for("web.index"))
    _set_session_cookie(response, authenticated_session_id, config)
    return response


@web.post("/logout")
def logout() -> Response:
    """Delete the server-side session and browser cookie."""
    config, _, sessions = _extensions()
    session_id, session = _session()
    if session is None or not _constant_time_text_equal(
        request.form.get("csrf_token", ""), session.csrf_token
    ):
        # Do not clear a valid browser session when the logout request fails CSRF.
        return render_template("error.html", message="The form expired."), 400
    sessions.delete(session_id)
    response = redirect(url_for("web.index"))
    response.delete_cookie(
        _SESSION_COOKIE,
        httponly=True,
        samesite="Lax",
        secure=config.secure_browser_transport,
        path="/",
    )
    return response


# .. start-deepsec-web-route
@web.route("/", methods=["GET", "POST"])
def index() -> Response | tuple[str, int]:
    """Show visible memories and let the user attempt one insert."""
    config, pool, _ = _extensions()
    _, session = _session()
    if session is None or session.end_user_token is None:
        return render_template("index.html", session=None, memories=[])

    message = None
    status = 200
    try:
        user_context = _security_context(config, session)
        if request.method == "POST":
            if not _constant_time_text_equal(
                request.form.get("csrf_token", ""),
                session.csrf_token,
            ):
                return render_template("error.html", message="The form expired."), 400
            content = request.form.get("content", "").strip()
            target_username = request.form.get("username", "").strip()
            if not content or not target_username:
                message = "Content and username are required."
                status = 400
            elif len(content) > 4000 or len(target_username) > 255:
                message = "The submitted memory is too large."
                status = 400
            else:
                try:
                    add_memory(
                        config,
                        pool,
                        user_context,
                        content,
                        target_username,
                    )
                    message = "Memory added."
                except oracledb.DatabaseError:
                    # Keep listing permitted rows after the deliberately denied write.
                    message = "Oracle Database denied this operation for the effective end user."
                    status = 403

        memories = list_visible_memories(config, pool, user_context)
    except oracledb.DatabaseError:
        # Never expose raw database errors, token contents, or submitted values.
        message = "Oracle Database denied this operation for the effective end user."
        memories = []
        status = 403
    except OAuthError:
        message = "The login session expired. Sign in again."
        memories = []
        status = 401

    return (
        render_template(
            "index.html",
            session=session,
            memories=memories,
            message=message,
        ),
        status,
    )


# .. end-deepsec-web-route
