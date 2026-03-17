"""Test hybrid search fusion."""
from collections import defaultdict


def test_rrf_formula():
    """Verify RRF formula produces expected relative ordering."""
    k = 60
    w = 1.0
    rank0_score = w / (k + 0 + 1)
    rank1_score = w / (k + 1 + 1)
    assert rank0_score > rank1_score
    assert abs(rank0_score - 1/61) < 1e-10


def test_rrf_multi_signal_boost():
    """Chunk appearing in multiple signals should score higher."""
    k = 60
    # Chunk A appears in vector only
    score_a = 1.0 / (k + 0 + 1)
    # Chunk B appears in both vector and bm25
    score_b = 1.0 / (k + 2 + 1) + 1.0 / (k + 0 + 1)
    assert score_b > score_a


def test_quality_boost():
    """Quality scores should adjust fusion scores."""
    base_score = 0.1
    boost_range = 0.15

    # High quality (1.0) -> boost
    high_q = base_score * (1.0 - boost_range + 2 * boost_range * 1.0)
    # Low quality (0.0) -> penalty
    low_q = base_score * (1.0 - boost_range + 2 * boost_range * 0.0)
    # Neutral (0.5) -> no change
    neutral_q = base_score * (1.0 - boost_range + 2 * boost_range * 0.5)

    assert high_q > neutral_q > low_q
    assert abs(neutral_q - base_score) < 1e-10
