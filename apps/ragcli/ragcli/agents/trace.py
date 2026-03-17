"""Reasoning trace storage and retrieval."""

import time
import json
from typing import Dict, Any, List, Optional
from ..utils.helpers import generate_uuid
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ReasoningTrace:
    def __init__(self, query: str, session_id: Optional[str] = None):
        self.trace_id = generate_uuid()
        self.query = query
        self.session_id = session_id
        self.steps = []
        self._step_order = 0

    def add_step(self, agent_role: str, input_data: Any, output_data: Any, reasoning: str = ""):
        self._step_order += 1
        self.steps.append({
            "step_id": generate_uuid(),
            "agent_role": agent_role,
            "input_data": input_data,
            "output_data": output_data,
            "reasoning": reasoning,
            "step_order": self._step_order,
            "start_time": time.perf_counter(),
        })

    def finalize_step(self, token_count: int = 0):
        if self.steps:
            step = self.steps[-1]
            step["duration_ms"] = (time.perf_counter() - step.pop("start_time", time.perf_counter())) * 1000
            step["token_count"] = token_count

    def persist(self, conn, query_id: Optional[str] = None):
        trace_sql = """
        INSERT INTO AGENT_TRACES (trace_id, query_id, session_id)
        VALUES (:v_trace, :v_query, :v_session)
        """
        with conn.cursor() as cursor:
            cursor.execute(trace_sql, {
                "v_trace": self.trace_id,
                "v_query": query_id,
                "v_session": self.session_id,
            })

            step_sql = """
            INSERT INTO TRACE_STEPS (
                step_id, trace_id, agent_role, input_data, output_data,
                reasoning, duration_ms, token_count, step_order
            ) VALUES (
                :v_step, :v_trace, :v_role, :v_input, :v_output,
                :v_reasoning, :v_duration, :v_tokens, :v_order
            )
            """
            for step in self.steps:
                cursor.execute(step_sql, {
                    "v_step": step["step_id"],
                    "v_trace": self.trace_id,
                    "v_role": step["agent_role"],
                    "v_input": json.dumps(step["input_data"], default=str)[:4000],
                    "v_output": json.dumps(step["output_data"], default=str)[:4000],
                    "v_reasoning": step.get("reasoning", ""),
                    "v_duration": step.get("duration_ms", 0),
                    "v_tokens": step.get("token_count", 0),
                    "v_order": step["step_order"],
                })
        conn.commit()

    @staticmethod
    def load(conn, trace_id: str) -> Optional[Dict[str, Any]]:
        sql = """
        SELECT t.trace_id, t.query_id, t.session_id, t.created_at,
               s.step_id, s.agent_role, s.input_data, s.output_data,
               s.reasoning, s.duration_ms, s.token_count, s.step_order
        FROM AGENT_TRACES t
        JOIN TRACE_STEPS s ON t.trace_id = s.trace_id
        WHERE t.trace_id = :v_id
        ORDER BY s.step_order
        """
        with conn.cursor() as cursor:
            cursor.execute(sql, {"v_id": trace_id})
            rows = cursor.fetchall()
            if not rows:
                return None
            trace = {
                "trace_id": rows[0][0],
                "query_id": rows[0][1],
                "session_id": rows[0][2],
                "created_at": rows[0][3],
                "steps": [],
            }
            for row in rows:
                trace["steps"].append({
                    "step_id": row[4],
                    "agent_role": row[5],
                    "input_data": row[6],
                    "output_data": row[7],
                    "reasoning": row[8],
                    "duration_ms": row[9],
                    "token_count": row[10],
                    "step_order": row[11],
                })
            return trace
