# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""In-memory, server-side sessions for the non-production learning app."""

import secrets
import time
from dataclasses import dataclass, field
from threading import Lock

from deepsec_webapp.oauth import EndUserToken

_ANONYMOUS_SESSION_TTL_SECONDS = 10 * 60
_MAX_SESSIONS = 1024


class SessionCapacityError(RuntimeError):
    """Report that the bounded learning-app session store is full."""


@dataclass
class DemoSession:
    """Authentication state stored only in the web process."""

    oauth_state: str | None = None
    code_verifier: str | None = None
    end_user_token: EndUserToken | None = None
    csrf_token: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    created_at: float = field(default_factory=time.time)


class DemoSessionStore:
    """Bounded process-local session store, intentionally unsuitable for production."""

    def __init__(self) -> None:
        self._sessions: dict[str, DemoSession] = {}
        self._lock = Lock()

    def create(self) -> tuple[str, DemoSession]:
        """Create a session and return its opaque identifier."""
        session = DemoSession()
        with self._lock:
            self._delete_expired_locked(time.time())
            if len(self._sessions) >= _MAX_SESSIONS:
                raise SessionCapacityError("The learning-app session store is full.")
            session_id = self._new_session_id_locked()
            self._sessions[session_id] = session
        return session_id, session

    def get(self, session_id: str | None) -> DemoSession | None:
        """Return an unexpired session."""
        if session_id is None:
            return None
        with self._lock:
            self._delete_expired_locked(time.time())
            return self._sessions.get(session_id)

    def authenticate(
        self,
        session_id: str,
        session: DemoSession,
        end_user_token: EndUserToken,
    ) -> tuple[str, DemoSession] | None:
        """Replace a pre-login session with a fresh authenticated session.

        Changing the opaque identifier and CSRF token at the authentication
        boundary prevents an attacker-selected anonymous session from becoming
        the victim's authenticated session.
        """
        with self._lock:
            self._delete_expired_locked(time.time())
            if self._sessions.get(session_id) is not session:
                return None
            del self._sessions[session_id]
            authenticated_session = DemoSession(end_user_token=end_user_token)
            authenticated_session_id = self._new_session_id_locked()
            self._sessions[authenticated_session_id] = authenticated_session
            return authenticated_session_id, authenticated_session

    def delete(self, session_id: str | None) -> None:
        """Delete a session without revealing whether it existed."""
        if session_id is None:
            return
        with self._lock:
            self._sessions.pop(session_id, None)

    def _new_session_id_locked(self) -> str:
        """Return a random identifier not already present while holding the lock."""
        while True:
            session_id = secrets.token_urlsafe(32)
            if session_id not in self._sessions:
                return session_id

    def _delete_expired_locked(self, now: float) -> None:
        """Remove expired login attempts and access-token sessions."""
        expired_ids = [
            session_id
            for session_id, session in self._sessions.items()
            if (
                session.end_user_token.expires_at
                if session.end_user_token is not None
                else session.created_at + _ANONYMOUS_SESSION_TTL_SECONDS
            )
            <= now
        ]
        for session_id in expired_ids:
            del self._sessions[session_id]
