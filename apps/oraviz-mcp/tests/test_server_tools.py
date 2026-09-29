#!/usr/bin/env python
"""
Tests for the Oracle Viz MCP server tools, with python-oracledb mocked out.
"""

import array
from unittest.mock import MagicMock

import oracledb
import pytest

from oraviz_mcp import server
from oraviz_mcp.server import (
    create_chart,
    execute_query,
    get_oracle_connection,
    get_table_details,
    get_table_schema,
    list_tables,
    profile_table,
    sample_table_data,
)

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

COLUMN_METADATA = [
    ("COLUMN_NAME",),
    ("DATA_TYPE",),
    ("DATA_LENGTH",),
    ("DATA_PRECISION",),
    ("DATA_SCALE",),
    ("NULLABLE",),
    ("COLUMN_ID",),
]


class FakeCursor:
    """A scripted cursor: each execute() pops the next step dict."""

    def __init__(self, steps=None):
        self.steps = list(steps or [])
        self.executed = []
        self.description = None
        self._rows = []
        self._one = None
        self.closed = False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        step = self.steps.pop(0) if self.steps else {}
        if "raise" in step:
            raise step["raise"]
        self.description = step.get("description")
        self._rows = step.get("rows", [])
        self._one = step.get("one")

    def fetchmany(self, size):
        return self._rows[:size]

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._one

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.closed = False
        self.fetch_lobs = True

    def cursor(self):
        return self._cursor

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def patch_connection(monkeypatch, *steps):
    cursor = FakeCursor(steps)
    connection = FakeConnection(cursor)
    monkeypatch.setattr(server, "get_oracle_connection", lambda: connection)
    return cursor, connection


def configure(monkeypatch, **overrides):
    values = dict(user="scott", password="tiger", max_rows=500, preview_rows=25, max_cell_chars=500)
    values.update(overrides)
    for key, value in values.items():
        monkeypatch.setattr(server.config, key, value)


class TestGetOracleConnection:
    def test_connection_arguments(self, monkeypatch):
        configure(monkeypatch)
        fake = MagicMock()
        monkeypatch.setattr(server.oracledb, "connect", fake)
        connection = get_oracle_connection()
        assert connection is fake.return_value
        kwargs = fake.call_args.kwargs
        assert kwargs["user"] == "scott"
        assert kwargs["password"] == "tiger"
        assert kwargs["dsn"] == "localhost:1521/FREEPDB1"
        assert kwargs["tcp_connect_timeout"] == 10
        assert "config_dir" not in kwargs
        assert fake.return_value.outputtypehandler is server._lob_locator
        assert fake.return_value.module == "oraviz-mcp"
        assert fake.return_value.call_timeout == 60000

    def test_call_timeout_cannot_be_disabled(self, monkeypatch):
        configure(monkeypatch, call_timeout=0)

        class StubConnection:
            pass

        stub = StubConnection()
        monkeypatch.setattr(server.oracledb, "connect", MagicMock(return_value=stub))
        with pytest.raises(ValueError, match="TIMEOUT"):
            get_oracle_connection()
        server.oracledb.connect.assert_not_called()
        assert not hasattr(stub, "call_timeout")

    def test_wallet_arguments(self, monkeypatch):
        configure(monkeypatch)
        monkeypatch.setattr(server.config, "dsn", "adb.example.com:1522/FREEPDB1")
        monkeypatch.setattr(server.config, "config_dir", "/wallet")
        monkeypatch.setattr(server.config, "wallet_location", "/wallet/creds")
        monkeypatch.setattr(server.config, "wallet_password", "secret")
        fake = MagicMock()
        monkeypatch.setattr(server.oracledb, "connect", fake)
        get_oracle_connection()
        kwargs = fake.call_args.kwargs
        assert kwargs["config_dir"] == "/wallet"
        assert kwargs["wallet_location"] == "/wallet/creds"
        assert kwargs["wallet_password"] == "secret"

    def test_connection_error_is_logged_and_reraised(self, monkeypatch):
        configure(monkeypatch)
        monkeypatch.setattr(
            server.oracledb, "connect", MagicMock(side_effect=oracledb.DatabaseError("boom"))
        )
        with pytest.raises(oracledb.Error):
            get_oracle_connection()

    def test_missing_configuration(self, monkeypatch):
        configure(monkeypatch, user="")
        with pytest.raises(ValueError, match="ORACLE_USER"):
            get_oracle_connection()


class TestExecuteQuery:
    def test_success_returns_compact_table(self, monkeypatch):
        configure(monkeypatch)
        patch_connection(
            monkeypatch,
            {
                "description": [("REGION",), ("REVENUE",)],
                "rows": [("East", 12.5), ("West", 7)],
            },
        )
        text = execute_query("SELECT region, revenue FROM sales")
        assert text.splitlines()[0] == "2 row(s) | columns: REGION, REVENUE"
        assert "| East | 12.5 |" in text
        assert "| West | 7 |" in text

    def test_default_limit_is_the_preview_cap(self, monkeypatch):
        configure(monkeypatch, preview_rows=2, max_rows=10)
        patch_connection(
            monkeypatch,
            {"description": [("A",)], "rows": [(1,), (2,), (3,)]},
        )
        text = execute_query("SELECT a FROM t")
        assert text.splitlines()[0] == "2 row(s) (truncated; more rows exist) | columns: A"
        assert "| 3 |" not in text

    def test_explicit_max_rows_is_respected_and_capped(self, monkeypatch):
        configure(monkeypatch, preview_rows=1, max_rows=3)
        cursor, _ = patch_connection(
            monkeypatch,
            {"description": [("A",)], "rows": [(1,), (2,), (3,), (4,), (5,)]},
        )
        text = execute_query("SELECT a FROM t", max_rows=99)
        assert text.splitlines()[0].startswith("3 row(s) (truncated; more rows exist)")
        assert cursor.executed

    def test_query_without_result_set(self, monkeypatch):
        configure(monkeypatch)
        patch_connection(monkeypatch, {})
        text = execute_query("SELECT 1 FROM dual WHERE 1 = 0")
        assert text == "no columns returned (the statement produced no result set)"

    def test_missing_configuration(self, monkeypatch):
        configure(monkeypatch, user="")
        with pytest.raises(ValueError, match="ORACLE_USER"):
            execute_query("SELECT 1 FROM dual")

    def test_rejects_non_select(self, monkeypatch):
        configure(monkeypatch)
        with pytest.raises(ValueError, match="read-only"):
            execute_query("DELETE FROM sales")

    def test_database_error_propagates(self, monkeypatch):
        configure(monkeypatch)
        patch_connection(monkeypatch, {"raise": oracledb.DatabaseError("boom")})
        with pytest.raises(oracledb.Error):
            execute_query("SELECT 1 FROM dual")


class TestListTables:
    def test_without_schema_uses_user_views(self, monkeypatch):
        configure(monkeypatch)
        cursor, _ = patch_connection(
            monkeypatch,
            {
                "description": [("OWNER",), ("TABLE_NAME",), ("OBJECT_TYPE",)],
                "rows": [("SCOTT", "SALES", "TABLE"), ("SCOTT", "SALES_V", "VIEW")],
            },
        )
        text = list_tables()
        sql, binds = cursor.executed[0]
        assert "user_tables" in sql and "user_views" in sql
        assert binds == {}
        assert "| SCOTT | SALES_V | VIEW |" in text

    def test_with_schema_uses_all_views(self, monkeypatch):
        configure(monkeypatch)
        cursor, _ = patch_connection(
            monkeypatch,
            {
                "description": [("OWNER",), ("TABLE_NAME",), ("OBJECT_TYPE",)],
                "rows": [("ORAVIZ", "SALES_DEMO", "TABLE")],
            },
        )
        text = list_tables("oraviz")
        sql, binds = cursor.executed[0]
        assert "all_tables" in sql and "all_views" in sql
        assert binds == {"owner": "ORAVIZ"}
        assert "| ORAVIZ | SALES_DEMO | TABLE |" in text

    def test_large_schemas_are_truncated(self, monkeypatch):
        configure(monkeypatch, max_rows=1)
        patch_connection(
            monkeypatch,
            {
                "description": [("OWNER",), ("TABLE_NAME",), ("OBJECT_TYPE",)],
                "rows": [("SCOTT", "A", "TABLE"), ("SCOTT", "B", "TABLE")],
            },
        )
        text = list_tables()
        assert text.splitlines()[0] == (
            "1 row(s) (truncated; more rows exist) | columns: OWNER, TABLE_NAME, OBJECT_TYPE"
        )
        assert "| SCOTT | B | TABLE |" not in text

    def test_invalid_schema(self, monkeypatch):
        configure(monkeypatch)
        with pytest.raises(ValueError, match="schema name"):
            list_tables("bad schema")

    def test_database_error_propagates(self, monkeypatch):
        configure(monkeypatch)
        patch_connection(monkeypatch, {"raise": oracledb.DatabaseError("boom")})
        with pytest.raises(oracledb.Error):
            list_tables()


class TestGetTableSchema:
    def test_compact_projection(self, monkeypatch):
        configure(monkeypatch)
        patch_connection(
            monkeypatch,
            {
                "description": COLUMN_METADATA,
                "rows": [
                    ("SALE_ID", "NUMBER", 22, 10, 0, "N", "YES"),
                    ("REGION", "VARCHAR2", 20, None, None, "N", "NO"),
                ],
            },
        )
        text = get_table_schema("sales_demo")
        assert text.splitlines()[0] == (
            "2 row(s) | columns: COLUMN_NAME, DATA_TYPE, DATA_LENGTH, NULLABLE, PRIMARY_KEY"
        )
        assert "| SALE_ID | NUMBER | 22 | N | YES |" in text
        assert "| REGION | VARCHAR2 | 20 | N | NO |" in text

    def test_missing_table(self, monkeypatch):
        configure(monkeypatch)
        patch_connection(monkeypatch, {"description": COLUMN_METADATA, "rows": []})
        with pytest.raises(ValueError, match="not found"):
            get_table_schema("nope")


class TestSampleTableData:
    def test_returns_sample_with_note(self, monkeypatch):
        configure(monkeypatch)
        cursor, _ = patch_connection(
            monkeypatch,
            {"one": (1,)},
            {"description": [("ID",), ("NAME",)], "rows": [(1, "a"), (2, "b")]},
        )
        text = sample_table_data("sales_demo", 2)
        assert "2 row(s) | columns: ID, NAME | sample of" in text
        assert '"SALES_DEMO"' in text
        assert "FETCH FIRST 2 ROWS ONLY" in cursor.executed[1][0]

    def test_size_is_capped(self, monkeypatch):
        configure(monkeypatch, max_rows=5)
        cursor, _ = patch_connection(
            monkeypatch,
            {"one": (1,)},
            {"description": [("ID",)], "rows": [(1,)]},
        )
        sample_table_data("sales_demo", 100)
        assert "FETCH FIRST 5 ROWS ONLY" in cursor.executed[1][0]

    def test_missing_table(self, monkeypatch):
        configure(monkeypatch)
        patch_connection(monkeypatch, {"one": (0,)})
        with pytest.raises(ValueError, match="not found"):
            sample_table_data("nope")

    def test_schema_qualified_name_is_used(self, monkeypatch):
        configure(monkeypatch)
        cursor, _ = patch_connection(
            monkeypatch,
            {"one": (1,)},
            {"description": [("ID",)], "rows": [(1,)]},
        )
        sample_table_data("oraviz.sales_demo", 1)
        assert 'FROM "ORAVIZ"."SALES_DEMO"' in cursor.executed[1][0]


class TestGetTableDetails:
    TABLE_ROW = ("ORAVIZ", "SALES_DEMO", "USERS", 96, 8, 100, None, "N", "DISABLED")

    def test_table_with_exact_count(self, monkeypatch):
        configure(monkeypatch)
        patch_connection(
            monkeypatch,
            {"one": self.TABLE_ROW},
            {"one": (96,)},
        )
        details = get_table_details("sales_demo", exact_row_count=True)
        assert details["object_type"] == "TABLE"
        assert details["owner"] == "ORAVIZ"
        assert details["name"] == "SALES_DEMO"
        assert details["tablespace_name"] == "USERS"
        assert details["num_rows_stat"] == 96
        assert details["last_analyzed"] is None
        assert details["exact_row_count"] == 96

    def test_table_without_exact_count(self, monkeypatch):
        configure(monkeypatch)
        patch_connection(monkeypatch, {"one": self.TABLE_ROW})
        details = get_table_details("sales_demo")
        assert "exact_row_count" not in details

    def test_view_fallback(self, monkeypatch):
        configure(monkeypatch)
        patch_connection(
            monkeypatch,
            {"one": None},
            {"one": ("ORAVIZ", "SALES_VIEW")},
        )
        details = get_table_details("sales_view")
        assert details == {"owner": "ORAVIZ", "name": "SALES_VIEW", "object_type": "VIEW"}

    def test_missing_object(self, monkeypatch):
        configure(monkeypatch)
        patch_connection(monkeypatch, {"one": None}, {"one": None})
        with pytest.raises(ValueError, match="not found"):
            get_table_details("nope")


class TestProfileTable:
    METADATA_ROWS = [
        ("REGION", "VARCHAR2", 20, None, None, "N", 1),
        ("REVENUE", "NUMBER", 22, 10, 2, "N", 2),
    ]

    def test_happy_path(self, monkeypatch):
        configure(monkeypatch)
        cursor, _ = patch_connection(
            monkeypatch,
            {"description": COLUMN_METADATA, "rows": self.METADATA_ROWS},
            {"one": (96, 96, 4, "East", "West", 90, 96, 1.5, 38000.0, 19476.5)},
        )
        profile = profile_table("sales_demo")
        assert profile["table"] == "SALES_DEMO"
        assert profile["row_count"] == 96
        assert profile["columns"][0] == {
            "column": "REGION",
            "data_type": "VARCHAR2",
            "nullable": "N",
            "non_null": 96,
            "distinct": 4,
            "min": "East",
            "max": "West",
            "nulls": 0,
        }
        assert profile["columns"][1]["avg"] == 19476.5
        assert profile["columns"][1]["nulls"] == 6
        # One aggregate query, quoting the validated table name.
        aggregate_sql = cursor.executed[1][0]
        assert aggregate_sql.startswith('SELECT COUNT(*)')
        assert 'FROM "SALES_DEMO"' in aggregate_sql

    def test_qualified_table_and_selected_columns(self, monkeypatch):
        configure(monkeypatch)
        cursor, _ = patch_connection(
            monkeypatch,
            {"description": COLUMN_METADATA, "rows": self.METADATA_ROWS},
            {"one": (96, 96, 4, "East", "West")},
        )
        profile = profile_table("oraviz.sales_demo", columns=["region"])
        assert profile["table"] == "ORAVIZ.SALES_DEMO"
        assert len(profile["columns"]) == 1
        assert 'FROM "ORAVIZ"."SALES_DEMO"' in cursor.executed[1][0]

    def test_unknown_column(self, monkeypatch):
        configure(monkeypatch)
        patch_connection(monkeypatch, {"description": COLUMN_METADATA, "rows": self.METADATA_ROWS})
        with pytest.raises(ValueError, match="Unknown column"):
            profile_table("sales_demo", columns=["nope"])

    def test_missing_table(self, monkeypatch):
        configure(monkeypatch)
        patch_connection(monkeypatch, {"description": COLUMN_METADATA, "rows": []})
        with pytest.raises(ValueError, match="not found"):
            profile_table("nope")

    def test_column_truncation_note(self, monkeypatch):
        configure(monkeypatch)
        patch_connection(
            monkeypatch,
            {"description": COLUMN_METADATA, "rows": self.METADATA_ROWS},
            {"one": (96, 96, 4, "East", "West")},
        )
        profile = profile_table("sales_demo", max_columns=1)
        assert len(profile["columns"]) == 1
        assert "note" in profile
        with pytest.raises(ValueError, match="max_columns"):
            profile_table("sales_demo", max_columns=0)


class TestCreateChart:
    def test_renders_image_and_preview(self, monkeypatch):
        configure(monkeypatch, max_rows=10)
        patch_connection(
            monkeypatch,
            {
                "description": [("REGION",), ("REVENUE",)],
                "rows": [("East", 10), ("West", 20)],
            },
        )
        result = create_chart(
            "SELECT region, revenue FROM sales ORDER BY revenue", "bar", title="Revenue"
        )
        assert isinstance(result, list) and len(result) == 2
        image, summary = result
        assert image.data.startswith(PNG_MAGIC)
        assert "Rendered a `bar` chart" in summary
        assert "| East | 10 |" in summary

    def test_truncation_note(self, monkeypatch):
        configure(monkeypatch, max_rows=2)
        patch_connection(
            monkeypatch,
            {"description": [("A",), ("B",)], "rows": [(1, 2), (3, 4), (5, 6)]},
        )
        _, summary = create_chart("SELECT a, b FROM t", "line")
        assert "only the first 2 rows were plotted" in summary

    def test_vector_column_is_projected(self, monkeypatch):
        configure(monkeypatch)
        patch_connection(
            monkeypatch,
            {
                "description": [("NAME",), ("EMBEDDING",)],
                "rows": [
                    ("alpha", array.array("f", [1.0, 0.0, 0.0])),
                    ("beta", array.array("f", [0.0, 1.0, 0.0])),
                    ("gamma", array.array("f", [0.0, 0.0, 1.0])),
                ],
            },
        )
        image, summary = create_chart("SELECT name, embedding FROM t", "vector")
        assert image.data.startswith(PNG_MAGIC)
        assert "Rendered a `vector` chart" in summary
        assert "<VECTOR(3)>" in summary

    def test_invalid_chart_type(self, monkeypatch):
        configure(monkeypatch)
        patch_connection(monkeypatch, {"description": [("A",)], "rows": [(1,)]})
        with pytest.raises(ValueError, match="Unsupported chart_type"):
            create_chart("SELECT a FROM t", "donut")

    def test_no_rows(self, monkeypatch):
        configure(monkeypatch)
        patch_connection(monkeypatch, {"description": [("A",)], "rows": []})
        with pytest.raises(ValueError, match="no rows"):
            create_chart("SELECT a FROM t", "bar")

    def test_database_error_propagates(self, monkeypatch):
        configure(monkeypatch)
        patch_connection(monkeypatch, {"raise": oracledb.DatabaseError("boom")})
        with pytest.raises(oracledb.Error):
            create_chart("SELECT a FROM t", "bar")
