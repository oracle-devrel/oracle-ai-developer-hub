#!/usr/bin/env python
"""
Tests for chart rendering (no database required).
"""

import array

import oracledb
import pytest

from oraviz_mcp.charts import (
    CHART_TYPES,
    ChartError,
    _project_vectors,
    _to_float,
    _vector_values,
    render_chart,
)

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

COLUMNS = ["REGION", "ONLINE", "RETAIL"]
ROWS = [["North", 120, 80], ["South", 200, 150], ["East", 90, 60], ["West", 160, 110]]

VECTOR_COLUMNS = ["NAME", "EMBEDDING"]
VECTOR_ROWS = [
    ["alpha", [1.0, 0.0, 0.0]],
    ["beta", [0.0, 1.0, 0.0]],
    ["gamma", [0.0, 0.0, 1.0]],
    ["delta", [1.0, 1.0, 0.0]],
]


def _png(*args, **kwargs) -> bytes:
    data = render_chart(*args, **kwargs)
    assert isinstance(data, bytes)
    assert data.startswith(PNG_MAGIC)
    return data


class TestRenderChart:
    @pytest.mark.parametrize("chart_type", [value for value in CHART_TYPES if value != "vector"])
    def test_all_types_render_png(self, chart_type):
        _png(COLUMNS, ROWS, chart_type)

    def test_titles_and_labels(self):
        _png(COLUMNS, ROWS, "bar", title="Sales", x_label="Region", y_label="Revenue")

    def test_single_series(self):
        _png(["MONTH", "REVENUE"], [["Jan", 1], ["Feb", 2]], "line")

    def test_many_series_are_capped_not_fatal(self):
        columns = ["LABEL"] + [f"S{i}" for i in range(10)]
        rows = [["row", *range(10)], ["row2", *range(10, 20)]]
        _png(columns, rows, "line")

    def test_many_categories_thins_ticks(self):
        rows = [[f"c{i}", i] for i in range(50)]
        _png(["CATEGORY", "VALUE"], rows, "bar")

    def test_none_values_do_not_break_rendering(self):
        rows = [["a", None], ["b", 2], ["c", None]]
        _png(["L", "V"], rows, "line")
        _png(["L", "V"], rows, "bar")

    def test_pie_groups_small_slices(self):
        rows = [[f"c{i}", i + 1] for i in range(20)]
        _png(["CATEGORY", "VALUE"], rows, "pie")

    def test_scatter_filters_non_numeric_pairs(self):
        rows = [[1, None], [2, 3], [None, 4]]
        _png(["X", "Y"], rows, "scatter")

    def test_histogram_single_numeric(self):
        _png(["AMOUNT"], [[1], [2], [2], [3]], "histogram")

    def test_chart_type_is_case_insensitive(self):
        _png(COLUMNS, ROWS, "BAR")


class TestRenderChartErrors:
    def test_unknown_type(self):
        with pytest.raises(ChartError, match="Unsupported chart_type"):
            render_chart(COLUMNS, ROWS, "sunburst")

    def test_empty_type(self):
        with pytest.raises(ChartError):
            render_chart(COLUMNS, ROWS, "")

    def test_no_columns(self):
        with pytest.raises(ChartError, match="no columns"):
            render_chart([], ROWS, "bar")

    def test_no_rows(self):
        with pytest.raises(ChartError, match="no rows"):
            render_chart(COLUMNS, [], "bar")

    def test_bar_needs_numeric_column(self):
        with pytest.raises(ChartError, match="numeric column"):
            render_chart(["A", "B"], [["x", "y"]], "bar")

    def test_line_needs_numeric_column(self):
        with pytest.raises(ChartError, match="numeric column"):
            render_chart(["A", "B"], [["x", "y"]], "line")

    def test_area_needs_numeric_column(self):
        with pytest.raises(ChartError, match="numeric column"):
            render_chart(["A", "B"], [["x", "y"]], "area")

    def test_scatter_needs_two_numeric_columns(self):
        with pytest.raises(ChartError, match="two numeric"):
            render_chart(["A", "B"], [["x", 1]], "scatter")

    def test_scatter_needs_a_complete_pair(self):
        with pytest.raises(ChartError, match="both columns"):
            render_chart(["X", "Y"], [[1, None], [None, 2]], "scatter")

    def test_pie_needs_numeric_column(self):
        with pytest.raises(ChartError, match="numeric column"):
            render_chart(["A", "B"], [["x", "y"]], "pie")

    def test_pie_rejects_negative_values(self):
        with pytest.raises(ChartError, match="non-negative"):
            render_chart(["A", "B"], [["x", -1]], "pie")

    def test_pie_rejects_all_zero(self):
        with pytest.raises(ChartError, match="positive"):
            render_chart(["A", "B"], [["x", 0]], "pie")

    def test_histogram_needs_numeric_column(self):
        with pytest.raises(ChartError, match="numeric column"):
            render_chart(["A"], [["x"]], "histogram")


class TestToFloat:
    def test_coercions(self):
        assert _to_float(3) == 3.0
        assert _to_float(3.5) == 3.5
        assert _to_float(" 4.25 ") == 4.25
        assert _to_float(True) is None
        assert _to_float(None) is None
        assert _to_float("abc") is None
        assert _to_float(float("inf")) is None
        assert _to_float(float("nan")) is None

    def test_decimal_like_values(self):
        import decimal

        assert _to_float(decimal.Decimal("1.25")) == 1.25


class TestVectorChart:
    def test_list_vectors_render_png(self):
        _png(VECTOR_COLUMNS, VECTOR_ROWS, "vector")

    def test_dense_driver_values_render_png(self):
        rows = [[name, array.array("f", vector)] for name, vector in VECTOR_ROWS]
        _png(VECTOR_COLUMNS, rows, "vector")

    def test_sparse_driver_values_render_png(self):
        rows = [
            [
                "alpha",
                oracledb.SparseVector(3, array.array("I", [0]), array.array("d", [1.0])),
            ],
            [
                "beta",
                oracledb.SparseVector(3, array.array("I", [1]), array.array("d", [1.0])),
            ],
            [
                "gamma",
                oracledb.SparseVector(3, array.array("I", [2]), array.array("d", [1.0])),
            ],
        ]
        _png(VECTOR_COLUMNS, rows, "vector")

    def test_vector_only_column_renders(self):
        _png(["EMBEDDING"], [[vector] for _, vector in VECTOR_ROWS], "vector")

    def test_custom_axis_labels(self):
        _png(VECTOR_COLUMNS, VECTOR_ROWS, "vector", x_label="X", y_label="Y")

    def test_missing_vectors_are_skipped(self):
        rows = [*VECTOR_ROWS, ["missing", None]]
        _png(VECTOR_COLUMNS, rows, "vector")

    def test_many_points_are_not_annotated(self):
        rows = [[f"p{i}", [float(i), float(i % 3), float(i % 5)]] for i in range(20)]
        _png(VECTOR_COLUMNS, rows, "vector")


class TestVectorChartErrors:
    def test_needs_a_vector_column(self):
        with pytest.raises(ChartError, match="VECTOR column"):
            render_chart(["A", "B"], [["x", 1]], "vector")

    def test_needs_two_vectors(self):
        with pytest.raises(ChartError, match="at least two vectors"):
            render_chart(VECTOR_COLUMNS, [VECTOR_ROWS[0]], "vector")

    def test_needs_two_dimensions(self):
        rows = [["alpha", [1.0]], ["beta", [2.0]]]
        with pytest.raises(ChartError, match="at least two dimensions"):
            render_chart(VECTOR_COLUMNS, rows, "vector")

    def test_ragged_vectors(self):
        rows = [["alpha", [1.0, 2.0]], ["beta", [1.0, 2.0, 3.0]]]
        with pytest.raises(ChartError, match="same length"):
            render_chart(VECTOR_COLUMNS, rows, "vector")

    def test_identical_vectors(self):
        rows = [["alpha", [1.0, 2.0]], ["beta", [1.0, 2.0]]]
        with pytest.raises(ChartError, match="not all identical"):
            render_chart(VECTOR_COLUMNS, rows, "vector")

    def test_non_finite_values(self):
        rows = [["alpha", [1.0, 2.0]], ["beta", [float("inf"), 2.0]]]
        with pytest.raises(ChartError, match="finite"):
            render_chart(VECTOR_COLUMNS, rows, "vector")


class TestVectorValues:
    def test_dense_array(self):
        assert _vector_values(array.array("f", [1.0, 2.0])) == [1.0, 2.0]

    def test_plain_sequence(self):
        assert _vector_values([1, 2.5]) == [1.0, 2.5]
        assert _vector_values((1,)) == [1.0]

    def test_sparse_object_is_densified(self):
        sparse = oracledb.SparseVector(4, [0, 2], [1.5, 3.5])
        assert _vector_values(sparse) == [1.5, 0.0, 3.5, 0.0]

    def test_non_vectors(self):
        assert _vector_values(None) is None
        assert _vector_values("abc") is None
        assert _vector_values(3) is None
        assert _vector_values(b"\x01\x02") is None
        assert _vector_values([]) is None
        assert _vector_values([1, "x"]) is None


class TestProjectVectors:
    def test_axis_aligned_data_has_one_explained_component(self):
        xs, ys, explained = _project_vectors([[-1.0, 0.0], [0.0, 0.0], [1.0, 0.0]])
        assert explained[0] == pytest.approx(1.0)
        assert explained[0] >= explained[1]
        assert xs == sorted(xs)
        assert ys == pytest.approx([0.0, 0.0, 0.0])

    def test_variance_is_split_across_components(self):
        _, _, explained = _project_vectors([[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0], [0.0, -1.0]])
        assert explained[0] == pytest.approx(0.5, abs=1e-9)
        assert explained[1] == pytest.approx(0.5, abs=1e-9)
