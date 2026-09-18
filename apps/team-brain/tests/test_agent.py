"""Agent orchestration: plan → execute (parallel) → synthesize, with dedupe.

Oracle port: `answer(question, identity, ...)` takes an `Identity`, not a raw
username string.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from team_brain.access import Identity
from team_brain.agent import answer
from team_brain.db import DocumentDB
from team_brain.ingest import ingest
from team_brain.schema import Document

pytestmark = pytest.mark.requires_oracle


def test_answer_shape_and_citations(db: DocumentDB, seed_docs: str) -> None:
    ingest("markdown", [seed_docs])
    result = answer("how do we roll back a billing deploy?", Identity.user("alice"))
    assert set(result) == {"answer", "citations", "evidence", "experts", "plan"}
    assert result["evidence"]
    assert result["answer"]


def test_evidence_deduped_by_id(db: DocumentDB) -> None:
    # A doc that both rankers return must appear once in evidence.
    db.upsert_document(
        Document(
            "md",
            "d",
            "Stripe refund webhook",
            "the stripe refund webhook handler",
            datetime.now(UTC),
        )
    )
    db.commit()
    result = answer("stripe refund webhook", Identity.user("demo"))
    ids = [e["id"] for e in result["evidence"]]
    assert len(ids) == len(set(ids))


def test_who_knows_populates_experts(db: DocumentDB) -> None:
    for i in range(3):
        db.upsert_document(
            Document(
                "slack",
                f"t{i}",
                "billing question",
                "how does billing refund work",
                datetime.now(UTC),
                author="alice",
            )
        )
    db.commit()
    result = answer("who knows about billing refunds?", Identity.user("demo"))
    # offline planner runs all tools, so who_knows executes
    assert any(x["author"] == "alice" for x in result["experts"])
