"""Tests for synthetic Q&A pair generation."""
import json
from unittest.mock import MagicMock, patch, call

from ragcli.eval.generator import SyntheticQAGenerator


def _make_mock_conn():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_conn, mock_cursor


def _make_config(**overrides):
    config = {
        "ollama": {
            "chat_model": "gemma3:270m",
            "endpoint": "http://localhost:11434",
            "timeout": 60,
        },
        "evaluation": {
            "pairs_per_chunk": 2,
            "max_chunks_per_doc": 20,
        },
    }
    config.update(overrides)
    return config


# --- _parse_qa_response tests ---

def test_parse_valid_json():
    mock_conn, _ = _make_mock_conn()
    gen = SyntheticQAGenerator(mock_conn, _make_config())

    response = json.dumps({
        "pairs": [
            {"question": "What is RAG?", "answer": "Retrieval-Augmented Generation"},
            {"question": "What DB?", "answer": "Oracle 26ai"},
        ]
    })
    result = gen._parse_qa_response(response)
    assert len(result) == 2
    assert result[0]["question"] == "What is RAG?"
    assert result[1]["answer"] == "Oracle 26ai"


def test_parse_json_in_code_block():
    mock_conn, _ = _make_mock_conn()
    gen = SyntheticQAGenerator(mock_conn, _make_config())

    response = '```json\n{"pairs": [{"question": "Q1", "answer": "A1"}]}\n```'
    result = gen._parse_qa_response(response)
    assert len(result) == 1
    assert result[0]["question"] == "Q1"
    assert result[0]["answer"] == "A1"


def test_parse_invalid_json():
    mock_conn, _ = _make_mock_conn()
    gen = SyntheticQAGenerator(mock_conn, _make_config())

    result = gen._parse_qa_response("This is not JSON at all {broken")
    assert result == []


def test_parse_missing_fields():
    mock_conn, _ = _make_mock_conn()
    gen = SyntheticQAGenerator(mock_conn, _make_config())

    response = json.dumps({
        "pairs": [
            {"question": "Valid Q", "answer": "Valid A"},
            {"question": "Missing answer"},
            {"answer": "Missing question"},
            {"question": "Also valid", "answer": "Yes"},
        ]
    })
    result = gen._parse_qa_response(response)
    assert len(result) == 2
    assert result[0]["question"] == "Valid Q"
    assert result[1]["question"] == "Also valid"


# --- generate_for_chunk tests ---

@patch("ragcli.eval.generator.generate_response")
def test_generate_for_chunk_truncates(mock_gen_response):
    mock_conn, _ = _make_mock_conn()
    gen = SyntheticQAGenerator(mock_conn, _make_config())

    long_text = "Z" * 5000
    mock_gen_response.return_value = json.dumps({
        "pairs": [{"question": "Q", "answer": "A"}]
    })

    gen.generate_for_chunk(long_text, n=2)

    # Verify generate_response was called
    mock_gen_response.assert_called_once()
    call_args = mock_gen_response.call_args
    messages = call_args[0][0]
    # The text embedded in the prompt should be truncated to 3000 chars
    user_content = messages[0]["content"]
    # 'Z' doesn't appear in the prompt template, so count should be exactly 3000
    assert user_content.count("Z") == 3000


# --- store_qa_pair tests ---

@patch("ragcli.eval.generator.generate_uuid", return_value="test-uuid-1234")
def test_store_qa_pair(mock_uuid):
    mock_conn, mock_cursor = _make_mock_conn()
    gen = SyntheticQAGenerator(mock_conn, _make_config())

    gen.store_qa_pair(
        run_id="run-001",
        document_id="doc-001",
        chunk_id="chunk-001",
        question="What is RAG?",
        answer="Retrieval-Augmented Generation",
    )

    # Verify INSERT was called
    assert mock_cursor.execute.call_count == 1
    sql = mock_cursor.execute.call_args[0][0]
    params = mock_cursor.execute.call_args[0][1]

    assert "INSERT INTO EVAL_RESULTS" in sql
    assert params["result_id"] == "test-uuid-1234"
    assert params["run_id"] == "run-001"
    assert params["document_id"] == "doc-001"
    assert params["question"] == "What is RAG?"
    assert params["expected_answer"] == "Retrieval-Augmented Generation"

    # Verify commit was called
    mock_conn.commit.assert_called_once()
