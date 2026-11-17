"""End-to-end: ingest → embed (in-database) → upsert → tombstone → search →
agent → citations.

The single test that proves the whole spine on the real Oracle AI Database
Free container.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from team_brain.access import Identity
from team_brain.agent import answer
from team_brain.db import DocumentDB
from team_brain.ingest import ingest

pytestmark = pytest.mark.requires_oracle


def test_full_pipeline_markdown_and_slack(
    db: DocumentDB, seed_docs: str, slack_export: str
) -> None:
    md = ingest("markdown", [seed_docs])
    sl = ingest("slack", ["--export", slack_export])
    assert md.upserted == 2
    assert sl.upserted == 3

    stats = db.stats()
    assert stats["by_source"]["markdown"] == 2
    assert stats["by_source"]["slack"] == 3

    # Retrieval → agent → cited answer (offline synthesis).
    result = answer("how do we deploy the billing service?", Identity.user("alice"))
    assert result["evidence"], "expected evidence"
    assert result["citations"], "expected citations"
    assert any(
        "deploy" in e["title"].lower() or "deploy" in e["snippet"].lower()
        for e in result["evidence"]
    )
    assert result["plan"]["tools"]


def test_reingest_is_idempotent(db: DocumentDB, seed_docs: str) -> None:
    ingest("markdown", [seed_docs])
    first = db.stats()["live_documents"]
    ingest("markdown", [seed_docs])
    assert db.stats()["live_documents"] == first  # no duplication


def test_removed_source_doc_is_tombstoned(db: DocumentDB, tmp_path: Path) -> None:
    (tmp_path / "keep.md").write_text("# Keep\n\npersistent knowledge", encoding="utf-8")
    gone = tmp_path / "gone.md"
    gone.write_text("# Gone\n\ntransient knowledge", encoding="utf-8")

    r1 = ingest("markdown", [str(tmp_path)])
    assert r1.upserted == 2

    gone.unlink()
    r2 = ingest("markdown", [str(tmp_path)])
    assert r2.upserted == 1
    assert r2.tombstoned == 1
    assert db.stats()["live_documents"] == 1
