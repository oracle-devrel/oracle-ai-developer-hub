"""Test BM25 search."""
from ragcli.search.bm25 import escape_oracle_text, BM25Search
from unittest.mock import MagicMock


def test_escape_simple():
    assert escape_oracle_text("hello") == "hello"


def test_escape_multi_word():
    result = escape_oracle_text("oracle database")
    assert "OR" in result


def test_escape_special_chars():
    result = escape_oracle_text("test & value")
    assert "\\&" in result


def test_search_empty_query():
    mock_conn = MagicMock()
    bm25 = BM25Search(mock_conn)
    result = bm25.search("   ", top_k=10)
    assert result == []


def test_search_calls_db():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [("c1", "d1", "text content", 1, 8.5)]
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    bm25 = BM25Search(mock_conn)
    results = bm25.search("oracle", top_k=5)
    assert len(results) == 1
    assert results[0]["chunk_id"] == "c1"
    assert results[0]["bm25_score"] == 8.5
