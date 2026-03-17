"""Test agent orchestrator."""
from unittest.mock import patch, MagicMock
from ragcli.agents.orchestrator import AgentOrchestrator

TEST_CONFIG = {
    "ollama": {"chat_model": "test", "endpoint": "http://localhost:11434", "timeout": 30},
    "search": {"strategy": "hybrid"},
}


@patch("ragcli.agents.orchestrator.Synthesizer")
@patch("ragcli.agents.orchestrator.Reasoner")
@patch("ragcli.agents.orchestrator.Researcher")
@patch("ragcli.agents.orchestrator.Planner")
def test_full_pipeline(MockPlanner, MockResearcher, MockReasoner, MockSynthesizer):
    MockPlanner.return_value.run.return_value = {"sub_queries": ["What is X?"], "strategy": "direct"}
    MockResearcher.return_value.run.return_value = {"evidence": [{"chunk_id": "c1", "text": "X is..."}], "graph_paths": []}
    MockReasoner.return_value.run.return_value = {"analysis": "X is a concept", "citations": ["c1"], "contradictions": []}
    MockSynthesizer.return_value.run.return_value = {"answer": "X is a concept.", "confidence": 0.9, "sources": ["doc1"]}

    search_fn = MagicMock(return_value=[{"chunk_id": "c1", "text": "X is...", "similarity_score": 0.9, "document_id": "doc1"}])

    orch = AgentOrchestrator(TEST_CONFIG)
    result = orch.run("What is X?", search_func=search_fn)

    assert result["answer"] == "X is a concept."
    assert result["confidence"] == 0.9
    assert result["trace_id"] is not None


@patch("ragcli.agents.orchestrator.Synthesizer")
@patch("ragcli.agents.orchestrator.Reasoner")
@patch("ragcli.agents.orchestrator.Researcher")
@patch("ragcli.agents.orchestrator.Planner")
def test_fallback_on_failure(MockPlanner, MockResearcher, MockReasoner, MockSynthesizer):
    MockPlanner.return_value.run.side_effect = Exception("planner died")

    search_fn = MagicMock(return_value=[{"chunk_id": "c1", "text": "fallback text", "similarity_score": 0.8, "document_id": "d1"}])

    orch = AgentOrchestrator(TEST_CONFIG)
    result = orch.run("What is X?", search_func=search_fn)

    # Should fall back to simple search + synthesize
    assert "answer" in result
    assert result["trace_id"] is not None


def test_orchestrator_no_search_func():
    orch = AgentOrchestrator(TEST_CONFIG)
    result = orch.run("What is X?")
    # Without search func, should return gracefully
    assert "answer" in result
