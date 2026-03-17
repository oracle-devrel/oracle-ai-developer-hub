"""Tests for ragcli database integration."""

import pytest
from unittest.mock import Mock, patch
from ragcli.database.oracle_client import OracleClient
from ragcli.config.config_manager import load_config

def test_oracle_client_init():
    """Test OracleClient initialization with mock config."""
    config = load_config("config.yaml.example")
    with patch('oracledb.create_pool') as mock_pool:
        client = OracleClient(config)
        mock_pool.assert_called_once()
        assert client.pool is not None

def test_init_db_success():
    """Test init_db with mock connection."""
    config = load_config("config.yaml.example")
    with patch('oracledb.create_pool'):
        client = OracleClient(config)

    with patch.object(client, 'get_connection') as mock_get:
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get.return_value = mock_conn

        from ragcli.database.schemas import get_create_schemas_sql
        sqls = get_create_schemas_sql(config)

        # First call per table: check if table exists (return 0 = doesn't exist)
        # Then execute CREATE for each table
        # Then check if vector index exists (return 0)
        # Total cursor.execute calls: len(sqls) table checks + len(sqls) creates + 1 index check
        mock_cursor.fetchone.return_value = (0,)  # table/index doesn't exist

        client.init_db()

        assert mock_conn.commit.called
        # Each table: 1 existence check + 1 create = 2 calls per table, + 1 index check
        assert mock_cursor.execute.call_count == len(sqls) * 2 + 1
