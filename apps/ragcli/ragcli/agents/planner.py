"""Planner agent: decomposes queries into sub-questions."""

import json
import re
from typing import Dict, List

from ragcli.core.embedding import generate_response
from ragcli.utils.logger import get_logger

logger = get_logger(__name__)


class Planner:
    """Decomposes a user query into 1-5 sub-questions with a strategy."""

    def __init__(self, config: dict):
        self.config = config
        self.model = config["ollama"]["chat_model"]

    def run(self, query: str, session_context: str = "") -> Dict:
        """Decompose query into sub-queries and a strategy.

        Returns:
            Dict with keys: sub_queries (List[str]), strategy (str)
        """
        try:
            context_block = ""
            if session_context:
                context_block = f"\nSession context:\n{session_context}\n"

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a query planner. Decompose the user's question into 1-5 "
                        "focused sub-questions that, when answered, fully address the original query. "
                        "Respond ONLY with valid JSON in this exact format:\n"
                        '{"sub_queries": ["question1", "question2"], "strategy": "parallel"}\n'
                        "strategy should be 'parallel' if sub-questions are independent, "
                        "'sequential' if they depend on each other, or 'direct' for simple queries."
                    ),
                },
                {
                    "role": "user",
                    "content": f"{context_block}Query: {query}",
                },
            ]

            raw = generate_response(messages, self.model, self.config, stream=False)
            return self._parse_response(raw, query)

        except Exception as e:
            logger.warning(f"Planner failed, falling back to direct: {e}")
            return {"sub_queries": [query], "strategy": "direct"}

    def _parse_response(self, raw: str, original_query: str) -> Dict:
        """Parse LLM JSON output, with fallback."""
        try:
            result = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            # Try extracting JSON from surrounding text
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                try:
                    result = json.loads(match.group())
                except (json.JSONDecodeError, TypeError):
                    return {"sub_queries": [original_query], "strategy": "direct"}
            else:
                return {"sub_queries": [original_query], "strategy": "direct"}

        # Validate structure
        if not isinstance(result.get("sub_queries"), list) or not result["sub_queries"]:
            result["sub_queries"] = [original_query]
        if result.get("strategy") not in ("parallel", "sequential", "direct"):
            result["strategy"] = "direct"

        return {
            "sub_queries": result["sub_queries"],
            "strategy": result["strategy"],
        }
