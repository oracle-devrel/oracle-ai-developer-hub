"""Tests for ragcli core modules."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from ragcli.core.rag_engine import upload_document, ask_query


@patch('ragcli.core.rag_engine.OracleClient')
@patch('ragcli.core.rag_engine.generate_embedding')
@patch('ragcli.core.rag_engine.insert_chunk')
@patch('ragcli.core.rag_engine.insert_document')
@patch('ragcli.core.rag_engine.get_document_metadata')
@patch('ragcli.core.rag_engine.chunk_text')
@patch('ragcli.core.rag_engine.preprocess_document')
def test_upload_document(mock_preprocess, mock_chunk, mock_meta, mock_insert_doc,
                         mock_insert_chunk, mock_emb, mock_client, tmp_path):
    """Test document upload with mocks."""
    # Create a real temp file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test text content for upload.")

    config = {
        'documents': {'chunk_size': 1000, 'chunk_overlap_percentage': 10,
                      'supported_formats': ['txt'], 'max_file_size_mb': 100},
        'ollama': {'embedding_model': 'test'},
        'vector_index': {'dimension': 768},
        'rag': {'top_k': 5, 'min_similarity_score': 0.5},
    }

    mock_preprocess.return_value = ("Test text content for upload.", False)
    mock_chunk.return_value = [{'text': 'Test text content', 'token_count': 5, 'char_count': 18}]
    mock_meta.return_value = {
        'chunk_count': 1,
        'total_tokens': 5,
        'extracted_text_size_bytes': 28,
        'ocr_processed': False,
    }
    mock_insert_doc.return_value = "test-doc-id"
    mock_emb.return_value = [0.1] * 768

    mock_conn = MagicMock()
    mock_client.return_value.get_connection.return_value = mock_conn

    metadata = upload_document(str(test_file), config)

    mock_insert_doc.assert_called_once()
    mock_insert_chunk.assert_called()
    assert metadata['chunk_count'] == 1
    assert metadata['document_id'] == 'test-doc-id'
    assert metadata['filename'] == 'test.txt'


@patch('ragcli.core.rag_engine.OracleClient')
@patch('ragcli.core.rag_engine.log_query')
@patch('ragcli.core.rag_engine.generate_response')
@patch('ragcli.core.rag_engine.search_chunks')
def test_ask_query(mock_search, mock_gen, mock_log, mock_client):
    """Test query asking with mocks."""
    config = {
        'rag': {'top_k': 5, 'min_similarity_score': 0.5},
        'ollama': {'chat_model': 'test', 'embedding_model': 'test'},
    }
    mock_search.return_value = {
        'results': [{'document_id': 'doc1', 'text': 'sample', 'similarity_score': 0.8}],
        'query_embedding': [0.1] * 768,
        'metrics': {'embedding_time_ms': 10, 'search_time_ms': 20},
    }
    mock_gen.return_value = "Sample answer"

    mock_conn = MagicMock()
    mock_client.return_value.get_connection.return_value = mock_conn

    result = ask_query("test query", config=config)

    assert result['response'] == "Sample answer"
    assert 'metrics' in result
    assert len(result['results']) == 1
