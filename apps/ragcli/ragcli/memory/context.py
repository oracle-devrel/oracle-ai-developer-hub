"""Rolling context summarization for session memory."""

from typing import List, Dict, Optional
from ..core.embedding import generate_response
from ..utils.logger import get_logger

logger = get_logger(__name__)

SUMMARIZE_PROMPT = """Summarize this conversation so far in 2-3 sentences. Focus on: topics discussed, key facts established, questions answered.

{previous_summary}Conversation:
{turns}

Summary:"""


class ContextManager:
    def __init__(self, config: dict):
        self.config = config
        self.model = config["ollama"]["chat_model"]
        self.summarize_every = config.get("memory", {}).get("summarize_every", 5)

    def should_summarize(self, turn_count: int) -> bool:
        return turn_count > 0 and turn_count % self.summarize_every == 0

    def summarize(self, turns: List[Dict], existing_summary: Optional[str] = None) -> str:
        previous = ""
        if existing_summary:
            previous = f"Previous summary: {existing_summary}\n\n"

        turns_text = "\n".join(
            f"User: {t['user_query']}\nAssistant: {(t.get('response') or '')[:300]}"
            for t in turns
        )

        prompt = SUMMARIZE_PROMPT.format(previous_summary=previous, turns=turns_text)
        messages = [{"role": "user", "content": prompt}]

        try:
            result = generate_response(messages, self.model, self.config, stream=False)
            return result.strip() if result else existing_summary or ""
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return existing_summary or ""
