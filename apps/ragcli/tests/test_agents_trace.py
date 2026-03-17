"""Test reasoning trace."""
import time
from ragcli.agents.trace import ReasoningTrace


def test_trace_creation():
    trace = ReasoningTrace("test query")
    assert trace.trace_id is not None
    assert len(trace.trace_id) == 36
    assert trace.query == "test query"
    assert len(trace.steps) == 0


def test_add_steps():
    trace = ReasoningTrace("test query")
    trace.add_step("planner", {"query": "test"}, {"sub_queries": ["a", "b"]}, "decomposed into 2")
    trace.finalize_step(token_count=50)
    trace.add_step("researcher", {"sub_queries": ["a"]}, {"chunks": []}, "searched")
    trace.finalize_step(token_count=100)

    assert len(trace.steps) == 2
    assert trace.steps[0]["agent_role"] == "planner"
    assert trace.steps[0]["step_order"] == 1
    assert trace.steps[1]["step_order"] == 2
    assert trace.steps[0]["token_count"] == 50
    assert trace.steps[1]["token_count"] == 100


def test_step_duration():
    trace = ReasoningTrace("test query")
    trace.add_step("planner", {}, {}, "")
    time.sleep(0.01)  # Small delay
    trace.finalize_step()
    assert trace.steps[0]["duration_ms"] > 0


def test_trace_with_session():
    trace = ReasoningTrace("test", session_id="sess-123")
    assert trace.session_id == "sess-123"
