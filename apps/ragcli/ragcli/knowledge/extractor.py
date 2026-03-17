"""Entity and relationship extraction from text using LLM."""

import json
import re
from typing import Dict, List

from ragcli.core.embedding import generate_response
from ragcli.utils.logger import get_logger

logger = get_logger(__name__)

MAX_INPUT_CHARS = 3000

EXTRACTION_PROMPT = """Extract entities and relationships from the following text.
Return ONLY valid JSON with this exact structure (no markdown, no explanation):

{{
  "entities": [
    {{"name": "EntityName", "type": "TYPE", "description": "Brief description"}}
  ],
  "relationships": [
    {{"source": "Entity1", "target": "Entity2", "type": "RELATIONSHIP_TYPE", "description": "Brief description"}}
  ]
}}

Entity types: PERSON, ORGANIZATION, TECHNOLOGY, CONCEPT, LOCATION, EVENT, PRODUCT, OTHER
Relationship types: USES, PART_OF, CREATED_BY, RELATED_TO, DEPENDS_ON, CONTAINS, LOCATED_IN, WORKS_FOR, OTHER

Rules:
- Extract only clearly stated entities and relationships.
- Each entity must have name, type, and optionally description.
- Each relationship must have source, target, type, and optionally description.
- Return empty lists if no entities or relationships are found.

Text:
{text}"""


def parse_extraction_response(raw: str) -> Dict[str, List]:
    """Parse LLM output into structured entities and relationships.

    Handles raw JSON, JSON wrapped in code blocks, partial JSON,
    and invalid responses gracefully.
    """
    empty_result = {"entities": [], "relationships": []}

    if not raw or not raw.strip():
        return empty_result

    # Try to extract JSON from code blocks first
    code_block_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
    json_str = code_block_match.group(1).strip() if code_block_match else raw.strip()

    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError:
        logger.debug("Failed to parse extraction response as JSON")
        return empty_result

    if not isinstance(parsed, dict):
        return empty_result

    # Validate and filter entities (require name + type)
    raw_entities = parsed.get("entities", [])
    valid_entities = []
    for entity in raw_entities:
        if isinstance(entity, dict) and entity.get("name") and entity.get("type"):
            valid_entities.append(entity)

    # Relationships don't need strict validation beyond being dicts
    raw_relationships = parsed.get("relationships", [])
    valid_relationships = []
    for rel in raw_relationships:
        if isinstance(rel, dict):
            valid_relationships.append(rel)

    return {"entities": valid_entities, "relationships": valid_relationships}


class EntityExtractor:
    """Extracts entities and relationships from text using an LLM."""

    def __init__(self, config: dict):
        self.config = config
        self.model = config["ollama"]["chat_model"]
        self.max_entities = config.get("knowledge_graph", {}).get(
            "max_entities_per_chunk", 10
        )

    def extract_from_text(self, text: str) -> Dict[str, List]:
        """Extract entities and relationships from a text chunk.

        Truncates input to MAX_INPUT_CHARS and limits output entities
        to max_entities_per_chunk from config.
        """
        truncated = text[:MAX_INPUT_CHARS]
        prompt = EXTRACTION_PROMPT.format(text=truncated)

        messages = [{"role": "user", "content": prompt}]

        try:
            raw_response = generate_response(
                messages=messages,
                model=self.model,
                config=self.config,
                stream=False,
            )
            result = parse_extraction_response(raw_response)
            # Limit entities to configured max
            result["entities"] = result["entities"][: self.max_entities]
            return result
        except Exception:
            logger.warning("Entity extraction failed", exc_info=True)
            return {"entities": [], "relationships": []}
