"""Adversarial query and data-budget regressions; no live database required."""

import array
from types import SimpleNamespace
from unittest.mock import MagicMock

import oracledb
import pytest
from fastmcp import Client

from oraviz_mcp import server
from oraviz_mcp.query_policy import MAX_SQL_CHARS, validate_query
from tests.test_server_tools import configure, patch_connection


@pytest.mark.parametrize("query", [
    "WITH x AS (SELECT 1 FROM dual) DELETE FROM t",
    "WITH FUNCTION f RETURN NUMBER IS BEGIN RETURN 1; END; SELECT f FROM dual",
    "SELECT * FROM t FOR UPDATE",
    "SELECT * FROM t FOR /* comment */ UPDATE",
    "SELECT seq.NEXTVAL FROM dual",
    'SELECT seq."NEXTVAL" FROM dual',
    "SELECT UTL_HTTP.REQUEST('https://attacker.invalid') FROM dual",
    'SELECT "UTL_HTTP"."REQUEST"(\'https://attacker.invalid\') FROM dual',
    "SELECT SYS.DBMS_LOCK.SLEEP(5) FROM dual",
    "SELECT evil_function() FROM dual",
    "SELECT * FROM t@remote",
    "SELECT * INTO copied FROM t",
    "SELECT 1 FROM dual;;",
    "SELECT 1 FROM dual; DELETE FROM t",
    "SELECT 1 FROM dual /* unterminated",
    "SELECT 'unterminated FROM dual",
    "SELECT ) FROM dual",
    "SELECT (1 FROM dual",
    "SELECT :unbound FROM dual",
    "SELECT q'[don't parse]' FROM dual",
    "SELECT nq'[text]' FROM dual",
    "SELECT " + "(" * 33 + "1" + ")" * 33 + " FROM dual",
    "SELECT \x00 FROM dual",
    None,
    42,
    "-- comment only",
    "SELECT '" + "x" * MAX_SQL_CHARS + "' FROM dual",
])
def test_unsafe_sql_never_connects(query, monkeypatch):
    connect = MagicMock()
    monkeypatch.setattr(server, "get_oracle_connection", connect)
    with pytest.raises(ValueError):
        server._run_query(query, 25)
    connect.assert_not_called()


@pytest.mark.parametrize("query", [
    "SELECT region, SUM(revenue) FROM sales GROUP BY region",
    "WITH totals AS (SELECT region, COUNT(*) n FROM sales GROUP BY region) SELECT * FROM totals",
    "SELECT 'DROP; UPDATE ''quoted''' label FROM dual",
    "SELECT 'https://example.invalid' FROM dual",
    "SELECT * FROM sales WHERE region IN ('East', 'West')",
    "SELECT region, ROW_NUMBER() OVER (ORDER BY revenue) n FROM sales",
    "SELECT (1 + 2) FROM dual",
    "SELECT ROUND(AVG(revenue), 2) FROM sales",
    "-- SELECT query\nSELECT 1 FROM dual /* harmless */",
    'SELECT "REGION" FROM "SALES"',
    "SELECT VECTOR_DISTANCE(embedding, TO_VECTOR('[1,2]'), COSINE) FROM vectors",
])
def test_supported_sql(query):
    assert validate_query(query) == query.strip()


def test_only_real_trailing_semicolon_removed():
    assert validate_query("SELECT ';' FROM dual; -- trailing ; comment") == "SELECT ';' FROM dual"


@pytest.mark.parametrize("identifier", ["a" * 129, 42, "A.B.C", '"A"'])
def test_identifier_bounds(identifier):
    with pytest.raises(ValueError):
        server.validate_table_name(identifier)
    with pytest.raises(ValueError):
        server.validate_column_name(identifier)


def test_result_width_rejected_before_fetch(monkeypatch):
    configure(monkeypatch)
    monkeypatch.setattr(server.config, "max_result_columns", 2)
    cursor = MagicMock(description=[("A",), ("B",), ("C",)])
    with pytest.raises(ValueError, match="columns"):
        server._fetch_rows(cursor, 25)
    cursor.fetchmany.assert_not_called()


def test_total_text_budget_and_header_escaping(monkeypatch):
    configure(monkeypatch, max_cell_chars=4096)
    text = server.render_rows(["NAME\nforged metadata|"], [("x" * 4096,)] * 500)
    assert len(text) <= 256_000
    assert "output character budget" in text
    assert "\nforged metadata" not in text


@pytest.mark.parametrize("data_type", [oracledb.DB_TYPE_CLOB, oracledb.DB_TYPE_NCLOB,
                                      oracledb.DB_TYPE_BLOB, oracledb.DB_TYPE_BFILE])
def test_lob_type_handler_preserves_locator(data_type):
    cursor = MagicMock(arraysize=5)
    assert server._lob_locator(cursor, SimpleNamespace(type_code=data_type)) is cursor.var.return_value
    cursor.var.assert_called_once_with(data_type, arraysize=5)


def test_normal_types_use_driver_default():
    assert server._lob_locator(MagicMock(), SimpleNamespace(type_code=oracledb.DB_TYPE_NUMBER)) is None


def test_metadata_identifiers_are_escaped_before_generated_sql(monkeypatch):
    name = 'ODD"NAME'
    cursor, _ = patch_connection(
        monkeypatch,
        {"rows": [(name, "NUMBER", 22, None, None, "Y", 1)]},
        {"one": (1, 1, 1, 2, 2, 2)},
    )
    server.profile_table("sales")
    query = cursor.executed[1][0]
    assert 'COUNT("ODD""NAME")' in query
    assert 'AS "ODD""NAME__NON_NULL"' in query


@pytest.mark.parametrize("user", ["SYSTEM", "sys", "SYSDBA", "DBSNMP", "SYSMAN"])
def test_admin_accounts_rejected_before_connect(user, monkeypatch):
    configure(monkeypatch, user=user)
    connect = MagicMock()
    monkeypatch.setattr(server.oracledb, "connect", connect)
    with pytest.raises(ValueError, match="administrator"):
        server.get_oracle_connection()
    connect.assert_not_called()


@pytest.mark.parametrize("kwargs", [
    {"columns": ["valid", "bad;sql"]},
    {"columns": ["valid"] * 201},
    {"columns": []},
    {"columns": "valid"},
    {"max_columns": True},
    {"max_columns": "50"},
    {"max_columns": 1.5},
])
def test_profile_input_rejected_before_database(kwargs, monkeypatch):
    connect = MagicMock()
    monkeypatch.setattr(server, "get_oracle_connection", connect)
    with pytest.raises(ValueError):
        server.profile_table("sales", **kwargs)
    connect.assert_not_called()


def test_overwide_metadata_fails_bounded(monkeypatch):
    patch_connection(monkeypatch, {"rows": [("a",)] * 201})
    with pytest.raises(ValueError, match="200 columns"):
        server._fetch_columns(None, "SALES")


def test_bad_chart_input_rejected_before_database(monkeypatch):
    connect = MagicMock()
    monkeypatch.setattr(server, "get_oracle_connection", connect)
    with pytest.raises(ValueError, match="chart_type"):
        server.create_chart("SELECT 1 FROM dual", "bogus")
    with pytest.raises(ValueError, match="labels"):
        server.create_chart("SELECT 1 FROM dual", "bar", title="x" * 201)
    connect.assert_not_called()


def test_oversized_vector_rejected(monkeypatch):
    patch_connection(monkeypatch, {"description": [("NAME",), ("VECTOR",)],
                                 "rows": [("x", array.array("f", [0] * 4097))]})
    with pytest.raises(ValueError, match="dimensions"):
        server.create_chart("SELECT name, embedding FROM t", "vector")


def test_chart_image_budget(monkeypatch):
    patch_connection(monkeypatch, {"description": [("A",)], "rows": [(1,)]})
    monkeypatch.setattr(server, "render_chart", lambda *a, **kw: b"x" * 2_000_001)
    with pytest.raises(ValueError, match="image output budget"):
        server.create_chart("SELECT a FROM t", "bar")


@pytest.mark.asyncio
async def test_wire_errors_never_expose_query_or_database_errors(monkeypatch, caplog):
    configure(monkeypatch)
    secret = "sensitive-customer-value"
    patch_connection(monkeypatch, {"raise": oracledb.DatabaseError(secret)})
    async with Client(server.mcp) as client:
        result = await client.call_tool("execute_query", {"query": f"SELECT '{secret}' FROM dual"},
                                        raise_on_error=False)
    assert result.is_error
    assert secret not in str(result)
    assert secret not in caplog.text


def test_numeric_environment_upper_bound(monkeypatch):
    monkeypatch.setenv("ORAVIZ_TEST_CAP", "999999")
    assert server._int_env("ORAVIZ_TEST_CAP", 60, minimum=1, maximum=300) == 60


@pytest.mark.asyncio
@pytest.mark.parametrize("name,arguments", [
    ("execute_query", {"query": "SELECT 1 FROM dual", "max_rows": True}),
    ("execute_query", {"query": "SELECT 1 FROM dual", "max_rows": "10"}),
    ("execute_query", {"query": "SELECT 1 FROM dual", "max_rows": 1.5}),
    ("execute_query", {"query": "SELECT 1 FROM dual", "approved": True}),
    ("execute_query", {"query": "x" * 32_001}),
    ("create_chart", {"sql": "SELECT 1 FROM dual", "chart_type": "bar", "title": "x" * 201}),
    ("profile_table", {"table_name": "sales", "columns": ["A"] * 201}),
    ("get_table_details", {"table_name": "sales", "exact_row_count": "false"}),
])
async def test_wire_schema_rejection_precedes_database(name, arguments, monkeypatch):
    configure(monkeypatch)
    connection = MagicMock()
    monkeypatch.setattr(server, "get_oracle_connection", connection)
    async with Client(server.mcp) as client:
        response = await client.call_tool(name, arguments, raise_on_error=False)
    assert response.is_error
    connection.assert_not_called()


@pytest.mark.asyncio
async def test_response_budget_includes_structured_results(monkeypatch):
    configure(monkeypatch, max_cell_chars=4096, preview_rows=100)
    patch_connection(monkeypatch, {"description": [("VALUE",)], "rows": [("x" * 4096,)] * 100})
    async with Client(server.mcp) as client:
        response = await client.call_tool("execute_query", {"query": "SELECT value FROM t"}, raise_on_error=False)
    assert response.is_error
    assert "x" * 100 not in str(response)


@pytest.mark.asyncio
async def test_oracle_session_carries_generated_audit_request(monkeypatch):
    configure(monkeypatch)
    connect = MagicMock()
    connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value.description = []
    monkeypatch.setattr(server.oracledb, "connect", connect)
    async with Client(server.mcp) as client:
        response = await client.call_tool("execute_query", {"query": "SELECT 1 FROM dual"})
    assert not response.is_error
    from uuid import UUID
    assert UUID(connect.return_value.client_identifier)
    assert connect.return_value.module == "oraviz-mcp"
