"""Tests for ragcli status utilities."""

import pytest
from unittest.mock import Mock, patch
from ragcli.utils.status import (
    check_db_connection, get_document_stats, check_ollama, get_overall_status
)
from ragcli.config.config_manager import load_config

@pytest.fixture
def config():
    return load_config()

@patch('ragcli.utils.status.OracleClient')
def test_check_db_connection(mock_client, config):
    """Test DB connection check."""
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_cursor.fetchone.return_value = (1,)
    mock_conn.cursor.return_value = mock_cursor
    mock_client.return_value.get_connection.return_value = mock_conn

    result = check_db_connection(config)
    assert result['status'] == 'connected'
    mock_client.assert_called_once()

@patch('ragcli.utils.status.OracleClient')
def test_get_document_stats(mock_client, config):
    """Test document stats."""
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_cursor.fetchone.side_effect = [(5,), (100,), (10000,)]
    mock_conn.cursor.return_value = mock_cursor
    mock_client.return_value.get_connection.return_value = mock_conn

    result = get_document_stats(config)
    assert result['documents'] == 5
    assert result['vectors'] == 100
    assert result['total_tokens'] == 10000
    mock_client.assert_called_once()

@patch('ragcli.utils.status.requests.get')
def test_check_ollama(mock_get, config):
    """Test Ollama check."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'models': ['llama2']}

    result = check_ollama(config)
    assert result['status'] == 'connected'
    assert '1 models' in result['message']

@patch('ragcli.utils.status.check_ollama')
@patch('ragcli.utils.status.get_document_stats')
@patch('ragcli.utils.status.check_db_connection')
def test_get_overall_status(mock_db, mock_stats, mock_ollama, config):
    """Test overall status aggregation."""
    mock_db.return_value = {'status': 'connected', 'message': 'OK'}
    mock_stats.return_value = {'status': 'ok', 'documents': 5, 'vectors': 100, 'total_tokens': 1000}
    mock_ollama.return_value = {'status': 'connected', 'message': 'OK'}

    result = get_overall_status(config)
    assert result['healthy'] is True
