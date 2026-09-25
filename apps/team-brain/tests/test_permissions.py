"""The permission leak matrix — asserted at every read layer.

| doc state              | acl     | alice        | bob     |
|------------------------|---------|--------------|---------|
| public                  | -       | visible      | visible |
| restricted              | [bob]   | ABSENT       | visible |
| tombstoned              | any     | absent       | absent  |
| project=x (query in y)  | -       | absent       | absent  |
| restricted, empty acl   | []      | ABSENT       | absent  |

Checked through retrieval.search AND agent.answer (answer text + citations).
The MCP layer is covered in test_mcp_server.py; the database-level guarantees
(no-identity session sees zero rows, context cannot be forged) are covered in
test_policy_in_database.py.

Oracle port: `alice`/`bob` are `Identity.user(...)` — a raw username with no
domain grant, ACL-checked only (the old `requesting_user` string argument).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from team_brain.access import Identity
from team_brain.agent import answer
from team_brain.db import DocumentDB
from team_brain.retrieval import search
from team_brain.schema import Document

pytestmark = pytest.mark.requires_oracle

SECRET = "hunter2_prod_billing_secret"  # in the bob-visible postmortem
ORPHAN = "orphan_xyzzy_secret"  # in the empty-acl channel, visible to nobody


def _seed(db: DocumentDB) -> None:
    rows = [
        Document(
            "md",
            "pub",
            "Public deploy doc",
            "public knowledge about deployment pipeline",
            datetime.now(UTC),
        ),
        Document(
            "slack",
            "sec",
            "Security postmortem",
            f"the leaked password {SECRET} caused the outage",
            datetime.now(UTC),
            visibility="restricted",
            acl=["bob"],
        ),
        Document(
            "md",
            "proj",
            "Project X only",
            "roadmap details for project apollo",
            datetime.now(UTC),
            project="apollo",
        ),
        Document(
            "slack",
            "closed",
            "Nobody channel",
            f"orphan secret {ORPHAN} in an empty-acl channel",
            datetime.now(UTC),
            visibility="restricted",
            acl=[],
        ),
    ]
    for d in rows:
        db.upsert_document(d)
    # a tombstoned public doc
    db.upsert_document(
        Document("md", "old", "Old doc", "deployment history archived", datetime.now(UTC))
    )
    db.commit()
    db.tombstone_missing("md", {"pub", "proj"})  # tombstones "old"
    db.commit()


def _titles(results: list) -> set[str]:
    return {e.title for e in results}


def test_public_visible_to_all(db: DocumentDB, alice: Identity, bob: Identity) -> None:
    _seed(db)
    assert "Public deploy doc" in _titles(search("deployment pipeline", alice, db=db))
    assert "Public deploy doc" in _titles(search("deployment pipeline", bob, db=db))


def test_restricted_absent_for_non_member_at_search(
    db: DocumentDB, alice: Identity, bob: Identity
) -> None:
    _seed(db)
    alice_results = search("leaked password outage postmortem", alice, db=db)
    assert "Security postmortem" not in _titles(alice_results)
    assert all(SECRET not in e.body for e in alice_results)
    bob_results = search("leaked password outage postmortem", bob, db=db)
    assert "Security postmortem" in _titles(bob_results)


def test_restricted_absent_in_agent_answer_and_citations(db: DocumentDB, alice: Identity) -> None:
    _seed(db)
    result = answer(f"what is the {SECRET}?", alice, db=db)
    assert SECRET not in result["answer"]
    assert all(SECRET not in e["snippet"] for e in result["evidence"])
    assert all(c["title"] != "Security postmortem" for c in result["citations"])


def test_tombstoned_absent_for_everyone(db: DocumentDB) -> None:
    _seed(db)
    for user in ("alice", "bob"):
        assert "Old doc" not in _titles(
            search("deployment history archived", Identity.user(user), db=db)
        )


def test_project_scoping(db: DocumentDB, alice: Identity) -> None:
    _seed(db)
    # Bounding the query to project 'default' hides the apollo-only doc.
    scoped = search("roadmap apollo", alice, project="default", db=db)
    assert "Project X only" not in _titles(scoped)
    unscoped = search("roadmap apollo", alice, db=db)
    assert "Project X only" in _titles(unscoped)


def test_empty_acl_restricted_is_fail_closed(db: DocumentDB) -> None:
    _seed(db)
    for user in ("alice", "bob", "carla"):
        results = search("orphan secret empty channel", Identity.user(user), db=db)
        assert "Nobody channel" not in _titles(results)
        assert all(ORPHAN not in e.body for e in results)
