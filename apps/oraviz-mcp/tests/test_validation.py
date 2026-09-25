#!/usr/bin/env python
"""
Tests for validation, value formatting, and context-engineered rendering.
"""

import array
import decimal
from datetime import date, datetime, time

import pytest

from oraviz_mcp.server import (
    _cell_text,
    format_value,
    qualified_name,
    quote_identifier,
    render_rows,
    validate_column_name,
    validate_max_rows,
    validate_query,
    validate_schema_name,
    validate_table_name,
    config,
)


class TestValidateQuery:
    @pytest.mark.parametrize(
        "query",
        [
            "SELECT 1 FROM dual",
            "select region, sum(revenue) from sales group by region",
            "  WITH totals AS (SELECT 1 AS n FROM dual) SELECT n FROM totals  ",
            "SELECT * FROM sales_demo;",
        ],
    )
    def test_accepts_read_only(self, query):
        assert validate_query(query)

    @pytest.mark.parametrize(
        "query",
        [
            "",
            "   ",
            "DELETE FROM sales_demo",
            "UPDATE sales_demo SET revenue = 0",
            "INSERT INTO t VALUES (1)",
            "DROP TABLE t",
            "CREATE TABLE t (id NUMBER)",
            "BEGIN NULL; END;",
            "SELECT 1 FROM dual; SELECT 2 FROM dual",
        ],
    )
    def test_rejects_non_read_only(self, query):
        with pytest.raises(ValueError):
            validate_query(query)


class TestIdentifiers:
    def test_table_simple(self):
        assert validate_table_name("sales_demo") == (None, "SALES_DEMO")

    def test_table_qualified(self):
        assert validate_table_name("oraviz.sales_demo") == ("ORAVIZ", "SALES_DEMO")

    def test_table_dollar_and_hash(self):
        assert validate_table_name("t$1#x") == (None, "T$1#X")

    @pytest.mark.parametrize("bad", ["", "   ", "1SALES", "SALES;DROP TABLE x", "A.B.C", "SALES DEMO", "a-b"])
    def test_table_rejects(self, bad):
        with pytest.raises(ValueError):
            validate_table_name(bad)

    def test_schema_and_column(self):
        assert validate_schema_name("scott") == "SCOTT"
        assert validate_column_name("revenue") == "REVENUE"
        with pytest.raises(ValueError):
            validate_schema_name("bad name")
        with pytest.raises(ValueError):
            validate_column_name("")

    def test_quoting(self):
        assert quote_identifier("SALES") == '"SALES"'
        assert qualified_name(None, "SALES") == '"SALES"'
        assert qualified_name("ORAVIZ", "SALES") == '"ORAVIZ"."SALES"'


class TestValidateMaxRows:
    def test_passes_through(self):
        assert validate_max_rows(10) == 10

    def test_clamps_to_configured_maximum(self, monkeypatch):
        monkeypatch.setattr(config, "max_rows", 50)
        assert validate_max_rows(1000) == 50

    @pytest.mark.parametrize("bad", [0, -1, True, "10", None])
    def test_rejects_bad_values(self, bad):
        with pytest.raises(ValueError):
            validate_max_rows(bad)


class TestFormatValue:
    def test_scalars(self):
        assert format_value(None) is None
        assert format_value(True) is True
        assert format_value(42) == 42
        assert format_value(3.5) == 3.5
        assert format_value(decimal.Decimal("12.50")) == 12.5

    def test_non_finite(self):
        assert format_value(float("nan")) == "nan"
        assert format_value(decimal.Decimal("Infinity")) == "Infinity"

    def test_high_precision_decimal_stays_exact(self):
        # Would round to 1.2345678901234568e+19 as a float; keep the exact digits.
        assert format_value(decimal.Decimal("12345678901234567890.12")) == "12345678901234567890.12"
        assert format_value(decimal.Decimal("0.1")) == 0.1

    def test_dates(self):
        assert format_value(datetime(2026, 9, 14, 0, 0)) == "2026-09-14"
        assert format_value(datetime(2026, 9, 14, 12, 30, 5)) == "2026-09-14T12:30:05"
        assert format_value(date(2026, 9, 14)) == "2026-09-14"
        assert format_value(time(12, 30)) == "12:30:00"

    def test_binary_and_vectors(self):
        assert format_value(b"abc") == "<binary 3 bytes>"
        assert format_value(bytearray(b"abcd")) == "<binary 4 bytes>"
        assert format_value(array.array("f", [1.0, 2.0])) == "<VECTOR(2)>"

    def test_sparse_vector_like(self):
        class Sparse:
            num_elements = 100
            values = [1.0, 2.0, 3.0]

        assert format_value(Sparse()) == "<VECTOR(3)>"

    def test_lob_like(self):
        class Lob:
            def read(self):
                pytest.fail("LOB contents must never be read")

        class BinaryLob:
            def read(self):
                pytest.fail("Binary LOB contents must never be read")

        assert format_value(Lob()) == "<LOB>"
        assert format_value(BinaryLob()) == "<LOB>"

    def test_lob_is_summarized_even_with_a_small_cell_budget(self, monkeypatch):
        monkeypatch.setattr(config, "max_cell_chars", 10)

        class Lob:
            def read(self):
                pytest.fail("LOB contents must never be read")

        assert format_value(Lob()) == "<LOB>"

    def test_long_strings_are_truncated(self, monkeypatch):
        monkeypatch.setattr(config, "max_cell_chars", 10)
        assert format_value("0123456789abcdef") == "0123456789..."
        # short values are untouched
        assert format_value("short") == "short"

    def test_objects_render_as_str(self):
        class Thing:
            def __str__(self):
                return "a thing"

        assert format_value(Thing()) == "a thing"


class TestCellText:
    def test_null(self):
        assert _cell_text(None) == "null"

    def test_escapes_table_delimiters(self):
        assert _cell_text("a|b") == "a\\|b"
        assert _cell_text("line1\nline2") == "line1 line2"
        assert _cell_text("cr\rlf") == "crlf"


class TestRenderRows:
    def test_metadata_and_table(self):
        text = render_rows(["REGION", "REVENUE"], [("East", 1.5), ("West", 2)])
        lines = text.splitlines()
        assert lines[0] == "2 row(s) | columns: REGION, REVENUE"
        assert lines[2] == "| REGION | REVENUE |"
        assert lines[3] == "|---|---|"
        assert lines[4] == "| East | 1.5 |"
        assert lines[5] == "| West | 2 |"

    def test_truncated_and_note(self):
        text = render_rows(["A"], [(1,)], truncated=True, note="sample of X")
        assert text.splitlines()[0] == "1 row(s) (truncated; more rows exist) | columns: A | sample of X"

    def test_empty_columns(self):
        assert render_rows([], []) == "no columns returned (the statement produced no result set)"

    def test_zero_rows_keeps_header(self):
        text = render_rows(["A", "B"], [])
        assert text.splitlines()[0] == "0 row(s) | columns: A, B"
        assert "| A | B |" in text

    def test_escapes_column_names(self):
        text = render_rows(["A|B", "C\nD"], [(1, 2)])
        assert "| A\\|B | C D |" in text
