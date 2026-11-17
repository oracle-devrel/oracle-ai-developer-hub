"""Retrieval headline: RRF fusion + age decay + light IDF.

`search()` takes an `Identity` (or reuses whatever identity is already on the
`db` session) instead of a raw username; the `db` fixture's INGEST identity
sees every row, which is exactly what these ranking-only tests want.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from team_brain.db import DocumentDB
from team_brain.retrieval import _age_decay, _idf_weight, search
from team_brain.schema import Document

pytestmark = pytest.mark.requires_oracle


def test_age_decay_monotonic() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    fresh = _age_decay(now, now, 180)
    old = _age_decay(now - timedelta(days=180), now, 180)
    older = _age_decay(now - timedelta(days=720), now, 180)
    assert fresh == 1.0
    assert abs(old - 0.5) < 1e-9  # one half-life
    assert older < old < fresh


def test_idf_weight_bounded_and_monotonic() -> None:
    assert _idf_weight(0.0) == 1.0
    assert _idf_weight(0.2) > _idf_weight(0.0)
    assert _idf_weight(999.0) == 1.5  # capped


def test_empty_and_stopword_queries_return_nothing(db: DocumentDB) -> None:
    db.upsert_document(Document("md", "d", "t", "kubernetes rollout", datetime.now(UTC)))
    db.commit()
    assert search("", db=db) == []
    assert search("the and of it", db=db) == []


def test_fresher_document_wins_on_age_decay(db: DocumentDB) -> None:
    text = "kubernetes blue-green deployment rollout strategy"
    now = datetime.now(UTC)
    db.upsert_document(Document("md", "fresh", "fresh", text, now))
    db.upsert_document(Document("md", "stale", "stale", text, now - timedelta(days=1200)))
    db.commit()
    results = search("kubernetes blue-green deployment rollout", db=db)
    assert results, "expected results"
    assert results[0].external_id == "fresh"


def test_doc_hit_by_both_rankers_outranks_single_ranker_hit(db: DocumentDB) -> None:
    now = datetime.now(UTC)
    # 'both' shares the query's exact terms (keyword + vector).
    db.upsert_document(
        Document("md", "both", "Stripe refund webhook", "handling the stripe refund webhook", now)
    )
    # 'weak' is only loosely related (vector-ish, no keyword overlap).
    db.upsert_document(
        Document("md", "weak", "Payments overview", "general notes on money movement", now)
    )
    db.commit()
    results = search("stripe refund webhook", db=db)
    assert results[0].external_id == "both"
    assert "keyword" in results[0].rankers_hit
