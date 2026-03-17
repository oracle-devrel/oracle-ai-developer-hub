"""Evaluation report generation and run comparison."""

from typing import Dict, List, Optional

from ragcli.utils.logger import get_logger

logger = get_logger(__name__)

# Column order returned by the EVAL_RUNS SELECT
_RUN_COLUMNS = [
    "run_id", "eval_mode", "started_at", "completed_at",
    "avg_faithfulness", "avg_relevance", "avg_context_precision",
    "avg_context_recall", "total_pairs", "config_snapshot",
]


class EvalReporter:
    """Generate and format evaluation reports."""

    def __init__(self, conn):
        """Initialize with a database connection.

        Args:
            conn: An oracledb connection object.
        """
        self.conn = conn

    def _fetch_run(self, run_id: str) -> Optional[Dict]:
        """Fetch a single run row as a dict.

        Args:
            run_id: The run to fetch.

        Returns:
            Dict with run fields, or None.
        """
        sql = """
            SELECT run_id, eval_mode, started_at, completed_at,
                   avg_faithfulness, avg_relevance, avg_context_precision,
                   avg_context_recall, total_pairs, config_snapshot
            FROM EVAL_RUNS
            WHERE run_id = :run_id
        """
        with self.conn.cursor() as cursor:
            cursor.execute(sql, {"run_id": run_id})
            row = cursor.fetchone()
            if row is None:
                return None
            return dict(zip(_RUN_COLUMNS, row))

    def _fetch_results(self, run_id: str) -> List[Dict]:
        """Fetch all results for a run.

        Args:
            run_id: The run to get results for.

        Returns:
            List of result dicts.
        """
        sql = """
            SELECT result_id, run_id, document_id, question, expected_answer,
                   actual_answer, faithfulness, relevance, context_precision,
                   context_recall, chunk_ids_json, duration_ms, created_at
            FROM EVAL_RESULTS
            WHERE run_id = :run_id
            ORDER BY created_at
        """
        columns = [
            "result_id", "run_id", "document_id", "question", "expected_answer",
            "actual_answer", "faithfulness", "relevance", "context_precision",
            "context_recall", "chunk_ids_json", "duration_ms", "created_at",
        ]
        with self.conn.cursor() as cursor:
            cursor.execute(sql, {"run_id": run_id})
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]

    def generate_report(self, run_id: str) -> Optional[Dict]:
        """Generate a full report for an eval run.

        Args:
            run_id: The run to report on.

        Returns:
            Dict with summary stats and per-result details, or None if run not found.
        """
        run = self._fetch_run(run_id)
        if run is None:
            logger.warning(f"Eval run {run_id} not found")
            return None

        results = self._fetch_results(run_id)

        report = {
            "run_id": run["run_id"],
            "eval_mode": run["eval_mode"],
            "started_at": run["started_at"],
            "completed_at": run["completed_at"],
            "avg_faithfulness": run["avg_faithfulness"],
            "avg_relevance": run["avg_relevance"],
            "avg_context_precision": run["avg_context_precision"],
            "avg_context_recall": run["avg_context_recall"],
            "total_pairs": run["total_pairs"],
            "results": results,
        }
        return report

    def compare_runs(self, run_id_1: str, run_id_2: str) -> Optional[Dict]:
        """Compare two eval runs and show metric deltas.

        Args:
            run_id_1: The baseline run.
            run_id_2: The comparison run.

        Returns:
            Dict with both runs' stats and a deltas sub-dict, or None on error.
        """
        run1 = self._fetch_run(run_id_1)
        run2 = self._fetch_run(run_id_2)

        if run1 is None or run2 is None:
            missing = run_id_1 if run1 is None else run_id_2
            logger.warning(f"Eval run {missing} not found for comparison")
            return None

        metric_keys = [
            "avg_faithfulness", "avg_relevance",
            "avg_context_precision", "avg_context_recall",
        ]
        # Strip the "avg_" prefix for the delta keys
        deltas = {}
        for key in metric_keys:
            v1 = run1.get(key) or 0.0
            v2 = run2.get(key) or 0.0
            short_key = key.replace("avg_", "")
            deltas[short_key] = round(v2 - v1, 6)

        return {
            "run_1": run1,
            "run_2": run2,
            "deltas": deltas,
        }

    def format_report_text(self, report: Dict) -> str:
        """Format a report dict as human-readable text for CLI output.

        Args:
            report: A report dict as returned by generate_report().

        Returns:
            Formatted multi-line string.
        """
        lines = [
            "=" * 60,
            f"  Evaluation Report: {report.get('run_id', 'N/A')}",
            "=" * 60,
            f"  Mode:               {report.get('eval_mode', 'N/A')}",
            f"  Total pairs:        {report.get('total_pairs', 0)}",
            f"  Started:            {report.get('started_at', 'N/A')}",
            f"  Completed:          {report.get('completed_at', 'N/A')}",
            "-" * 60,
            "  Metric Averages:",
            f"    Faithfulness:       {report.get('avg_faithfulness', 'N/A')}",
            f"    Relevance:          {report.get('avg_relevance', 'N/A')}",
            f"    Context Precision:  {report.get('avg_context_precision', 'N/A')}",
            f"    Context Recall:     {report.get('avg_context_recall', 'N/A')}",
            "-" * 60,
        ]

        results = report.get("results", [])
        if results:
            lines.append(f"  Per-Result Details ({len(results)} results):")
            lines.append("-" * 60)
            for i, r in enumerate(results, 1):
                q = str(r.get("question", ""))[:80]
                lines.append(f"  [{i}] Q: {q}")
                lines.append(
                    f"      F={r.get('faithfulness', 'N/A')}  "
                    f"R={r.get('relevance', 'N/A')}  "
                    f"CP={r.get('context_precision', 'N/A')}  "
                    f"CR={r.get('context_recall', 'N/A')}  "
                    f"({r.get('duration_ms', 'N/A')}ms)"
                )
        else:
            lines.append("  No individual results recorded.")

        lines.append("=" * 60)
        return "\n".join(lines)
