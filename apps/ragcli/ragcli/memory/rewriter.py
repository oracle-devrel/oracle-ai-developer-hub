"""Query rewriting with conversation context."""

from typing import List, Dict, Any, Optional
from ..core.embedding import generate_response
from ..utils.logger import get_logger

logger = get_logger(__name__)

REWRITE_PROMPT = """Given this conversation history and a follow-up question, rewrite the follow-up as a standalone question that captures all necessary context.
If the follow-up is already standalone, return it unchanged. Return ONLY the rewritten question, nothing else.

History:
{history}

Follow-up: {query}
Standalone question:"""


class QueryRewriter:
    def __init__(self, config: dict):
        self.config = config
        self.model = config["ollama"]["chat_model"]

    def _is_likely_standalone(self, query: str) -> bool:
        referential_words = {"it", "its", "they", "them", "their", "this", "that", "those", "these"}
        lower = query.lower()
        return not any(f" {w} " in f" {lower} " for w in referential_words)

    def _format_history(self, history: List[Dict], summary: Optional[str]) -> str:
        parts = []
        if summary:
            parts.append(f"Earlier context: {summary}")
        for turn in history:
            parts.append(f"User: {turn['user_query']}")
            resp = turn.get("response", "")
            if resp and len(resp) > 400:
                resp = resp[:400] + "..."
            parts.append(f"Assistant: {resp}")
        return "\n".join(parts)

    def rewrite(self, query: str, history: List[Dict], summary: Optional[str]) -> str:
        if not history and not summary:
            return query

        if self._is_likely_standalone(query) and not history:
            return query

        history_text = self._format_history(history, summary)
        prompt = REWRITE_PROMPT.format(history=history_text, query=query)

        messages = [{"role": "user", "content": prompt}]
        try:
            result = generate_response(messages, self.model, self.config, stream=False)
            return result.strip() if result else query
        except Exception as e:
            logger.error(f"Query rewrite failed, using original: {e}")
            return query
