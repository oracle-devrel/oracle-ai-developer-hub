"""The two retrieval legs, run through Oracle's LangChain package.

  vector leg   -> OracleVS.similarity_search_with_score  (VECTOR_DISTANCE, cosine)
  keyword leg  -> OracleTextSearchRetriever              (Oracle Text CONTAINS)

Both point at the same `documents` table the ingest MERGE wrote, on the same
database session whose identity was established through `tb_session`. They are
plain SQL underneath, so the row policy filters them exactly like the hand-written
queries in db.py (`keyword_search_sql` / `vector_search_sql`). The test suite
asserts the two backends return the same rows in the same order.

The `metadata` JSON column doubles as the row LangChain hands back, which is why
db.py writes source / external_id / title / url / author / created_at / project
/ domains into it.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

# Imported eagerly on purpose. These pull in numpy's native extension, and a
# first-time import of a native module from inside a running server (the MCP
# stdio transport's worker context) deadlocks on Windows. Importing at module
# load, in the main thread, sidesteps that entirely.
from langchain_oracledb.embeddings import OracleEmbeddings
from langchain_oracledb.retrievers import OracleTextSearchRetriever
from langchain_oracledb.vectorstores import OracleVS
from langchain_oracledb.vectorstores.utils import DistanceStrategy

from team_brain.config import EMBEDDING_MODEL
from team_brain.db import _strip_stop_words

if TYPE_CHECKING:
    from team_brain.db import DocumentDB

TABLE = "DOCUMENTS"


def _row_key(md: dict[str, Any]) -> str:
    return f"{md.get('source')}::{md.get('external_id')}"


def _created_at(md: dict[str, Any]) -> datetime | None:
    raw = md.get("created_at")
    if not raw:
        return None
    dt = datetime.fromisoformat(str(raw))
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _row(md: dict[str, Any], body: str, score: float) -> dict[str, Any]:
    return {
        "id": _row_key(md),
        "source": md.get("source", ""),
        "external_id": md.get("external_id", ""),
        "title": md.get("title", "") or "",
        "body": body or "",
        "url": md.get("url", "") or "",
        "author": md.get("author", "") or "",
        "created_at": _created_at(md),
        "project": md.get("project", "default"),
        "metadata": md,
        "score": score,
    }


def _vector_store(db: DocumentDB) -> Any:
    conn = db.connection
    embeddings = OracleEmbeddings(
        conn=conn, params={"provider": "database", "model": EMBEDDING_MODEL}
    )
    return OracleVS(
        client=conn,
        embedding_function=embeddings,
        table_name=TABLE,
        distance_strategy=DistanceStrategy.COSINE,
    )


def vector_leg(db: DocumentDB, query: str, project: str | None, limit: int) -> list[dict[str, Any]]:
    """Cosine nearest neighbours; the query is embedded in-database by OracleEmbeddings."""
    vs = _vector_store(db)
    flt = {"project": {"$eq": project}} if project else None
    hits = vs.similarity_search_with_score(query, k=limit, filter=flt)
    # OracleVS returns cosine DISTANCE; similarity = 1 - distance, like the SQL leg.
    return [_row(dict(doc.metadata), doc.page_content, 1.0 - float(dist)) for doc, dist in hits]


def keyword_leg(
    db: DocumentDB, query: str, project: str | None, limit: int
) -> list[dict[str, Any]]:
    """Oracle Text CONTAINS over title + text, ranked by SCORE."""
    if project is not None:
        # OracleTextSearchRetriever 1.5 has no predicate/filter argument.
        # Use our bound SQL on the same session so project filtering precedes
        # TOP K; finite over-fetching can silently lose every matching row.
        return db.keyword_search_sql(query, project, limit)
    terms = ["".join(ch for ch in t if ch.isalnum()) for t in _strip_stop_words(query)]
    terms = [t for t in terms if t]
    if not terms:
        return []
    retriever = OracleTextSearchRetriever(
        client=db.connection,
        table_name=TABLE,
        column_name="TEXT",
        k=limit,
        return_scores=True,
        returned_columns=["METADATA"],
    )
    docs = retriever.invoke(" ".join(terms))
    rows: list[dict[str, Any]] = []
    for doc in docs:
        md = dict(doc.metadata.get("metadata") or {})
        # Oracle Text SCORE is 0..100; normalise to 0..1 like the SQL leg.
        rows.append(_row(md, doc.page_content, float(doc.metadata.get("score") or 0) / 100.0))
    return rows[:limit]
