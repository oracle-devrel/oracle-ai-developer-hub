"""Diff-chunker for incremental re-indexing.

Compares old chunks against new content to determine what changed,
enabling selective re-embedding instead of full reprocessing.
"""

import difflib
from dataclasses import dataclass, field
from typing import Dict, List

from ragcli.utils.helpers import generate_uuid
from ragcli.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DiffResult:
    """Result of diffing old chunks against new chunks."""

    added: list = field(default_factory=list)
    removed: list = field(default_factory=list)
    modified: list = field(default_factory=list)
    unchanged: list = field(default_factory=list)


class DiffChunker:
    """Compares old chunks against new content and determines what changed.

    Uses sequence matching to find the best alignment between old and new
    chunk lists, then classifies each chunk as added, removed, modified,
    or unchanged.
    """

    def __init__(self, similarity_threshold: float = 0.6):
        """Initialize the DiffChunker.

        Args:
            similarity_threshold: Minimum similarity ratio (0.0-1.0) for
                two chunks to be considered a match. Defaults to 0.6.
        """
        self.similarity_threshold = similarity_threshold

    def diff(self, old_chunks: List[Dict], new_chunks: List[Dict]) -> DiffResult:
        """Compare old chunks against new chunks and classify changes.

        Uses greedy matching: for each new chunk, finds the best-matching
        old chunk. Once an old chunk is matched, it's removed from candidates.

        Args:
            old_chunks: List of dicts with at least {"chunk_id": str, "content": str}
            new_chunks: List of dicts with at least {"chunk_id": str, "content": str}

        Returns:
            DiffResult with added, removed, modified, and unchanged lists.
        """
        result = DiffResult()

        # Track which old chunks have been matched
        available_old = list(range(len(old_chunks)))

        for new_chunk in new_chunks:
            best_idx = None
            best_ratio = 0.0

            for old_idx in available_old:
                ratio = self._similarity(
                    old_chunks[old_idx]["content"],
                    new_chunk["content"],
                )
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_idx = old_idx

            if best_idx is not None and best_ratio >= self.similarity_threshold:
                # Found a match; remove from candidates
                available_old.remove(best_idx)

                if best_ratio >= 0.95:
                    result.unchanged.append(new_chunk)
                else:
                    result.modified.append({
                        "old": old_chunks[best_idx],
                        "new": new_chunk,
                    })
            else:
                result.added.append(new_chunk)

        # Any old chunks left unmatched are removed
        for old_idx in available_old:
            result.removed.append(old_chunks[old_idx])

        logger.debug(
            "Diff complete: %d added, %d removed, %d modified, %d unchanged",
            len(result.added),
            len(result.removed),
            len(result.modified),
            len(result.unchanged),
        )

        return result

    def _similarity(self, text_a: str, text_b: str) -> float:
        """Compute similarity ratio between two texts.

        Args:
            text_a: First text.
            text_b: Second text.

        Returns:
            Float between 0.0 and 1.0 indicating similarity.
        """
        return difflib.SequenceMatcher(None, text_a, text_b).ratio()

    def summarize(self, diff_result: DiffResult) -> Dict[str, int]:
        """Summarize a DiffResult as counts.

        Args:
            diff_result: The DiffResult to summarize.

        Returns:
            Dict with keys "added", "removed", "modified", "unchanged"
            mapped to their respective counts.
        """
        return {
            "added": len(diff_result.added),
            "removed": len(diff_result.removed),
            "modified": len(diff_result.modified),
            "unchanged": len(diff_result.unchanged),
        }
