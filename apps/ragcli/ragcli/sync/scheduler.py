"""Sync scheduler for managing sync sources and events."""

from typing import Any, Dict, List, Optional

from ragcli.utils.helpers import generate_uuid
from ragcli.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_CONFIG = {
    "default_poll_interval": 300,
    "debounce_seconds": 2,
    "max_file_size_mb": 50,
    "supported_formats": ["pdf", "md", "txt", "html", "csv", "json"],
}


class SyncScheduler:
    """Manage sync sources and log sync events to Oracle DB."""

    def __init__(self, conn, config: Optional[Dict[str, Any]] = None):
        self._conn = conn
        self._config = config or DEFAULT_CONFIG

    def add_source(self, source_type: str, path: str,
                   glob_pattern: Optional[str] = None,
                   poll_interval: Optional[int] = None) -> str:
        """Add a new sync source. Returns the source_id."""
        source_id = generate_uuid()
        if poll_interval is None:
            poll_interval = self._config.get("default_poll_interval", 300)

        sql = """
            INSERT INTO SYNC_SOURCES (source_id, source_type, source_path,
                                      glob_pattern, poll_interval, enabled)
            VALUES (:source_id, :source_type, :source_path,
                    :glob_pattern, :poll_interval, 1)
        """
        params = {
            "source_id": source_id,
            "source_type": source_type,
            "source_path": path,
            "glob_pattern": glob_pattern,
            "poll_interval": poll_interval,
        }
        with self._conn.cursor() as cursor:
            cursor.execute(sql, params)
        self._conn.commit()
        logger.info("Added sync source %s (%s): %s", source_id, source_type, path)
        return source_id

    def remove_source(self, source_id: str) -> None:
        """Remove a sync source by ID."""
        sql = "DELETE FROM SYNC_SOURCES WHERE source_id = :source_id"
        with self._conn.cursor() as cursor:
            cursor.execute(sql, {"source_id": source_id})
        self._conn.commit()
        logger.info("Removed sync source %s", source_id)

    def list_sources(self) -> List[Dict[str, Any]]:
        """List all sync sources."""
        sql = """
            SELECT source_id, source_type, source_path, glob_pattern,
                   poll_interval, enabled, last_sync, metadata_json, created_at
            FROM SYNC_SOURCES
            ORDER BY created_at DESC
        """
        with self._conn.cursor() as cursor:
            cursor.execute(sql)
            columns = [col[0].lower() for col in cursor.description]
            rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def get_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Get a single sync source by ID."""
        sql = """
            SELECT source_id, source_type, source_path, glob_pattern,
                   poll_interval, enabled, last_sync, metadata_json, created_at
            FROM SYNC_SOURCES
            WHERE source_id = :source_id
        """
        with self._conn.cursor() as cursor:
            cursor.execute(sql, {"source_id": source_id})
            row = cursor.fetchone()
            if row is None:
                return None
            columns = [col[0].lower() for col in cursor.description]
        return dict(zip(columns, row))

    def log_event(self, source_id: str, file_path: str, event_type: str,
                  document_id: Optional[str] = None,
                  chunks_added: int = 0, chunks_removed: int = 0,
                  chunks_unchanged: int = 0) -> str:
        """Log a sync event. Returns the event_id."""
        event_id = generate_uuid()
        sql = """
            INSERT INTO SYNC_EVENTS (event_id, source_id, file_path, event_type,
                                     document_id, chunks_added, chunks_removed,
                                     chunks_unchanged)
            VALUES (:event_id, :source_id, :file_path, :event_type,
                    :document_id, :chunks_added, :chunks_removed,
                    :chunks_unchanged)
        """
        params = {
            "event_id": event_id,
            "source_id": source_id,
            "file_path": file_path,
            "event_type": event_type,
            "document_id": document_id,
            "chunks_added": chunks_added,
            "chunks_removed": chunks_removed,
            "chunks_unchanged": chunks_unchanged,
        }
        with self._conn.cursor() as cursor:
            cursor.execute(sql, params)
        self._conn.commit()
        logger.debug("Logged sync event %s for %s", event_id, file_path)
        return event_id

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent sync events."""
        sql = """
            SELECT event_id, source_id, file_path, event_type,
                   document_id, chunks_added, chunks_removed,
                   chunks_unchanged, processed_at
            FROM SYNC_EVENTS
            ORDER BY processed_at DESC
            FETCH FIRST :limit ROWS ONLY
        """
        with self._conn.cursor() as cursor:
            cursor.execute(sql, {"limit": limit})
            columns = [col[0].lower() for col in cursor.description]
            rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def update_last_sync(self, source_id: str) -> None:
        """Update the last_sync timestamp for a source."""
        sql = """
            UPDATE SYNC_SOURCES
            SET last_sync = SYSTIMESTAMP
            WHERE source_id = :source_id
        """
        with self._conn.cursor() as cursor:
            cursor.execute(sql, {"source_id": source_id})
        self._conn.commit()

    def get_sync_status(self) -> Dict[str, Any]:
        """Get a summary of sync status across all sources."""
        with self._conn.cursor() as cursor:
            # Total and enabled sources
            cursor.execute(
                "SELECT COUNT(*), SUM(CASE WHEN enabled = 1 THEN 1 ELSE 0 END) "
                "FROM SYNC_SOURCES"
            )
            total, enabled = cursor.fetchone()

            # Last sync times
            cursor.execute(
                "SELECT source_id, source_type, source_path, last_sync "
                "FROM SYNC_SOURCES ORDER BY last_sync DESC NULLS LAST"
            )
            sources_columns = ["source_id", "source_type", "source_path", "last_sync"]
            sources_status = [dict(zip(sources_columns, row))
                              for row in cursor.fetchall()]

            # Recent event count (last 24h)
            cursor.execute(
                "SELECT COUNT(*) FROM SYNC_EVENTS "
                "WHERE processed_at > SYSTIMESTAMP - INTERVAL '1' DAY"
            )
            recent_events = cursor.fetchone()[0]

        return {
            "total_sources": total or 0,
            "enabled_sources": enabled or 0,
            "sources": sources_status,
            "recent_event_count_24h": recent_events or 0,
        }
