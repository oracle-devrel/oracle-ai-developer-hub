"""Enrichment-before-embedding: the retrieval-quality centerpiece.

Embedding raw chat is the naive mistake: "sounds good" and "shipping it" land
right next to the actual technical resolution, so retrieval drowns in noise.
Instead we ask a fast model to distill a thread into structured fields, then
embed the distilled *question + resolution*. The raw body is still stored for
keyword search and citation.

Best-effort by design: if enrichment fails (or no LLM is configured), we fall
back to the raw text and NEVER drop the document.

This is ENRICHMENT POLICY: one shared decision about what a noisy thread
actually meant, applied at write time so the corpus is clean for every reader.
Doing it here (once, in the substrate) rather than in each person's own agent is
the point. See docs/PERSONAL_VS_TEAM.md.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from team_brain.config import PLANNER_MODEL, has_llm
from team_brain.llm import chat_model


class Distilled(BaseModel):
    """Structured, searchable knowledge distilled from a chat thread."""

    question: str = Field(description="The core question/problem, one line.")
    summary: str = Field(description="2-3 sentence summary.")
    resolution: str = Field(description="What was decided/resolved.")
    systems: list[str] = Field(default_factory=list)
    refs: list[str] = Field(default_factory=list)


def enrich_thread(thread_text: str) -> dict[str, Any] | None:
    """Return {question, summary, resolution, systems, refs} or None on failure/offline."""
    if not has_llm() or not thread_text.strip():
        return None
    try:
        distiller = chat_model(PLANNER_MODEL, max_tokens=500).with_structured_output(Distilled)
        out = distiller.invoke(f"Distill this thread:\n\n{thread_text[:6000]}")
        return out.model_dump()
    except Exception:  # noqa: BLE001 - enrichment is best-effort
        return None


def embedding_text(title: str, body: str, enriched: dict[str, Any] | None) -> str:
    """The string to embed: distilled question+resolution when available, else title+body."""
    if enriched:
        parts = [
            enriched.get("question", ""),
            enriched.get("resolution", ""),
            enriched.get("summary", ""),
        ]
        text = "\n".join(p for p in parts if p).strip()
        if text:
            return text
    return f"{title}\n{body}".strip()


def enriched_json(enriched: dict[str, Any] | None) -> str:
    return json.dumps(enriched) if enriched else ""
