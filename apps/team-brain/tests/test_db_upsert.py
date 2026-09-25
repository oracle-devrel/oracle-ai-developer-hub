"""Idempotent upsert by (source, external_id).

Oracle port: `upsert_document(doc, embed_text=None)` takes an optional TEXT to
embed (the database computes the vector in-place via VECTOR_EMBEDDING); there
is no local vector to pass in. `keyword_search` no longer takes a username —
identity lives on the session (the `db` fixture defaults to INGEST, which
sees every row, so no explicit identity switch is needed for these tests).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from team_brain.db import DocumentDB
from team_brain.schema import Document

pytestmark = pytest.mark.requires_oracle


def _doc(body: str = "original body") -> Document:
    return Document(
        source="md",
        external_id="doc-1",
        title="Runbook",
        body=body,
        created_at=datetime.now(UTC),
    )


def test_reingest_same_doc_no_duplicate(db: DocumentDB) -> None:
    d = _doc()
    db.upsert_document(d)
    db.upsert_document(d)
    db.commit()
    assert db.stats()["live_documents"] == 1


def test_changed_body_updates_in_place(db: DocumentDB) -> None:
    db.upsert_document(_doc("original body"))
    db.commit()
    db.upsert_document(_doc("updated body with refund logic"))
    db.commit()
    assert db.stats()["live_documents"] == 1
    rows = db.keyword_search("refund", None, 5)
    assert any("refund" in r["body"] for r in rows)


def test_content_hash_changes_with_body() -> None:
    unchanged = _doc("original body").content_hash()
    assert _doc("original body").content_hash() == unchanged
    assert _doc("a totally different body").content_hash() != unchanged


def test_distinct_ids_are_distinct_rows(db: DocumentDB) -> None:
    for i in range(3):
        d = Document("md", f"doc-{i}", "t", "body", datetime.now(UTC))
        db.upsert_document(d)
    db.commit()
    assert db.stats()["live_documents"] == 3
