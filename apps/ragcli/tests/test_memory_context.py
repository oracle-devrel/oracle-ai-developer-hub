"""Test context manager for rolling summarization."""
from unittest.mock import patch
from ragcli.memory.context import ContextManager

TEST_CONFIG = {
    "ollama": {"chat_model": "test", "endpoint": "http://localhost:11434", "timeout": 30},
    "memory": {"summarize_every": 5},
}


def test_should_not_summarize_below_threshold():
    manager = ContextManager(config=TEST_CONFIG)
    assert manager.should_summarize(turn_count=3) is False


def test_should_summarize_at_threshold():
    manager = ContextManager(config=TEST_CONFIG)
    assert manager.should_summarize(turn_count=5) is True


def test_should_summarize_at_multiple():
    manager = ContextManager(config=TEST_CONFIG)
    assert manager.should_summarize(turn_count=10) is True


def test_should_not_summarize_at_zero():
    manager = ContextManager(config=TEST_CONFIG)
    assert manager.should_summarize(turn_count=0) is False


@patch("ragcli.memory.context.generate_response")
def test_summarize_turns(mock_gen):
    mock_gen.return_value = "User discussed payment systems and databases."

    manager = ContextManager(config=TEST_CONFIG)
    turns = [
        {"user_query": "How does payment work?", "response": "It uses Stripe."},
        {"user_query": "What DB?", "response": "PostgreSQL."},
    ]
    summary = manager.summarize(turns, existing_summary=None)
    assert summary == "User discussed payment systems and databases."
    mock_gen.assert_called_once()


@patch("ragcli.memory.context.generate_response")
def test_summarize_failure_returns_existing(mock_gen):
    mock_gen.side_effect = Exception("LLM failed")

    manager = ContextManager(config=TEST_CONFIG)
    summary = manager.summarize([], existing_summary="old summary")
    assert summary == "old summary"
