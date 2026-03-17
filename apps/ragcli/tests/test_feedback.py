"""Tests for feedback collection and quality analysis."""
import math
from unittest.mock import MagicMock, call

from ragcli.feedback.collector import FeedbackCollector, _wilson_score
from ragcli.feedback.analyzer import FeedbackAnalyzer


# --- Wilson score tests ---

def test_wilson_score_no_data():
    assert _wilson_score(0, 0) == 0.5


def test_wilson_score_positive():
    score = _wilson_score(10, 0)
    assert score > 0.65, f"Expected >0.65, got {score}"


def test_wilson_score_mixed():
    score = _wilson_score(7, 3)
    assert 0.35 < score < 0.75, f"Expected between 0.35 and 0.75, got {score}"


# --- FeedbackCollector tests ---

def _make_mock_conn():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_conn, mock_cursor


def test_submit_chunk_feedback():
    mock_conn, mock_cursor = _make_mock_conn()
    collector = FeedbackCollector(mock_conn)

    collector.submit_chunk_feedback(
        query_id="q-123",
        chunk_id="c-456",
        rating=1,
        comment="Great chunk"
    )

    # Calls: INSERT feedback, MERGE counts, SELECT counts, UPDATE score
    assert mock_cursor.execute.call_count == 4

    # First call: FEEDBACK insert
    first_sql = mock_cursor.execute.call_args_list[0][0][0]
    first_params = mock_cursor.execute.call_args_list[0][0][1]
    assert "INSERT INTO FEEDBACK" in first_sql
    assert first_params["query_id"] == "q-123"
    assert first_params["chunk_id"] == "c-456"
    assert first_params["rating"] == 1
    assert first_params["target_type"] == "chunk"
    assert first_params["comment_text"] == "Great chunk"

    # Second call: MERGE INTO CHUNK_QUALITY
    second_sql = mock_cursor.execute.call_args_list[1][0][0]
    assert "MERGE INTO CHUNK_QUALITY" in second_sql

    # Should commit
    mock_conn.commit.assert_called()


def test_submit_answer_feedback():
    mock_conn, mock_cursor = _make_mock_conn()
    collector = FeedbackCollector(mock_conn)

    collector.submit_answer_feedback(query_id="q-789", rating=-1, comment="Bad answer")

    assert mock_cursor.execute.call_count == 1
    first_sql = mock_cursor.execute.call_args_list[0][0][0]
    first_params = mock_cursor.execute.call_args_list[0][0][1]
    assert "INSERT INTO FEEDBACK" in first_sql
    assert first_params["target_type"] == "answer"
    assert first_params["rating"] == -1
    mock_conn.commit.assert_called()


def test_get_chunk_quality_default():
    mock_conn, mock_cursor = _make_mock_conn()
    mock_cursor.fetchone.return_value = None

    collector = FeedbackCollector(mock_conn)
    score = collector.get_chunk_quality("c-nonexistent")

    assert score == 0.5


def test_get_chunk_quality_found():
    mock_conn, mock_cursor = _make_mock_conn()
    mock_cursor.fetchone.return_value = (0.82,)

    collector = FeedbackCollector(mock_conn)
    score = collector.get_chunk_quality("c-exists")

    assert score == 0.82


def test_get_chunk_qualities_batch():
    mock_conn, mock_cursor = _make_mock_conn()
    mock_cursor.fetchall.return_value = [
        ("c-1", 0.9),
        ("c-2", 0.3),
    ]

    collector = FeedbackCollector(mock_conn)
    result = collector.get_chunk_qualities(["c-1", "c-2", "c-3"])

    assert isinstance(result, dict)
    assert result["c-1"] == 0.9
    assert result["c-2"] == 0.3
    # Missing chunk should default to 0.5
    assert result["c-3"] == 0.5


def test_get_chunk_qualities_empty():
    mock_conn, mock_cursor = _make_mock_conn()
    collector = FeedbackCollector(mock_conn)
    result = collector.get_chunk_qualities([])
    assert result == {}


def test_get_feedback_stats():
    mock_conn, mock_cursor = _make_mock_conn()
    mock_cursor.fetchone.return_value = (42, 0.65, 30, 12)

    collector = FeedbackCollector(mock_conn)
    stats = collector.get_feedback_stats()

    assert stats["total_feedback"] == 42
    assert stats["avg_rating"] == 0.65
    assert stats["total_chunk_feedback"] == 30
    assert stats["total_answer_feedback"] == 12


# --- FeedbackAnalyzer tests ---

def test_get_quality_distribution():
    mock_conn, mock_cursor = _make_mock_conn()
    mock_cursor.fetchall.return_value = [
        ("0.0-0.2", 5),
        ("0.2-0.4", 10),
        ("0.4-0.6", 20),
        ("0.6-0.8", 15),
        ("0.8-1.0", 8),
    ]

    analyzer = FeedbackAnalyzer(mock_conn)
    dist = analyzer.get_quality_distribution()

    assert isinstance(dist, dict)
    assert mock_cursor.execute.call_count == 1


def test_get_low_quality_chunks():
    mock_conn, mock_cursor = _make_mock_conn()
    mock_cursor.fetchall.return_value = [
        ("c-bad1", 0.1, 2, 15),
        ("c-bad2", 0.25, 3, 10),
    ]

    analyzer = FeedbackAnalyzer(mock_conn)
    results = analyzer.get_low_quality_chunks(threshold=0.3, limit=20)

    assert len(results) == 2
    assert results[0]["chunk_id"] == "c-bad1"
    assert results[0]["quality_score"] == 0.1


def test_get_signal_performance():
    mock_conn, mock_cursor = _make_mock_conn()
    mock_cursor.fetchall.return_value = [
        (1, 25),
        (0, 10),
        (-1, 5),
    ]

    analyzer = FeedbackAnalyzer(mock_conn)
    perf = analyzer.get_signal_performance(limit=100)

    assert isinstance(perf, dict)
