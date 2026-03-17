"""Evaluation run management: create, execute, and track eval runs."""

import json
from typing import Dict, List, Optional

from ragcli.utils.helpers import generate_uuid
from ragcli.utils.logger import get_logger

logger = get_logger(__name__)


class EvalRunner:
    """Manages evaluation runs against the EVAL_RUNS and EVAL_RESULTS tables."""

    def __init__(self, conn, config: dict):
        """Initialize with a database connection and config.

        Args:
            conn: An oracledb connection object.
            config: Application configuration dict.
        """
        self.conn = conn
        self.config = config

    def create_run(self, eval_mode: str) -> str:
        """Create a new evaluation run.

        Args:
            eval_mode: The evaluation mode (e.g. 'synthetic', 'manual', 'golden').

        Returns:
            The generated run_id.
        """
        run_id = generate_uuid()
        config_snapshot = json.dumps(self.config, default=str)

        sql = """
            INSERT INTO EVAL_RUNS (run_id, eval_mode, config_snapshot)
            VALUES (:run_id, :eval_mode, :config_snapshot)
        """
        with self.conn.cursor() as cursor:
            cursor.execute(sql, {
                "run_id": run_id,
                "eval_mode": eval_mode,
                "config_snapshot": config_snapshot,
            })
        self.conn.commit()
        logger.info(f"Created eval run {run_id} with mode '{eval_mode}'")
        return run_id

    def complete_run(self, run_id: str) -> None:
        """Calculate averages from results and mark run as completed.

        Args:
            run_id: The run to complete.
        """
        avg_sql = """
            SELECT
                AVG(faithfulness),
                AVG(relevance),
                AVG(context_precision),
                AVG(context_recall),
                COUNT(*)
            FROM EVAL_RESULTS
            WHERE run_id = :run_id
        """
        update_sql = """
            UPDATE EVAL_RUNS
            SET completed_at = SYSTIMESTAMP,
                avg_faithfulness = :avg_faithfulness,
                avg_relevance = :avg_relevance,
                avg_context_precision = :avg_context_precision,
                avg_context_recall = :avg_context_recall,
                total_pairs = :total_pairs
            WHERE run_id = :run_id
        """
        with self.conn.cursor() as cursor:
            cursor.execute(avg_sql, {"run_id": run_id})
            row = cursor.fetchone()
            avg_faith, avg_rel, avg_cp, avg_cr, total = row

            cursor.execute(update_sql, {
                "avg_faithfulness": avg_faith,
                "avg_relevance": avg_rel,
                "avg_context_precision": avg_cp,
                "avg_context_recall": avg_cr,
                "total_pairs": total,
                "run_id": run_id,
            })
        self.conn.commit()
        logger.info(f"Completed eval run {run_id}: {total} pairs evaluated")

    def run_synthetic(self, document_id: Optional[str] = None) -> str:
        """Create a synthetic evaluation run.

        Creates the run record. Actual Q&A pair generation and scoring
        will be wired in Phase 9 when the full RAG pipeline is available.

        Args:
            document_id: Optional document ID to scope evaluation to.

        Returns:
            The created run_id.
        """
        run_id = self.create_run("synthetic")
        logger.info(
            f"Synthetic eval run {run_id} created"
            + (f" for document {document_id}" if document_id else " for all documents")
        )
        # Phase 9 will wire in: generate Q&A pairs, run RAG, score results
        self.complete_run(run_id)
        return run_id

    def get_run(self, run_id: str) -> Optional[Dict]:
        """Fetch a single eval run by ID.

        Args:
            run_id: The run to fetch.

        Returns:
            Dict with run fields, or None if not found.
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
            return _row_to_run_dict(row)

    def list_runs(self, limit: int = 20) -> List[Dict]:
        """List recent eval runs, newest first.

        Args:
            limit: Maximum number of runs to return.

        Returns:
            List of run dicts.
        """
        sql = """
            SELECT run_id, eval_mode, started_at, completed_at,
                   avg_faithfulness, avg_relevance, avg_context_precision,
                   avg_context_recall, total_pairs, config_snapshot
            FROM EVAL_RUNS
            ORDER BY started_at DESC
            FETCH FIRST :limit ROWS ONLY
        """
        with self.conn.cursor() as cursor:
            cursor.execute(sql, {"limit": limit})
            rows = cursor.fetchall()
            return [_row_to_run_dict(row) for row in rows]

    def get_run_results(self, run_id: str) -> List[Dict]:
        """Fetch all results for a given run.

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
        with self.conn.cursor() as cursor:
            cursor.execute(sql, {"run_id": run_id})
            rows = cursor.fetchall()
            return [_row_to_result_dict(row) for row in rows]


def _row_to_run_dict(row) -> Dict:
    """Convert a DB row tuple to a run dict."""
    return {
        "run_id": row[0],
        "eval_mode": row[1],
        "started_at": row[2],
        "completed_at": row[3],
        "avg_faithfulness": row[4],
        "avg_relevance": row[5],
        "avg_context_precision": row[6],
        "avg_context_recall": row[7],
        "total_pairs": row[8],
        "config_snapshot": row[9],
    }


def _row_to_result_dict(row) -> Dict:
    """Convert a DB row tuple to a result dict."""
    return {
        "result_id": row[0],
        "run_id": row[1],
        "document_id": row[2],
        "question": row[3],
        "expected_answer": row[4],
        "actual_answer": row[5],
        "faithfulness": row[6],
        "relevance": row[7],
        "context_precision": row[8],
        "context_recall": row[9],
        "chunk_ids_json": row[10],
        "duration_ms": row[11],
        "created_at": row[12],
    }
