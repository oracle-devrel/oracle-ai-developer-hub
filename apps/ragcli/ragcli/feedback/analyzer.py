"""Feedback analysis and quality distribution reporting."""
from typing import Dict, List, Optional

from ragcli.feedback.collector import _wilson_score
from ragcli.utils.logger import get_logger

logger = get_logger(__name__)


class FeedbackAnalyzer:
    """Analyzes collected feedback to surface quality insights."""

    def __init__(self, conn):
        self.conn = conn

    def get_signal_performance(self, limit: int = 100) -> Dict:
        """Return counts of feedback per rating value for recent chunk feedback.

        Since search-signal provenance isn't stored yet, this returns
        overall rating distribution for chunk-level feedback.
        """
        sql = """
            SELECT rating, COUNT(*) AS cnt
            FROM FEEDBACK
            WHERE target_type = 'chunk' AND chunk_id IS NOT NULL
            AND ROWNUM <= :lim
            GROUP BY rating
            ORDER BY rating
        """
        with self.conn.cursor() as cursor:
            cursor.execute(sql, {"lim": limit})
            rows = cursor.fetchall()

        result = {}
        for row in rows:
            result[row[0]] = row[1]
        return result

    def get_quality_distribution(self) -> Dict[str, int]:
        """Return chunk counts bucketed by quality_score ranges."""
        sql = """
            SELECT
                CASE
                    WHEN quality_score < 0.2 THEN '0.0-0.2'
                    WHEN quality_score < 0.4 THEN '0.2-0.4'
                    WHEN quality_score < 0.6 THEN '0.4-0.6'
                    WHEN quality_score < 0.8 THEN '0.6-0.8'
                    ELSE '0.8-1.0'
                END AS bucket,
                COUNT(*) AS cnt
            FROM CHUNK_QUALITY
            GROUP BY
                CASE
                    WHEN quality_score < 0.2 THEN '0.0-0.2'
                    WHEN quality_score < 0.4 THEN '0.2-0.4'
                    WHEN quality_score < 0.6 THEN '0.4-0.6'
                    WHEN quality_score < 0.8 THEN '0.6-0.8'
                    ELSE '0.8-1.0'
                END
            ORDER BY bucket
        """
        with self.conn.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()

        return {row[0]: row[1] for row in rows}

    def get_low_quality_chunks(self, threshold: float = 0.3, limit: int = 20) -> List[Dict]:
        """Return chunks with quality_score below threshold, worst first."""
        sql = """
            SELECT chunk_id, quality_score, positive_count, negative_count
            FROM CHUNK_QUALITY
            WHERE quality_score < :threshold
            ORDER BY quality_score ASC
            FETCH FIRST :lim ROWS ONLY
        """
        with self.conn.cursor() as cursor:
            cursor.execute(sql, {"threshold": threshold, "lim": limit})
            rows = cursor.fetchall()

        return [
            {
                "chunk_id": row[0],
                "quality_score": row[1],
                "positive_count": row[2],
                "negative_count": row[3],
            }
            for row in rows
        ]

    def recalibrate_all_quality_scores(self) -> int:
        """Recalculate all quality_scores from raw counts using Wilson score.

        Returns the number of rows updated.
        """
        select_sql = "SELECT chunk_id, positive_count, negative_count FROM CHUNK_QUALITY"
        update_sql = "UPDATE CHUNK_QUALITY SET quality_score = :score, last_updated = SYSTIMESTAMP WHERE chunk_id = :chunk_id"

        updated = 0
        with self.conn.cursor() as cursor:
            cursor.execute(select_sql)
            rows = cursor.fetchall()

            for row in rows:
                chunk_id, pos, neg = row[0], row[1], row[2]
                new_score = _wilson_score(pos, neg)
                cursor.execute(update_sql, {"score": new_score, "chunk_id": chunk_id})
                updated += 1

        self.conn.commit()
        logger.info("Recalibrated %d chunk quality scores", updated)
        return updated
