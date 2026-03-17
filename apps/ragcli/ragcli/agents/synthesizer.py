"""Synthesizer agent: composes a final answer with confidence scoring."""

import json
import re
from typing import Dict, List

from ragcli.core.embedding import generate_response
from ragcli.utils.logger import get_logger

logger = get_logger(__name__)


class Synthesizer:
    """Composes a final answer from analysis and evidence."""

    def __init__(self, config: dict):
        self.config = config
        self.model = config["ollama"]["chat_model"]

    def run(self, query: str, analysis: str, evidence: List[Dict]) -> Dict:
        """Compose a final answer with confidence score and source attribution.

        Returns:
            Dict with keys: answer (str), confidence (float), sources (List[str])
        """
        try:
            source_ids = list({
                item.get("document_id", "") for item in evidence if item.get("document_id")
            })
            evidence_text = self._format_evidence(evidence)

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a synthesis agent. Compose a clear, comprehensive final answer "
                        "based on the analysis and evidence provided. Include a confidence score "
                        "from 0.0 (no confidence) to 1.0 (fully confident). "
                        "Respond ONLY with valid JSON in this exact format:\n"
                        '{"answer": "your final answer", "confidence": 0.85, "sources": ["source1"]}'
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Query: {query}\n\n"
                        f"Analysis:\n{analysis}\n\n"
                        f"Evidence:\n{evidence_text}\n\n"
                        f"Available sources: {source_ids}"
                    ),
                },
            ]

            raw = generate_response(messages, self.model, self.config, stream=False)
            return self._parse_response(raw, analysis, source_ids)

        except Exception as e:
            logger.warning(f"Synthesizer failed: {e}")
            return {"answer": analysis, "confidence": 0.0, "sources": []}

    def _format_evidence(self, evidence: List[Dict]) -> str:
        """Format evidence list into a readable string for the LLM."""
        parts = []
        for i, item in enumerate(evidence, 1):
            chunk_id = item.get("chunk_id", f"chunk_{i}")
            text = item.get("text", "")
            parts.append(f"[{chunk_id}]: {text}")
        return "\n".join(parts)

    def _parse_response(self, raw: str, fallback_analysis: str, fallback_sources: List[str]) -> Dict:
        """Parse LLM JSON output, with fallback."""
        try:
            result = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                try:
                    result = json.loads(match.group())
                except (json.JSONDecodeError, TypeError):
                    return {"answer": fallback_analysis, "confidence": 0.0, "sources": fallback_sources}
            else:
                return {"answer": fallback_analysis, "confidence": 0.0, "sources": fallback_sources}

        # Clamp confidence to [0.0, 1.0]
        confidence = result.get("confidence", 0.0)
        try:
            confidence = max(0.0, min(1.0, float(confidence)))
        except (TypeError, ValueError):
            confidence = 0.0

        return {
            "answer": result.get("answer", fallback_analysis),
            "confidence": confidence,
            "sources": result.get("sources", fallback_sources),
        }
