"""Researcher agent: retrieves evidence for a sub-query."""

from typing import Callable, Dict, List

from ragcli.utils.logger import get_logger

logger = get_logger(__name__)


class Researcher:
    """Calls a search function and formats results as evidence."""

    def __init__(self, config: dict):
        self.config = config

    def run(self, sub_query: str, search_func: Callable) -> Dict:
        """Retrieve evidence for a sub-query using the provided search function.

        Args:
            sub_query: The question to search for.
            search_func: Callable that takes a query string and returns a list of chunk dicts.

        Returns:
            Dict with keys: evidence (List[Dict]), graph_paths (List)
        """
        try:
            raw_chunks = search_func(sub_query)
            evidence = self._format_evidence(raw_chunks)
            return {"evidence": evidence, "graph_paths": []}

        except Exception as e:
            logger.warning(f"Researcher search failed for '{sub_query}': {e}")
            return {"evidence": [], "graph_paths": []}

    def _format_evidence(self, chunks: List[Dict]) -> List[Dict]:
        """Normalize chunk dicts into a consistent evidence format."""
        evidence = []
        for chunk in chunks:
            evidence.append({
                "chunk_id": chunk.get("chunk_id", ""),
                "text": chunk.get("text", ""),
                "similarity_score": chunk.get("similarity_score", 0.0),
                "document_id": chunk.get("document_id", ""),
            })
        return evidence
