"""Test session manager."""
from unittest.mock import MagicMock, patch
from ragcli.memory.session import SessionManager


def test_create_session():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    manager = SessionManager(mock_conn)
    session_id = manager.create_session()

    assert session_id is not None
    assert len(session_id) == 36
    mock_cursor.execute.assert_called_once()


def test_add_turn():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    manager = SessionManager(mock_conn)
    turn_id = manager.add_turn(
        session_id="test-session-id",
        turn_number=1,
        user_query="What is RAG?",
        rewritten_query="What is RAG?",
        response="RAG is retrieval-augmented generation.",
    )

    assert turn_id is not None
    assert len(turn_id) == 36


def test_get_recent_turns():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("turn1", "sess1", 1, "query1", "rewritten1", "response1", None, None, None),
    ]
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    manager = SessionManager(mock_conn)
    turns = manager.get_recent_turns("sess1", limit=5)

    assert len(turns) == 1
    assert turns[0]["user_query"] == "query1"


def test_get_turn_count():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (3,)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    manager = SessionManager(mock_conn)
    count = manager.get_turn_count("sess1")
    assert count == 3
