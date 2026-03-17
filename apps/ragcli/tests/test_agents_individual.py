"""Test individual agents."""
from unittest.mock import patch, MagicMock
from ragcli.agents.planner import Planner
from ragcli.agents.researcher import Researcher
from ragcli.agents.reasoner import Reasoner
from ragcli.agents.synthesizer import Synthesizer

TEST_CONFIG = {
    "ollama": {"chat_model": "test", "endpoint": "http://localhost:11434", "timeout": 30}
}


@patch("ragcli.agents.planner.generate_response")
def test_planner_decompose(mock_gen):
    mock_gen.return_value = '{"sub_queries": ["What is X?", "How does X work?"], "strategy": "parallel"}'
    planner = Planner(TEST_CONFIG)
    result = planner.run("Tell me about X")
    assert len(result["sub_queries"]) == 2
    assert result["strategy"] == "parallel"


@patch("ragcli.agents.planner.generate_response")
def test_planner_failure_fallback(mock_gen):
    mock_gen.side_effect = Exception("LLM failed")
    planner = Planner(TEST_CONFIG)
    result = planner.run("Tell me about X")
    assert result["sub_queries"] == ["Tell me about X"]
    assert result["strategy"] == "direct"


def test_researcher_calls_search():
    search_fn = MagicMock(return_value=[
        {"chunk_id": "c1", "text": "evidence text", "similarity_score": 0.9, "document_id": "d1"}
    ])
    researcher = Researcher(TEST_CONFIG)
    result = researcher.run("What is X?", search_fn)
    assert len(result["evidence"]) == 1
    search_fn.assert_called_once_with("What is X?")


def test_researcher_search_failure():
    search_fn = MagicMock(side_effect=Exception("search failed"))
    researcher = Researcher(TEST_CONFIG)
    result = researcher.run("What is X?", search_fn)
    assert result["evidence"] == []


@patch("ragcli.agents.reasoner.generate_response")
def test_reasoner_analyze(mock_gen):
    mock_gen.return_value = '{"analysis": "X is a concept that...", "citations": ["c1"], "contradictions": []}'
    reasoner = Reasoner(TEST_CONFIG)
    evidence = [{"chunk_id": "c1", "text": "X is defined as..."}]
    result = reasoner.run("What is X?", evidence)
    assert "analysis" in result
    assert len(result["analysis"]) > 0


@patch("ragcli.agents.synthesizer.generate_response")
def test_synthesizer_compose(mock_gen):
    mock_gen.return_value = '{"answer": "X is a concept...", "confidence": 0.85, "sources": ["doc1"]}'
    synth = Synthesizer(TEST_CONFIG)
    result = synth.run("What is X?", "X is a concept that...", [{"document_id": "doc1"}])
    assert "answer" in result
    assert result["confidence"] == 0.85
