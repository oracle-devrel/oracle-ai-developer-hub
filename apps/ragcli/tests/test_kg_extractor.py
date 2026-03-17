"""Test knowledge graph entity extraction."""
from unittest.mock import patch
from ragcli.knowledge.extractor import EntityExtractor, parse_extraction_response

TEST_CONFIG = {
    "ollama": {"chat_model": "test", "endpoint": "http://localhost:11434", "timeout": 30},
    "knowledge_graph": {"max_entities_per_chunk": 10},
}


def test_parse_valid_json():
    raw = '{"entities": [{"name": "Python", "type": "TECHNOLOGY", "description": "A programming language"}], "relationships": [{"source": "Python", "target": "Django", "type": "USES", "description": "Django is built with Python"}]}'
    result = parse_extraction_response(raw)
    assert len(result["entities"]) == 1
    assert result["entities"][0]["name"] == "Python"
    assert len(result["relationships"]) == 1


def test_parse_invalid_json():
    result = parse_extraction_response("not json at all")
    assert result["entities"] == []
    assert result["relationships"] == []


def test_parse_partial_json():
    raw = '{"entities": [{"name": "X", "type": "CONCEPT"}]}'
    result = parse_extraction_response(raw)
    assert len(result["entities"]) == 1
    assert result["relationships"] == []


def test_parse_json_in_code_block():
    raw = '```json\n{"entities": [{"name": "Y", "type": "ORG", "description": "test"}], "relationships": []}\n```'
    result = parse_extraction_response(raw)
    assert len(result["entities"]) == 1
    assert result["entities"][0]["name"] == "Y"


def test_parse_missing_required_fields():
    raw = '{"entities": [{"description": "no name or type"}], "relationships": []}'
    result = parse_extraction_response(raw)
    assert result["entities"] == []


@patch("ragcli.knowledge.extractor.generate_response")
def test_extract_from_text(mock_gen):
    mock_gen.return_value = '{"entities": [{"name": "Oracle", "type": "TECHNOLOGY", "description": "Database"}], "relationships": []}'
    extractor = EntityExtractor(TEST_CONFIG)
    result = extractor.extract_from_text("Oracle Database is used for vector search.")
    assert len(result["entities"]) == 1
    assert result["entities"][0]["name"] == "Oracle"


@patch("ragcli.knowledge.extractor.generate_response")
def test_extract_failure_returns_empty(mock_gen):
    mock_gen.side_effect = Exception("LLM failed")
    extractor = EntityExtractor(TEST_CONFIG)
    result = extractor.extract_from_text("some text")
    assert result["entities"] == []
    assert result["relationships"] == []
