"""Hybrid retrieval: two legs over one table, fused by rank, filtered by the database.

Naive RAG stops at "embed everything, take the top-k by cosine." On real team
data that loses twice: exact strings (error codes, flag names) that only keyword
search nails, and stale-but-similar documents that crowd out fresher answers.

  1. Run BOTH a vector leg (VECTOR_DISTANCE over the in-database embeddings) and
     a keyword leg (Oracle Text CONTAINS). Each leg is a plain query on the
     `documents` table, so the row policy filters both. There is no permission
     code in this module.
  2. Merge them with Reciprocal Rank Fusion (RRF): fusion over ranks, not raw
     scores, so the Oracle Text SCORE vs cosine scale mismatch does not matter.
  3. Multiply in an age-decay factor so fresher knowledge wins ties.
  4. Light IDF-style boost from the keyword leg's score.

Both legs can run through Oracle's LangChain package (OracleVS +
OracleTextSearchRetriever, the default) or as the equivalent plain SQL. The
test suite asserts the two agree.

`_naive_linear_blend` is kept as the workshop's "before" so the RRF win stays
visible side by side.

This module is RETRIEVAL POLICY: the team's standing answer to "what does
relevant mean here." It lives in the shared substrate rather than in anyone's
personal second brain. See docs/PERSONAL_VS_TEAM.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from team_brain.access import Identity
from team_brain.config import AGE_HALF_LIFE_DAYS, RRF_K, SEARCH_DEFAULT_LIMIT
from team_brain.db import _STOP_WORDS, DocumentDB


def _has_content(query: str) -> bool:
    """A query with no non-stop-word alphanumeric term has no search intent."""
    return any(t.lower() not in _STOP_WORDS and any(c.isalnum() for c in t) for t in query.split())


@dataclass
class Evidence:
    """One retrieved, policy-cleared document with a fused score."""

    id: str
    source: str
    external_id: str
    title: str
    body: str
    url: str
    author: str
    created_at: datetime
    metadata: dict[str, Any]
    score: float
    rankers_hit: list[str] = field(default_factory=list)

    @property
    def domains(self) -> list[str]:
        return list(self.metadata.get("domains") or [])

    def access_label(self) -> str:
        """Why this row was visible: its domain labels, or that it is a private (ACL) row."""
        label = " + ".join(self.domains) if self.domains else "company-wide"
        if self.metadata.get("visibility") == "restricted":
            return f"private (members only){', ' + label if self.domains else ''}"
        return label

    def snippet(self, length: int = 240) -> str:
        text = " ".join(self.body.split())
        return text[: length - 1] + "..." if len(text) > length else text

    def to_row(self) -> dict[str, Any]:
        """Plain dict for MCP / JSON output. Rows carry their labels so a demo can
        point at an answer and show WHY it was allowed."""
        return {
            "id": self.id,
            "source": self.source,
            "title": self.title,
            "url": self.url,
            "author": self.author,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "snippet": self.snippet(),
            "score": round(self.score, 5),
            "rankers_hit": self.rankers_hit,
            "domains": self.domains,
            "access": self.access_label(),
        }


def _age_decay(created_at: datetime | None, now: datetime, half_life_days: float) -> float:
    if created_at is None:
        return 1.0
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    age_days = max(0.0, (now - created_at).total_seconds() / 86400.0)
    return float(0.5 ** (age_days / half_life_days))


def _idf_weight(kw_score: float) -> float:
    """Light IDF-style boost from the keyword leg's (0..1) score, in [1.0, 1.5]."""
    return 1.0 + min(0.5, kw_score)


def _evidence_from(row: dict[str, Any], score: float, rankers: list[str]) -> Evidence:
    return Evidence(
        id=str(row["id"]),
        source=row["source"],
        external_id=row["external_id"],
        title=row["title"],
        body=row["body"],
        url=row["url"],
        author=row["author"],
        created_at=row["created_at"],
        metadata=row["metadata"] or {},
        score=score,
        rankers_hit=rankers,
    )


def _open(db: DocumentDB | None, identity: Identity | None) -> tuple[DocumentDB, bool]:
    """Use the caller's session, or open one for this identity."""
    if db is not None:
        if identity is not None and db.identity != identity:
            db.set_identity(identity)
        return db, False
    if identity is None:
        raise ValueError("search needs an Identity when no DocumentDB session is given")
    return DocumentDB(identity=identity), True


def search(
    query: str,
    identity: Identity | None = None,
    project: str | None = None,
    limit: int = SEARCH_DEFAULT_LIMIT,
    db: DocumentDB | None = None,
    now: datetime | None = None,
) -> list[Evidence]:
    """Policy-filtered hybrid search -> fused, freshness-aware Evidence list.

    Who is asking is a property of the database session (`identity`), not an
    argument the SQL is built from. Pass an Identity, or a DocumentDB whose
    identity is already set.
    """
    if not query.strip() or not _has_content(query):
        return []
    now = now or datetime.now(UTC)
    db, owns = _open(db, identity)
    try:
        over = max(limit * 3, 15)
        kw_rows = db.keyword_search(query, project, over)
        vec_rows = db.vector_search(query, project, over)
    finally:
        if owns:
            db.close()

    by_id: dict[str, dict[str, Any]] = {}
    rrf: dict[str, float] = {}
    rankers: dict[str, list[str]] = {}
    kw_score_by_id: dict[str, float] = {}

    for rank, row in enumerate(kw_rows):
        did = str(row["id"])
        by_id.setdefault(did, row)
        rrf[did] = rrf.get(did, 0.0) + 1.0 / (RRF_K + rank)
        rankers.setdefault(did, []).append("keyword")
        kw_score_by_id[did] = row["score"]

    for rank, row in enumerate(vec_rows):
        did = str(row["id"])
        by_id.setdefault(did, row)
        rrf[did] = rrf.get(did, 0.0) + 1.0 / (RRF_K + rank)
        rankers.setdefault(did, []).append("vector")

    results: list[Evidence] = []
    for did, base in rrf.items():
        row = by_id[did]
        fused = base * _age_decay(row["created_at"], now, AGE_HALF_LIFE_DAYS)
        fused *= _idf_weight(kw_score_by_id.get(did, 0.0))
        results.append(_evidence_from(row, fused, rankers[did]))

    results.sort(key=lambda e: e.score, reverse=True)
    return results[:limit]


def _naive_linear_blend(
    query: str,
    identity: Identity | None = None,
    project: str | None = None,
    limit: int = SEARCH_DEFAULT_LIMIT,
    vector_weight: float = 0.7,
    keyword_weight: float = 0.3,
    db: DocumentDB | None = None,
) -> list[Evidence]:
    """The 'before': fixed-weight blend of min-max-normalized raw scores.

    Kept ONLY for the workshop before/after. Its flaw: Oracle Text SCORE and
    cosine similarity live on different scales, so a single linear weight is a
    guess that RRF removes the need for.
    """
    db, owns = _open(db, identity)
    try:
        over = max(limit * 3, 15)
        kw_rows = db.keyword_search(query, project, over)
        vec_rows = db.vector_search(query, project, over)
    finally:
        if owns:
            db.close()

    scores: dict[str, dict[str, float]] = {}
    by_id: dict[str, dict[str, Any]] = {}
    for row in kw_rows:
        did = str(row["id"])
        by_id.setdefault(did, row)
        scores.setdefault(did, {"keyword": 0.0, "vector": 0.0})["keyword"] = row["score"]
    for row in vec_rows:
        did = str(row["id"])
        by_id.setdefault(did, row)
        scores.setdefault(did, {"keyword": 0.0, "vector": 0.0})["vector"] = row["score"]

    for kind in ("keyword", "vector"):
        vals = [s[kind] for s in scores.values() if s[kind] > 0]
        if not vals:
            continue
        lo, hi = min(vals), max(vals)
        spread = hi - lo
        for s in scores.values():
            if s[kind] > 0:
                s[kind] = (s[kind] - lo) / spread if spread > 0 else 1.0

    out: list[Evidence] = []
    for did, s in scores.items():
        combined = vector_weight * s["vector"] + keyword_weight * s["keyword"]
        out.append(_evidence_from(by_id[did], combined, []))
    out.sort(key=lambda e: e.score, reverse=True)
    return out[:limit]
