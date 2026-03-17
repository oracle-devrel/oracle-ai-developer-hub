"""Reasoner agent: analyzes evidence, cross-references, identifies contradictions."""

import json
import re
from typing import Dict, List

from ragcli.core.embedding import generate_response
from ragcli.utils.logger import get_logger

logger = get_logger(__name__)


class Reasoner:
    """Analyzes gathered evidence and produces a structured analysis."""

    def __init__(self, config: dict):
        self.config = config
        self.model = config["ollama"]["chat_model"]

    def run(self, query: str, evidence: List[Dict]) -> Dict:
        """Analyze evidence to produce analysis, citations, and contradictions.

        Returns:
            Dict with keys: analysis (str), citations (List[str]), contradictions (List[str])
        """
        try:
            evidence_text = self._format_evidence(evidence)

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a reasoning agent. Analyze the provided evidence to answer the query. "
                        "Cross-reference pieces of evidence, identify any contradictions, and cite sources. "
                        "Respond ONLY with valid JSON in this exact format:\n"
                        '{"analysis": "your analysis text", "citations": ["chunk_id1"], "contradictions": ["description of contradiction"]}'
                    ),
                },
                {
                    "role": "user",
                    "content": f"Query: {query}\n\nEvidence:\n{evidence_text}",
                },
            ]

            raw = generate_response(messages, self.model, self.config, stream=False)
            return self._parse_response(raw)

        except Exception as e:
            logger.warning(f"Reasoner failed: {e}")
            return {"analysis": "", "citations": [], "contradictions": []}

    def _format_evidence(self, evidence: List[Dict]) -> str:
        """Format evidence list into a readable string for the LLM."""
        parts = []
        for i, item in enumerate(evidence, 1):
            chunk_id = item.get("chunk_id", f"chunk_{i}")
            text = item.get("text", "")
            parts.append(f"[{chunk_id}]: {text}")
        return "\n".join(parts)

    def _parse_response(self, raw: str) -> Dict:
        """Parse LLM JSON output, with fallback."""
        try:
            result = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                try:
                    result = json.loads(match.group())
                except (json.JSONDecodeError, TypeError):
                    return {"analysis": "", "citations": [], "contradictions": []}
            else:
                return {"analysis": "", "citations": [], "contradictions": []}

        return {
            "analysis": result.get("analysis", ""),
            "citations": result.get("citations", []),
            "contradictions": result.get("contradictions", []),
        }
