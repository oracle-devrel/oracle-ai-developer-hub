"""Tests for eval metrics, runner, and reporter modules."""
import json
from unittest.mock import MagicMock, patch, call

from ragcli.eval.metrics import EvalMetrics
from ragcli.eval.runner import EvalRunner
from ragcli.eval.reporter import EvalReporter


# --- Helper to build mock DB connection ---

def _make_mock_conn():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_conn, mock_cursor


# --- EvalMetrics._parse_score tests ---

def test_parse_score_valid():
    config = {"ollama": {"model": "gemma3:270m", "base_url": "http://localhost:11434"}}
    metrics = EvalMetrics(config)
    assert metrics._parse_score("0.85") == 0.85


def test_parse_score_with_text():
    config = {"ollama": {"model": "gemma3:270m", "base_url": "http://localhost:11434"}}
    metrics = EvalMetrics(config)
    assert metrics._parse_score("The score is 0.7 because the answer is mostly relevant") == 0.7


def test_parse_score_clamped():
    config = {"ollama": {"model": "gemma3:270m", "base_url": "http://localhost:11434"}}
    metrics = EvalMetrics(config)
    assert metrics._parse_score("1.5") == 1.0
    assert metrics._parse_score("-0.3") == 0.0


def test_parse_score_invalid():
    config = {"ollama": {"model": "gemma3:270m", "base_url": "http://localhost:11434"}}
    metrics = EvalMetrics(config)
    assert metrics._parse_score("no number here") == 0.0


# --- EvalMetrics.score_all test ---

@patch("ragcli.eval.metrics.generate_response")
def test_score_all(mock_gen):
    """score_all returns dict with all 4 metric keys."""
    # Each call to generate_response returns a generator yielding a score string
    mock_gen.side_effect = [
        iter(["0.9"]),   # faithfulness
        iter(["0.8"]),   # relevance
        iter(["0.7"]),   # context_precision
        iter(["0.6"]),   # context_recall
    ]
    config = {"ollama": {"model": "gemma3:270m", "base_url": "http://localhost:11434"}}
    metrics = EvalMetrics(config)
    result = metrics.score_all(
        question="What is RAG?",
        expected="RAG is retrieval-augmented generation",
        actual="RAG stands for retrieval-augmented generation",
        context="RAG is retrieval-augmented generation, a technique..."
    )
    assert result["faithfulness"] == 0.9
    assert result["relevance"] == 0.8
    assert result["context_precision"] == 0.7
    assert result["context_recall"] == 0.6
    assert mock_gen.call_count == 4


# --- EvalRunner tests ---

@patch("ragcli.eval.runner.generate_uuid", return_value="run-uuid-001")
def test_create_run(mock_uuid):
    mock_conn, mock_cursor = _make_mock_conn()
    config = {"ollama": {"model": "gemma3:270m"}}
    runner = EvalRunner(mock_conn, config)

    run_id = runner.create_run("synthetic")

    assert run_id == "run-uuid-001"
    # Should have called INSERT
    assert mock_cursor.execute.call_count == 1
    insert_sql = mock_cursor.execute.call_args_list[0][0][0]
    assert "INSERT INTO EVAL_RUNS" in insert_sql
    insert_params = mock_cursor.execute.call_args_list[0][0][1]
    assert insert_params["run_id"] == "run-uuid-001"
    assert insert_params["eval_mode"] == "synthetic"
    mock_conn.commit.assert_called_once()


def test_complete_run():
    mock_conn, mock_cursor = _make_mock_conn()
    # Mock the SELECT AVG query result
    mock_cursor.fetchone.return_value = (0.85, 0.75, 0.65, 0.55, 10)
    config = {"ollama": {"model": "gemma3:270m"}}
    runner = EvalRunner(mock_conn, config)

    runner.complete_run("run-uuid-001")

    # Should have called SELECT (averages) + UPDATE
    assert mock_cursor.execute.call_count == 2
    # First call: SELECT averages
    select_sql = mock_cursor.execute.call_args_list[0][0][0]
    assert "AVG" in select_sql
    # Second call: UPDATE
    update_sql = mock_cursor.execute.call_args_list[1][0][0]
    assert "UPDATE EVAL_RUNS" in update_sql
    update_params = mock_cursor.execute.call_args_list[1][0][1]
    assert update_params["avg_faithfulness"] == 0.85
    assert update_params["avg_relevance"] == 0.75
    assert update_params["avg_context_precision"] == 0.65
    assert update_params["avg_context_recall"] == 0.55
    assert update_params["total_pairs"] == 10
    mock_conn.commit.assert_called()


# --- EvalReporter tests ---

def test_compare_runs():
    mock_conn, mock_cursor = _make_mock_conn()
    reporter = EvalReporter(mock_conn)

    # Mock two sequential fetchone calls for the two runs
    mock_cursor.fetchone.side_effect = [
        # run 1
        ("run-1", "synthetic", None, None, 0.80, 0.70, 0.60, 0.50, 10, None),
        # run 2
        ("run-2", "synthetic", None, None, 0.90, 0.75, 0.65, 0.60, 15, None),
    ]

    result = reporter.compare_runs("run-1", "run-2")

    assert result is not None
    deltas = result["deltas"]
    # run2 - run1
    assert abs(deltas["faithfulness"] - 0.10) < 0.001
    assert abs(deltas["relevance"] - 0.05) < 0.001
    assert abs(deltas["context_precision"] - 0.05) < 0.001
    assert abs(deltas["context_recall"] - 0.10) < 0.001


def test_format_report():
    mock_conn, _ = _make_mock_conn()
    reporter = EvalReporter(mock_conn)

    report = {
        "run_id": "run-001",
        "eval_mode": "synthetic",
        "avg_faithfulness": 0.85,
        "avg_relevance": 0.75,
        "avg_context_precision": 0.65,
        "avg_context_recall": 0.55,
        "total_pairs": 10,
        "results": [],
    }
    text = reporter.format_report_text(report)

    assert "run-001" in text
    assert "synthetic" in text
    assert "0.85" in text
    assert "0.75" in text
    assert "0.65" in text
    assert "0.55" in text
    assert "10" in text
