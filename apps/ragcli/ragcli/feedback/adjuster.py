"""Feedback-driven weight adjuster for search signals and graph edges."""

from ragcli.utils.logger import get_logger

logger = get_logger(__name__)


class WeightAdjuster:
    """Adjusts search weights and graph edge strengths based on user feedback."""

    def __init__(self, conn, config=None):
        self.conn = conn
        self.config = config or {}

    def adjust_search_weights(self, current_weights):
        """Analyze recent feedback to shift weights toward better-performing signals.

        For now, returns current_weights unchanged since we don't yet track
        signal provenance per chunk. Logs the analysis for observability.

        Args:
            current_weights: dict like {"bm25": 1.0, "vector": 1.0, "graph": 0.8}

        Returns:
            dict with (potentially adjusted) signal weights.
        """
        logger.info(
            "Weight analysis requested. Signal provenance not yet tracked; "
            "returning current weights: %s",
            current_weights,
        )
        return current_weights

    def strengthen_graph_edges(self, chunk_ids, factor=1.1):
        """Multiply weight by factor for relationships linked to chunk_ids. Cap at 5.0.

        Args:
            chunk_ids: list of chunk ID strings.
            factor: multiplicative factor (default 1.1).
        """
        if not chunk_ids:
            return

        # Build bind variable placeholders for the IN clause
        bind_names = [f"cid_{i}" for i in range(len(chunk_ids))]
        in_clause = ", ".join(f":{name}" for name in bind_names)

        sql = (
            f"UPDATE KG_RELATIONSHIPS "
            f"SET weight = LEAST(weight * :factor, 5.0) "
            f"WHERE chunk_id IN ({in_clause})"
        )

        params = {"factor": factor}
        for name, cid in zip(bind_names, chunk_ids):
            params[name] = cid

        with self.conn.cursor() as cursor:
            cursor.execute(sql, params)
        self.conn.commit()

        logger.info(
            "Strengthened edges for %d chunks by factor %.2f", len(chunk_ids), factor
        )

    def weaken_graph_edges(self, chunk_ids, factor=0.9):
        """Multiply weight by factor for relationships linked to chunk_ids. Floor at 0.1.

        Args:
            chunk_ids: list of chunk ID strings.
            factor: multiplicative factor (default 0.9).
        """
        if not chunk_ids:
            return

        bind_names = [f"cid_{i}" for i in range(len(chunk_ids))]
        in_clause = ", ".join(f":{name}" for name in bind_names)

        sql = (
            f"UPDATE KG_RELATIONSHIPS "
            f"SET weight = GREATEST(weight * :factor, 0.1) "
            f"WHERE chunk_id IN ({in_clause})"
        )

        params = {"factor": factor}
        for name, cid in zip(bind_names, chunk_ids):
            params[name] = cid

        with self.conn.cursor() as cursor:
            cursor.execute(sql, params)
        self.conn.commit()

        logger.info(
            "Weakened edges for %d chunks by factor %.2f", len(chunk_ids), factor
        )

    def get_quality_boost(self, quality_score, boost_range=None):
        """Calculate retrieval boost/penalty from a chunk's quality score.

        quality_score 0.5 = neutral (0.0 boost).
        1.0 = +boost_range. 0.0 = -boost_range. Linear interpolation.

        Args:
            quality_score: float between 0.0 and 1.0.
            boost_range: max boost magnitude (default from config or 0.15).

        Returns:
            float boost value.
        """
        if boost_range is None:
            boost_range = self.config.get("quality_boost_range", 0.15)
        return (quality_score - 0.5) * 2 * boost_range

    def should_recalibrate(self):
        """Check if total feedback count exceeds recalibrate_after threshold.

        Returns:
            True if recalibration is needed.
        """
        threshold = self.config.get("recalibrate_after", 50)
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM FEEDBACK")
            row = cursor.fetchone()
            count = row[0] if row else 0

        needs_recal = count >= threshold
        if needs_recal:
            logger.info(
                "Recalibration triggered: %d feedback entries (threshold %d)",
                count,
                threshold,
            )
        return needs_recal

    def process_feedback(self, chunk_ids, rating):
        """Convenience method to adjust graph edges and check recalibration.

        Args:
            chunk_ids: list of chunk ID strings involved in the feedback.
            rating: positive number strengthens edges, negative weakens them.
        """
        if rating > 0:
            self.strengthen_graph_edges(chunk_ids)
        elif rating < 0:
            self.weaken_graph_edges(chunk_ids)

        if self.should_recalibrate():
            logger.info("Recalibration threshold reached. Consider running weight adjustment.")
