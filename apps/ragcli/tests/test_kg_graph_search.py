"""Test graph search."""
from unittest.mock import MagicMock
from ragcli.knowledge.graph_search import GraphSearch

TEST_CONFIG = {"knowledge_graph": {"max_hops": 2}}


def test_get_chunks_for_entities_empty():
    mock_conn = MagicMock()
    gs = GraphSearch(mock_conn, TEST_CONFIG)
    assert gs.get_chunks_for_entities([]) == []


def test_find_entities_by_embedding():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [("e1", "Python", "TECHNOLOGY", 0.1)]
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    gs = GraphSearch(mock_conn, TEST_CONFIG)
    results = gs.find_entities_by_embedding([0.1, 0.2, 0.3], top_k=5)
    assert len(results) == 1
    assert results[0]["name"] == "Python"


def test_get_chunks_for_entities():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [("chunk1",), ("chunk2",)]
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    gs = GraphSearch(mock_conn, TEST_CONFIG)
    chunks = gs.get_chunks_for_entities(["e1", "e2"])
    assert len(chunks) == 2
    assert "chunk1" in chunks
