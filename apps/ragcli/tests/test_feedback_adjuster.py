"""Test feedback-driven weight adjuster."""
from unittest.mock import MagicMock, call
from ragcli.feedback.adjuster import WeightAdjuster


def _make_mock_conn():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_conn, mock_cursor


def test_quality_boost_neutral():
    mock_conn, _ = _make_mock_conn()
    adjuster = WeightAdjuster(mock_conn)
    boost = adjuster.get_quality_boost(0.5)
    assert boost == 0.0


def test_quality_boost_positive():
    mock_conn, _ = _make_mock_conn()
    adjuster = WeightAdjuster(mock_conn)
    boost = adjuster.get_quality_boost(1.0)
    assert abs(boost - 0.15) < 1e-9


def test_quality_boost_negative():
    mock_conn, _ = _make_mock_conn()
    adjuster = WeightAdjuster(mock_conn)
    boost = adjuster.get_quality_boost(0.0)
    assert abs(boost - (-0.15)) < 1e-9


def test_quality_boost_custom_range():
    mock_conn, _ = _make_mock_conn()
    adjuster = WeightAdjuster(mock_conn)
    boost = adjuster.get_quality_boost(1.0, boost_range=0.2)
    assert abs(boost - 0.2) < 1e-9


def test_strengthen_graph_edges():
    mock_conn, mock_cursor = _make_mock_conn()
    adjuster = WeightAdjuster(mock_conn)
    adjuster.strengthen_graph_edges(["chunk-1", "chunk-2"], factor=1.1)

    mock_cursor.execute.assert_called_once()
    sql_arg = mock_cursor.execute.call_args[0][0]
    assert "LEAST" in sql_arg
    assert "KG_RELATIONSHIPS" in sql_arg
    params = mock_cursor.execute.call_args[0][1]
    assert params["factor"] == 1.1
    mock_conn.commit.assert_called()


def test_weaken_graph_edges():
    mock_conn, mock_cursor = _make_mock_conn()
    adjuster = WeightAdjuster(mock_conn)
    adjuster.weaken_graph_edges(["chunk-1", "chunk-2"], factor=0.9)

    mock_cursor.execute.assert_called_once()
    sql_arg = mock_cursor.execute.call_args[0][0]
    assert "GREATEST" in sql_arg
    assert "KG_RELATIONSHIPS" in sql_arg
    params = mock_cursor.execute.call_args[0][1]
    assert params["factor"] == 0.9
    mock_conn.commit.assert_called()


def test_adjust_search_weights_returns_current():
    mock_conn, _ = _make_mock_conn()
    adjuster = WeightAdjuster(mock_conn)
    current = {"bm25": 1.0, "vector": 1.0, "graph": 0.8}
    result = adjuster.adjust_search_weights(current)
    assert result == current
