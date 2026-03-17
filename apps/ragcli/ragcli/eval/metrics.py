"""LLM-judged evaluation metrics for RAG quality assessment."""

import re
from typing import Dict, List

from ragcli.core.embedding import generate_response
from ragcli.utils.logger import get_logger

logger = get_logger(__name__)


class EvalMetrics:
    """Four core LLM-judged metrics for RAG evaluation.

    Each metric returns a float between 0.0 and 1.0.
    """

    FAITHFULNESS_PROMPT = """Score how faithfully the answer reflects ONLY the provided context.
Score 0.0 if the answer contains claims not in the context.
Score 1.0 if every claim is supported by the context.
Return ONLY a number between 0.0 and 1.0.

Context: {context}
Answer: {answer}

Score:"""

    RELEVANCE_PROMPT = """Score how well the answer addresses the question.
Score 0.0 if the answer is completely irrelevant.
Score 1.0 if the answer fully addresses the question.
Return ONLY a number between 0.0 and 1.0.

Question: {question}
Answer: {answer}

Score:"""

    CONTEXT_PRECISION_PROMPT = """Score what fraction of the retrieved context chunks are actually relevant to answering the question.
Score 0.0 if none are relevant.
Score 1.0 if all are relevant.
Return ONLY a number between 0.0 and 1.0.

Question: {question}
Context chunks: {context}

Score:"""

    CONTEXT_RECALL_PROMPT = """Score whether the retrieved context contains enough information to produce the expected answer.
Score 0.0 if the context has none of the needed information.
Score 1.0 if the context fully covers the expected answer.
Return ONLY a number between 0.0 and 1.0.

Expected answer: {expected}
Context: {context}

Score:"""

    def __init__(self, config: dict):
        """Initialize with config containing ollama model and endpoint.

        Args:
            config: Configuration dict with ollama.model and ollama.base_url keys.
        """
        self.config = config
        self.model = config.get("ollama", {}).get("model", "gemma3:270m")

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM with a scoring prompt and return the raw response."""
        messages = [{"role": "user", "content": prompt}]
        try:
            response = "".join(generate_response(
                messages=messages,
                model=self.model,
                config=self.config,
                stream=False,
            ))
            return response.strip()
        except Exception as e:
            logger.error(f"LLM call failed during eval scoring: {e}")
            return ""

    def _parse_score(self, response: str) -> float:
        """Extract a float score from the LLM response.

        Uses regex to find the first number. Clamps result to [0.0, 1.0].
        Returns 0.0 if no valid number is found.
        """
        match = re.search(r"-?\d+\.?\d*", response)
        if match is None:
            return 0.0
        value = float(match.group())
        return max(0.0, min(1.0, value))

    def score_faithfulness(self, context: str, answer: str) -> float:
        """Score how faithfully the answer reflects the provided context.

        Args:
            context: The retrieved context chunks.
            answer: The generated answer.

        Returns:
            Float between 0.0 and 1.0.
        """
        prompt = self.FAITHFULNESS_PROMPT.format(context=context, answer=answer)
        response = self._call_llm(prompt)
        return self._parse_score(response)

    def score_relevance(self, question: str, answer: str) -> float:
        """Score how well the answer addresses the question.

        Args:
            question: The user's question.
            answer: The generated answer.

        Returns:
            Float between 0.0 and 1.0.
        """
        prompt = self.RELEVANCE_PROMPT.format(question=question, answer=answer)
        response = self._call_llm(prompt)
        return self._parse_score(response)

    def score_context_precision(self, question: str, context: str) -> float:
        """Score what fraction of retrieved chunks are relevant.

        Args:
            question: The user's question.
            context: The retrieved context chunks.

        Returns:
            Float between 0.0 and 1.0.
        """
        prompt = self.CONTEXT_PRECISION_PROMPT.format(question=question, context=context)
        response = self._call_llm(prompt)
        return self._parse_score(response)

    def score_context_recall(self, expected: str, context: str) -> float:
        """Score whether context covers enough to produce the expected answer.

        Args:
            expected: The expected/ground-truth answer.
            context: The retrieved context chunks.

        Returns:
            Float between 0.0 and 1.0.
        """
        prompt = self.CONTEXT_RECALL_PROMPT.format(expected=expected, context=context)
        response = self._call_llm(prompt)
        return self._parse_score(response)

    def score_all(
        self,
        question: str,
        expected: str,
        actual: str,
        context: str,
    ) -> Dict[str, float]:
        """Run all 4 metrics and return a dict of scores.

        Args:
            question: The user's question.
            expected: The expected/ground-truth answer.
            actual: The generated answer.
            context: The retrieved context chunks.

        Returns:
            Dict with keys: faithfulness, relevance, context_precision, context_recall.
        """
        return {
            "faithfulness": self.score_faithfulness(context, actual),
            "relevance": self.score_relevance(question, actual),
            "context_precision": self.score_context_precision(question, context),
            "context_recall": self.score_context_recall(expected, context),
        }
