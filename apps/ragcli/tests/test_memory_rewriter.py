"""Test query rewriter."""
from unittest.mock import MagicMock, patch
from ragcli.memory.rewriter import QueryRewriter

TEST_CONFIG = {
    "ollama": {"chat_model": "test", "endpoint": "http://localhost:11434", "timeout": 30}
}


def test_standalone_query_no_history():
    rewriter = QueryRewriter(config=TEST_CONFIG)
    result = rewriter.rewrite("What is RAG?", history=[], summary=None)
    assert result == "What is RAG?"


def test_standalone_detection_no_pronouns():
    rewriter = QueryRewriter(config=TEST_CONFIG)
    result = rewriter.rewrite(
        "How does PostgreSQL handle indexing?",
        history=[],
        summary=None,
    )
    assert result == "How does PostgreSQL handle indexing?"


@patch("ragcli.memory.rewriter.generate_response")
def test_rewrite_with_history(mock_gen):
    mock_gen.return_value = "What databases does the payment system use?"

    rewriter = QueryRewriter(config=TEST_CONFIG)
    history = [
        {"user_query": "How does the payment system work?", "response": "It processes transactions..."},
    ]
    result = rewriter.rewrite("What databases does it use?", history=history, summary=None)

    assert result == "What databases does the payment system use?"
    mock_gen.assert_called_once()


@patch("ragcli.memory.rewriter.generate_response")
def test_rewrite_failure_returns_original(mock_gen):
    mock_gen.side_effect = Exception("LLM failed")

    rewriter = QueryRewriter(config=TEST_CONFIG)
    history = [{"user_query": "prior", "response": "resp"}]
    result = rewriter.rewrite("What about it?", history=history, summary=None)

    assert result == "What about it?"
