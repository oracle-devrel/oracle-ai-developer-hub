"""Tombstoning: content a connector no longer emits is soft-deleted and hidden.

Oracle-specific nuance: under the `db` fixture's default INGEST identity the
row policy applies NO predicate at all (see access.policy_function_sql), so
even a tombstoned row would still show up in a plain keyword/vector search.
`db.stats()` is a hard-coded `deleted_at IS NULL` count (not policy-filtered)
so it always reflects reality; to prove a tombstoned row is HIDDEN from a
normal read we switch to a real `user` identity, which the policy does filter.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from team_brain.access import Identity
from team_brain.db import DocumentDB
from team_brain.schema import Document

pytestmark = pytest.mark.requires_oracle


def _doc(ext: str, body: str) -> Document:
    return Document("md", ext, ext, body, datetime.now(UTC))


def test_missing_id_is_tombstoned_and_hidden(db: DocumentDB) -> None:
    for ext in ("a", "b"):
        db.upsert_document(_doc(ext, f"content about {ext} deployment"))
    db.commit()

    # Re-sync sees only "a" → "b" tombstoned.
    tomb = db.tombstone_missing("md", {"a"})
    db.commit()
    assert tomb == 1
    assert db.stats()["live_documents"] == 1

    # A search as a real reader can no longer return the tombstoned doc.
    db.set_identity(Identity.user("demo"))
    rows = db.keyword_search("deployment", None, 10)
    assert all(r["external_id"] != "b" for r in rows)


def test_tombstoned_doc_resurrects_on_reappear(db: DocumentDB) -> None:
    db.upsert_document(_doc("a", "alpha content"))
    db.upsert_document(_doc("b", "beta content"))
    db.commit()
    db.tombstone_missing("md", {"a"})
    db.commit()
    assert db.stats()["live_documents"] == 1

    # b comes back in a later sync → resurrected (deleted_at cleared).
    db.upsert_document(_doc("b", "beta content again"))
    db.commit()
    assert db.stats()["live_documents"] == 2
