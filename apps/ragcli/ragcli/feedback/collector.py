"""Feedback collection and chunk quality scoring."""
import math
from typing import Dict, List, Optional

from ragcli.utils.helpers import generate_uuid
from ragcli.utils.logger import get_logger

logger = get_logger(__name__)


def _wilson_score(positive: int, negative: int, z: float = 1.96) -> float:
    """Calculate Wilson score lower bound for quality ranking.

    Returns a value between 0 and 1. With no data, defaults to 0.5.
    """
    n = positive + negative
    if n == 0:
        return 0.5
    p_hat = positive / n
    score = (p_hat + z * z / (2 * n) - z * math.sqrt((p_hat * (1 - p_hat) + z * z / (4 * n)) / n)) / (1 + z * z / n)
    return round(score, 4)


class FeedbackCollector:
    """Collects user feedback on answers and chunks, maintains quality scores."""

    def __init__(self, conn):
        self.conn = conn

    def submit_answer_feedback(self, query_id: str, rating: int, comment: Optional[str] = None) -> str:
        """Insert answer-level feedback. Rating: -1, 0, or +1."""
        feedback_id = generate_uuid()
        sql = """
            INSERT INTO FEEDBACK (feedback_id, query_id, chunk_id, target_type, rating, comment_text)
            VALUES (:feedback_id, :query_id, NULL, :target_type, :rating, :comment_text)
        """
        params = {
            "feedback_id": feedback_id,
            "query_id": query_id,
            "target_type": "answer",
            "rating": rating,
            "comment_text": comment,
        }
        with self.conn.cursor() as cursor:
            cursor.execute(sql, params)
        self.conn.commit()
        logger.info("Answer feedback recorded: %s (rating=%d)", feedback_id, rating)
        return feedback_id

    def submit_chunk_feedback(self, query_id: str, chunk_id: str, rating: int, comment: Optional[str] = None) -> str:
        """Insert chunk-level feedback and update quality score."""
        feedback_id = generate_uuid()
        insert_sql = """
            INSERT INTO FEEDBACK (feedback_id, query_id, chunk_id, target_type, rating, comment_text)
            VALUES (:feedback_id, :query_id, :chunk_id, :target_type, :rating, :comment_text)
        """
        params = {
            "feedback_id": feedback_id,
            "query_id": query_id,
            "chunk_id": chunk_id,
            "target_type": "chunk",
            "rating": rating,
            "comment_text": comment,
        }
        with self.conn.cursor() as cursor:
            cursor.execute(insert_sql, params)
            self._update_chunk_quality(cursor, chunk_id, rating)
        self.conn.commit()
        logger.info("Chunk feedback recorded: %s for chunk %s (rating=%d)", feedback_id, chunk_id, rating)
        return feedback_id

    def _update_chunk_quality(self, cursor, chunk_id: str, rating: int):
        """MERGE into CHUNK_QUALITY, recalculate Wilson score."""
        pos_inc = 1 if rating > 0 else 0
        neg_inc = 1 if rating < 0 else 0

        merge_sql = """
            MERGE INTO CHUNK_QUALITY cq
            USING (SELECT :chunk_id AS chunk_id FROM DUAL) src
            ON (cq.chunk_id = src.chunk_id)
            WHEN MATCHED THEN
                UPDATE SET
                    positive_count = cq.positive_count + :pos_inc,
                    negative_count = cq.negative_count + :neg_inc,
                    quality_score = :new_score_placeholder,
                    last_updated = SYSTIMESTAMP
            WHEN NOT MATCHED THEN
                INSERT (chunk_id, positive_count, negative_count, quality_score, last_updated)
                VALUES (:chunk_id_ins, :init_pos, :init_neg, :init_score, SYSTIMESTAMP)
        """
        # We need current counts to compute the new Wilson score.
        # For the INSERT case, we know the counts. For UPDATE, we use a two-step
        # approach: first try to read existing counts, then merge.
        # But since MERGE can't easily call Python mid-statement, we do a
        # simple MERGE that increments counts, then a follow-up UPDATE for the score.

        # Step 1: MERGE to upsert counts
        merge_counts_sql = """
            MERGE INTO CHUNK_QUALITY cq
            USING (SELECT :chunk_id AS chunk_id FROM DUAL) src
            ON (cq.chunk_id = src.chunk_id)
            WHEN MATCHED THEN
                UPDATE SET
                    positive_count = cq.positive_count + :pos_inc,
                    negative_count = cq.negative_count + :neg_inc,
                    last_updated = SYSTIMESTAMP
            WHEN NOT MATCHED THEN
                INSERT (chunk_id, positive_count, negative_count, quality_score, last_updated)
                VALUES (:chunk_id, :init_pos, :init_neg, :init_score, SYSTIMESTAMP)
        """
        init_score = _wilson_score(pos_inc, neg_inc)
        cursor.execute(merge_counts_sql, {
            "chunk_id": chunk_id,
            "pos_inc": pos_inc,
            "neg_inc": neg_inc,
            "init_pos": pos_inc,
            "init_neg": neg_inc,
            "init_score": init_score,
        })

        # Step 2: Read back counts and update Wilson score
        cursor.execute(
            "SELECT positive_count, negative_count FROM CHUNK_QUALITY WHERE chunk_id = :chunk_id",
            {"chunk_id": chunk_id}
        )
        row = cursor.fetchone()
        if row:
            new_score = _wilson_score(row[0], row[1])
            cursor.execute(
                "UPDATE CHUNK_QUALITY SET quality_score = :score WHERE chunk_id = :chunk_id",
                {"score": new_score, "chunk_id": chunk_id}
            )

    def get_feedback_stats(self) -> Dict:
        """Return aggregate feedback statistics."""
        sql = """
            SELECT
                COUNT(*) AS total_feedback,
                NVL(AVG(rating), 0) AS avg_rating,
                SUM(CASE WHEN target_type = 'chunk' THEN 1 ELSE 0 END) AS total_chunk_feedback,
                SUM(CASE WHEN target_type = 'answer' THEN 1 ELSE 0 END) AS total_answer_feedback
            FROM FEEDBACK
        """
        with self.conn.cursor() as cursor:
            cursor.execute(sql)
            row = cursor.fetchone()
        if row:
            return {
                "total_feedback": row[0],
                "avg_rating": row[1],
                "total_chunk_feedback": row[2],
                "total_answer_feedback": row[3],
            }
        return {
            "total_feedback": 0,
            "avg_rating": 0,
            "total_chunk_feedback": 0,
            "total_answer_feedback": 0,
        }

    def get_chunk_quality(self, chunk_id: str) -> float:
        """Return quality_score for a chunk (default 0.5 if not found)."""
        sql = "SELECT quality_score FROM CHUNK_QUALITY WHERE chunk_id = :chunk_id"
        with self.conn.cursor() as cursor:
            cursor.execute(sql, {"chunk_id": chunk_id})
            row = cursor.fetchone()
        if row is None:
            return 0.5
        return row[0]

    def get_chunk_qualities(self, chunk_ids: List[str]) -> Dict[str, float]:
        """Return {chunk_id: quality_score} for a batch. Missing chunks default to 0.5."""
        if not chunk_ids:
            return {}

        # Build bind variables for IN clause
        bind_names = [f":id_{i}" for i in range(len(chunk_ids))]
        bind_params = {f"id_{i}": cid for i, cid in enumerate(chunk_ids)}
        in_clause = ", ".join(bind_names)

        sql = f"SELECT chunk_id, quality_score FROM CHUNK_QUALITY WHERE chunk_id IN ({in_clause})"
        with self.conn.cursor() as cursor:
            cursor.execute(sql, bind_params)
            rows = cursor.fetchall()

        result = {cid: 0.5 for cid in chunk_ids}
        for row in rows:
            result[row[0]] = row[1]
        return result
