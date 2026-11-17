"""Small, transparent grounding decisions used by the notebook and tests."""

from __future__ import annotations

from typing import Any


def citations_from_documents(documents: list[Any]) -> list[dict[str, str]]:
    citations: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for document in documents:
        metadata = document.metadata
        source_url = metadata["source_url"]
        chunk_id = metadata.get("chunk_id", metadata["document_id"])
        identity = (source_url, chunk_id)
        if identity not in seen:
            citations.append({"title": metadata["title"], "url": source_url, "chunk_id": chunk_id})
            seen.add(identity)
    return citations


def citation_urls_are_retrieved(citations: list[dict[str, str]], documents: list[Any]) -> bool:
    """Check that every citation identifies an exact retrieved chunk.

    The historical function name is retained for the notebook/tests, but URL-only
    membership is deliberately not sufficient: several corpus records can share a
    source URL while representing different evidence.
    """
    retrieved_chunks = {
        (
            document.metadata["source_url"],
            document.metadata.get("chunk_id", document.metadata["document_id"]),
        )
        for document in documents
    }
    cited_chunks = {(citation.get("url"), citation.get("chunk_id")) for citation in citations}
    return bool(citations) and cited_chunks.issubset(retrieved_chunks)


def grounding_decision(results: list[tuple[Any, float]], max_distance: float) -> dict[str, Any]:
    """Return the notebook's deterministic answer-eligibility decision.

    Retrieval and model calls remain visible in the notebook. This function only
    centralizes the safety decision so empty/weak evidence has regression coverage.
    A result exactly on the configured boundary is accepted; larger distances are
    rejected. Results are compared by ascending distance so caller ordering does
    not change which document is considered the closest match.
    """
    if not results:
        return {
            "grounded": False,
            "supporting_document": None,
            "best_score": None,
            "uncertainty": "The corpus has no matching evidence for this query and filter.",
        }

    supporting_document, best_score = min(results, key=lambda result: result[1])
    if best_score > max_distance:
        return {
            "grounded": False,
            "supporting_document": supporting_document,
            "best_score": best_score,
            "uncertainty": f"The closest result was too distant ({best_score:.4f}) to answer from this dataset.",
        }

    return {
        "grounded": True,
        "supporting_document": supporting_document,
        "best_score": best_score,
        "uncertainty": None,
    }
