"""Session manager for conversational memory."""

import json
from typing import Dict, List, Optional

from ragcli.utils.helpers import generate_uuid
from ragcli.utils.logger import get_logger

logger = get_logger(__name__)


class SessionManager:
    """Manages conversation sessions and turns in Oracle DB."""

    def __init__(self, conn):
        """Initialize with a database connection.

        Args:
            conn: An oracledb connection object.
        """
        self.conn = conn

    def create_session(self, title: Optional[str] = None) -> str:
        """Create a new session and return its ID.

        Args:
            title: Optional session title.

        Returns:
            The generated session_id (UUID4 string).
        """
        session_id = generate_uuid()
        with self.conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO SESSIONS (session_id, title)
                   VALUES (:1, :2)""",
                [session_id, title],
            )
        self.conn.commit()
        logger.debug("Created session %s", session_id)
        return session_id

    def touch(self, session_id: str) -> None:
        """Update the last_active timestamp for a session.

        Args:
            session_id: The session to touch.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                """UPDATE SESSIONS SET last_active = SYSTIMESTAMP
                   WHERE session_id = :1""",
                [session_id],
            )
        self.conn.commit()

    def update_summary(self, session_id: str, summary: str) -> None:
        """Update the summary for a session.

        Args:
            session_id: The session to update.
            summary: New summary text.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                """UPDATE SESSIONS SET summary = :1
                   WHERE session_id = :2""",
                [summary, session_id],
            )
        self.conn.commit()

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get a session by ID.

        Args:
            session_id: The session to retrieve.

        Returns:
            Dict with session fields, or None if not found.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                """SELECT session_id, created_at, last_active, title, summary, metadata_json
                   FROM SESSIONS WHERE session_id = :1""",
                [session_id],
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return {
            "session_id": row[0],
            "created_at": row[1],
            "last_active": row[2],
            "title": row[3],
            "summary": row[4],
            "metadata_json": row[5],
        }

    def get_summary(self, session_id: str) -> Optional[str]:
        """Get the summary for a session.

        Args:
            session_id: The session to query.

        Returns:
            The summary string, or None.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT summary FROM SESSIONS WHERE session_id = :1",
                [session_id],
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return row[0]

    def add_turn(
        self,
        session_id: str,
        turn_number: int,
        user_query: str,
        rewritten_query: Optional[str] = None,
        response: Optional[str] = None,
        trace_id: Optional[str] = None,
        chunk_ids: Optional[List[str]] = None,
    ) -> str:
        """Add a turn to a session.

        Args:
            session_id: The session this turn belongs to.
            turn_number: Sequential turn number within the session.
            user_query: The user's original query.
            rewritten_query: The rewritten/expanded query (if any).
            response: The assistant's response.
            trace_id: Optional agent trace ID.
            chunk_ids: Optional list of chunk IDs used for context.

        Returns:
            The generated turn_id (UUID4 string).
        """
        turn_id = generate_uuid()
        chunk_ids_json = json.dumps(chunk_ids) if chunk_ids else None
        with self.conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO SESSION_TURNS
                   (turn_id, session_id, turn_number, user_query,
                    rewritten_query, response, trace_id, chunk_ids_json)
                   VALUES (:1, :2, :3, :4, :5, :6, :7, :8)""",
                [
                    turn_id,
                    session_id,
                    turn_number,
                    user_query,
                    rewritten_query,
                    response,
                    trace_id,
                    chunk_ids_json,
                ],
            )
        self.conn.commit()
        logger.debug("Added turn %s to session %s", turn_id, session_id)
        return turn_id

    def get_recent_turns(self, session_id: str, limit: int = 5) -> List[Dict]:
        """Get the most recent turns for a session in chronological order.

        Args:
            session_id: The session to query.
            limit: Maximum number of turns to return.

        Returns:
            List of turn dicts, ordered by turn_number ascending.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                """SELECT turn_id, session_id, turn_number, user_query,
                          rewritten_query, response, trace_id, chunk_ids_json, created_at
                   FROM SESSION_TURNS
                   WHERE session_id = :1
                   ORDER BY turn_number DESC
                   FETCH FIRST :2 ROWS ONLY""",
                [session_id, limit],
            )
            rows = cursor.fetchall()

        # Reverse to chronological order (ascending turn_number)
        rows = list(reversed(rows))
        return [
            {
                "turn_id": row[0],
                "session_id": row[1],
                "turn_number": row[2],
                "user_query": row[3],
                "rewritten_query": row[4],
                "response": row[5],
                "trace_id": row[6],
                "chunk_ids_json": row[7],
                "created_at": row[8],
            }
            for row in rows
        ]

    def get_turn_count(self, session_id: str) -> int:
        """Count the number of turns in a session.

        Args:
            session_id: The session to query.

        Returns:
            Number of turns.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM SESSION_TURNS WHERE session_id = :1",
                [session_id],
            )
            row = cursor.fetchone()
        return row[0] if row else 0

    def list_sessions(self, limit: int = 20) -> List[Dict]:
        """List recent sessions ordered by last activity.

        Args:
            limit: Maximum number of sessions to return.

        Returns:
            List of session dicts.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                """SELECT session_id, created_at, last_active, title, summary, metadata_json
                   FROM SESSIONS
                   ORDER BY last_active DESC
                   FETCH FIRST :1 ROWS ONLY""",
                [limit],
            )
            rows = cursor.fetchall()

        return [
            {
                "session_id": row[0],
                "created_at": row[1],
                "last_active": row[2],
                "title": row[3],
                "summary": row[4],
                "metadata_json": row[5],
            }
            for row in rows
        ]
