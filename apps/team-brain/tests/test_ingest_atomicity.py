"""A failed snapshot must leave the previous committed knowledge intact."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from team_brain.access import Identity
from team_brain.db import DocumentDB
from team_brain.ingest import ingest
from team_brain.schema import Document

pytestmark = pytest.mark.requires_oracle


@pytest.mark.parametrize("failure", ["upsert", "tombstone", "finish_log"])
def test_failed_snapshot_rolls_back_all_changes(db, monkeypatch, failure):
    now = datetime.now(UTC)
    db.upsert_document(
        Document(
            "atomic",
            "existing",
            "Original",
            "original private body",
            now,
            visibility="restricted",
            acl=["member"],
        )
    )
    db.upsert_document(Document("atomic", "missing", "Keep", "keep until success", now))
    db.commit()
    docs = [
        Document("atomic", "existing", "Changed", "changed body", now),
        Document("atomic", "new", "New", "new body", now),
    ]
    if failure == "upsert":
        docs.append(Document("atomic", "bad", "Bad", "invalid project", now, project="x" * 250))
    elif failure == "tombstone":
        original = db.tombstone_missing

        def fail_tombstone(source, seen):
            original(source, seen)
            raise RuntimeError("tombstone failure")

        monkeypatch.setattr(db, "tombstone_missing", fail_tombstone)
    else:
        original_finish = db.record_run_finish

        def fail_success_log(run_id, upserted, tombstoned, error=None):
            if error is None:
                raise RuntimeError("finish log failure")
            return original_finish(run_id, upserted, tombstoned, error)

        monkeypatch.setattr(db, "record_run_finish", fail_success_log)
    monkeypatch.setattr(
        "team_brain.ingest.build_connector", lambda *_: SimpleNamespace(fetch=lambda: iter(docs))
    )
    with pytest.raises(Exception, match="ORA-12899|tombstone failure|finish log failure"):
        ingest("atomic", [], db=db)

    reader = DocumentDB(identity=Identity.user("member"))
    try:
        assert reader.get_document("atomic::existing")["body"] == "original private body"
        assert reader.get_document("atomic::missing") is not None
        assert reader.get_document("atomic::new") is None
        reader.set_identity(Identity.anonymous())
        assert reader.get_document("atomic::existing") is None
        with reader.connection.cursor() as cur:
            cur.execute("SELECT upserted, tombstoned, error FROM ingestion_runs ORDER BY id DESC")
            upserted, tombstoned, error = cur.fetchone()
        assert (upserted, tombstoned) == (0, 0)
        assert error
    finally:
        reader.close()
