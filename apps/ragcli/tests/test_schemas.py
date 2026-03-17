"""Test that all new schemas are generated."""
from ragcli.database.schemas import get_create_schemas_sql

def test_all_tables_present():
    config = {'vector_index': {'dimension': 768}}
    tables = get_create_schemas_sql(config)
    table_names = [name for name, _ in tables]
    # Existing
    assert "DOCUMENTS" in table_names
    assert "CHUNKS" in table_names
    assert "QUERIES" in table_names
    assert "QUERY_RESULTS" in table_names
    # New
    assert "SESSIONS" in table_names
    assert "SESSION_TURNS" in table_names
    assert "KG_ENTITIES" in table_names
    assert "KG_RELATIONSHIPS" in table_names
    assert "KG_ENTITY_CHUNKS" in table_names
    assert "AGENT_TRACES" in table_names
    assert "TRACE_STEPS" in table_names
    assert "FEEDBACK" in table_names
    assert "CHUNK_QUALITY" in table_names
    assert "EVAL_RUNS" in table_names
    assert "EVAL_RESULTS" in table_names
    assert "SYNC_SOURCES" in table_names
    assert "SYNC_EVENTS" in table_names

def test_schema_count():
    config = {'vector_index': {'dimension': 768}}
    tables = get_create_schemas_sql(config)
    assert len(tables) == 17  # 4 existing + 13 new

def test_schema_sql_valid():
    config = {'vector_index': {'dimension': 768}}
    tables = get_create_schemas_sql(config)
    for name, sql in tables:
        assert "CREATE TABLE" in sql
        assert name in sql
