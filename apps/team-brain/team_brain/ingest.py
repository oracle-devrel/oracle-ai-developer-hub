"""Ingestion runner: connector.fetch() -> enrich -> upsert (embedding in-database) -> tombstone.

One code path for every source. Enrichment is applied per document (a no-op for
sources that don't need it), the embedding is computed by the database inside
the MERGE that writes the row, upserts are idempotent by `(source, external_id)`,
and anything a connector no longer emits is tombstoned. Each run is logged to
`ingestion_runs`.

The runner switches the session into INGEST mode (see access.py): the write path
has to see every row to upsert and tombstone correctly. Nothing it does is
readable by a caller until that caller establishes its own identity.
"""

from __future__ import annotations

from dataclasses import dataclass

from team_brain.access import INGEST
from team_brain.connectors import build_connector
from team_brain.db import DocumentDB
from team_brain.enrich import embedding_text
from team_brain.schema import Document


@dataclass
class IngestResult:
    source: str
    upserted: int
    tombstoned: int
    skipped_fail_closed: int


def ingest(source: str, args: list[str], db: DocumentDB | None = None) -> IngestResult:
    owns_db = db is None
    db = db or DocumentDB()
    db.init_schema()
    db.set_identity(INGEST)
    run_id = db.record_run_start(source)
    upserted = 0
    tombstoned = 0
    skipped = 0
    try:
        connector = build_connector(source, args)
        docs: list[Document] = list(connector.fetch())

        # A restricted doc with an empty ACL is visible to no one. Warn, still
        # store it (so it is tracked and tombstonable); it can never surface.
        for d in docs:
            if d.fail_closed():
                skipped += 1

        seen: set[str] = set()
        for d in docs:
            db.upsert_document(d, embedding_text(d.title, d.body, d.metadata.get("_enriched")))
            seen.add(d.external_id)
            upserted += 1
        tombstoned = db.tombstone_missing(source, seen)
        # Commit the complete snapshot and its success log together.
        db.record_run_finish(run_id, upserted, tombstoned)
        return IngestResult(source, upserted, tombstoned, skipped)
    except Exception as exc:
        db.rollback()
        db.record_run_finish(run_id, 0, 0, error=str(exc))
        raise
    finally:
        if owns_db:
            db.close()
