"""Test knowledge graph store."""
from unittest.mock import MagicMock
from ragcli.knowledge.graph_store import GraphStore


def test_upsert_entity_new():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    store = GraphStore(mock_conn)
    entity_id = store.upsert_entity("Python", "TECHNOLOGY", "A language", doc_id="doc1")
    assert entity_id is not None
    assert len(entity_id) == 36


def test_upsert_entity_existing():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = ("existing-id",)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    store = GraphStore(mock_conn)
    entity_id = store.upsert_entity("Python", "TECHNOLOGY", "A language")
    assert entity_id == "existing-id"


def test_insert_relationship():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    store = GraphStore(mock_conn)
    rel_id = store.insert_relationship("src-id", "tgt-id", "USES", "desc", "chunk1", "doc1")
    assert rel_id is not None
    assert len(rel_id) == 36


def test_get_entity_chunks_empty():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    store = GraphStore(mock_conn)
    chunks = store.get_entity_chunks("entity-1")
    assert chunks == []
