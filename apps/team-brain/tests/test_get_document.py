"""`get_document`: full text by row id, and the row policy still applies to it.

A row the caller may not see is indistinguishable from a row that does not exist.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from team_brain.access import Identity
from team_brain.db import DocumentDB
from team_brain.schema import Document

pytestmark = pytest.mark.requires_oracle


def _seed(db: DocumentDB) -> None:
    now = datetime.now(UTC)
    long_body = "The batch cluster autoscaler max was raised from 6 to 10 nodes. " * 12
    db.upsert_document(
        Document("slack", "ops:1", "Autoscaler", long_body, now, author="jeff", domains=["ops"])
    )
    db.upsert_document(
        Document(
            "slack",
            "sales:1",
            "Deal desk",
            "Reps may offer up to 20% off list.",
            now,
            author="sam",
            domains=["sales"],
        )
    )
    db.upsert_document(
        Document(
            "markdown", "pub.md", "Public doc", "Everyone can read this.", now, url="file://pub.md"
        )
    )
    db.commit()


def test_full_text_is_returned_for_a_visible_row(db: DocumentDB) -> None:
    _seed(db)
    db.set_identity(Identity.principal("jeff"))
    row = db.get_document("slack::ops:1")
    assert row is not None
    assert row["author"] == "jeff"
    assert len(row["body"]) > 240, "full text, not a snippet"
    assert row["body"].count("6 to 10") == 12


def test_policy_hides_rows_from_get_document(db: DocumentDB) -> None:
    _seed(db)
    db.set_identity(Identity.principal("jeff"))
    assert db.get_document("slack::sales:1") is None, "jeff must not fetch a sales row by id"
    assert db.get_document("markdown::pub.md") is not None
    db.set_identity(Identity.principal("sam"))
    assert db.get_document("slack::ops:1") is None
    assert db.get_document("slack::sales:1") is not None
    db.set_identity(Identity.anonymous())
    assert db.get_document("slack::ops:1") is None
    assert db.get_document("markdown::pub.md") is not None


def test_bad_ids_are_simply_not_found(db: DocumentDB) -> None:
    _seed(db)
    db.set_identity(Identity.principal("brian"))
    assert db.get_document("no-separator") is None
    assert db.get_document("slack::does-not-exist") is None
    assert db.get_document("slack::ops:1") is not None
