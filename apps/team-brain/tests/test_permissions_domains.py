"""Domain leak matrix — group-based access enforced at retrieval.

This is the Exploration-Hour whiteboard turned into an executable guarantee.
Content is LABELED by domain at ingestion; the label is ENFORCED here, in the
database's row policy, before any row reaches the LLM. Leadership sees all; a
domain member sees only their grant; an identity with no grant sees only
company-wide content.

| doc domains   | jeff(ops) | julia(ops,mkt) | sam(sales) | brian(all) | anon(none) |
|---------------|-----------|----------------|------------|------------|------------|
| []  (public)  | visible   | visible        | visible    | visible    | visible    |
| [ops]         | visible   | visible        | ABSENT     | visible    | ABSENT     |
| [marketing]   | ABSENT    | visible        | ABSENT     | visible    | ABSENT     |
| [sales]       | ABSENT    | ABSENT         | visible    | visible    | ABSENT     |

Asserted through retrieval.search AND agent.answer (answer text + citations).

Oracle port: no `allowed_domains`/`all_domains` kwargs — a bare
`Identity.principal(username)` is enough; the database resolves the group
grant from the seeded `principals`/`group_grants` tables (via `tokens`, which
seeds them) and the row policy enforces it. `Identity.anonymous()` replaces
the old `ANONYMOUS` Principal sentinel for the no-grant case.
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

OPS = "ops_autoscaler_nodepool_reindex"
MKT = "marketing_utm_webinar_funnel"
SALES = "sales_discount_ceiling_dealdesk"
PUBLIC = "company_holiday_calendar_allhands"


def _seed(db: DocumentDB) -> None:
    rows = [
        Document("md", "pub", "Company handbook", f"everyone can read {PUBLIC}", datetime.now(UTC)),
        Document(
            "slack", "ops", "Ops runbook", f"{OPS} decision", datetime.now(UTC), domains=["ops"]
        ),
        Document(
            "slack",
            "mkt",
            "Marketing plan",
            f"{MKT} numbers",
            datetime.now(UTC),
            domains=["marketing"],
        ),
        Document(
            "slack", "sales", "Deal desk", f"{SALES} policy", datetime.now(UTC), domains=["sales"]
        ),
    ]
    for d in rows:
        db.upsert_document(d)
    db.commit()


def _bodies(results: list) -> str:
    return " ".join(e.title + " " + e.body for e in results)


def test_public_visible_to_everyone(db: DocumentDB, tokens: dict[str, str]) -> None:
    _seed(db)
    query = "company handbook everyone holiday allhands"
    for username in tokens:
        assert PUBLIC in _bodies(search(query, Identity.principal(username), db=db))
    assert PUBLIC in _bodies(search(query, Identity.anonymous(), db=db))


def test_jeff_ops_only(db: DocumentDB, tokens: dict[str, str]) -> None:
    _seed(db)
    jeff = Identity.principal("jeff")
    # ops content is visible
    assert OPS in _bodies(search("ops autoscaler nodepool reindex runbook", jeff, db=db))
    # marketing + sales content is absent no matter what jeff searches for
    assert MKT not in _bodies(search("marketing utm webinar funnel numbers", jeff, db=db))
    assert SALES not in _bodies(search("sales discount ceiling dealdesk policy", jeff, db=db))


def test_julia_ops_and_marketing_not_sales(db: DocumentDB, tokens: dict[str, str]) -> None:
    _seed(db)
    julia = Identity.principal("julia")
    assert OPS in _bodies(search("ops autoscaler nodepool reindex", julia, db=db))
    assert MKT in _bodies(search("marketing utm webinar funnel", julia, db=db))
    assert SALES not in _bodies(search("sales discount ceiling dealdesk", julia, db=db))


def test_sam_sales_only(db: DocumentDB, tokens: dict[str, str]) -> None:
    _seed(db)
    sam = Identity.principal("sam")
    assert SALES in _bodies(search("sales discount ceiling dealdesk", sam, db=db))
    assert OPS not in _bodies(search("ops autoscaler nodepool reindex", sam, db=db))
    assert MKT not in _bodies(search("marketing utm webinar funnel", sam, db=db))


def test_brian_sees_all_domains(db: DocumentDB, tokens: dict[str, str]) -> None:
    _seed(db)
    brian = Identity.principal("brian")
    assert OPS in _bodies(search("ops autoscaler nodepool reindex", brian, db=db))
    assert MKT in _bodies(search("marketing utm webinar funnel", brian, db=db))
    assert SALES in _bodies(search("sales discount ceiling dealdesk", brian, db=db))


def test_anonymous_sees_only_public(db: DocumentDB, tokens: dict[str, str]) -> None:
    _seed(db)
    # No token → no domain grant → only company-wide content.
    anon = Identity.anonymous()
    assert PUBLIC in _bodies(search("company handbook holiday allhands", anon, db=db))
    assert OPS not in _bodies(search("ops autoscaler nodepool reindex", anon, db=db))
    assert MKT not in _bodies(search("marketing utm webinar funnel", anon, db=db))
    assert SALES not in _bodies(search("sales discount ceiling dealdesk", anon, db=db))


def test_domain_enforced_in_agent_answer_and_citations(
    db: DocumentDB, tokens: dict[str, str]
) -> None:
    _seed(db)
    jeff = Identity.principal("jeff")
    result = answer("what is our sales discount ceiling policy?", jeff, db=db)
    # The sales policy must not reach the answer text, the evidence, or citations.
    assert SALES not in result["answer"]
    assert all(SALES not in e["snippet"] for e in result["evidence"])
    assert all(c["title"] != "Deal desk" for c in result["citations"])
