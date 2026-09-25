"""LLM access for the planner, the synthesizer, and enrichment: LangChain chat models.

Provider-independent: `LLM_BASE_URL` + `LLM_API_KEY` point at any OpenAI-compatible
endpoint (OpenRouter by default, so one key covers Claude, GPT, Gemini, ...).

Runs WITHOUT a key. When none is set, every call falls back to a deterministic
path (plan = "use every tool", synthesize = an extractive answer built from the
evidence, enrichment = skipped). That keeps the whole app, and the test suite,
runnable offline; wiring a key turns on real reasoning without touching callers.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from team_brain.config import LLM_API_KEY, LLM_BASE_URL, PLANNER_MODEL, SYNTH_MODEL, has_llm

AVAILABLE_TOOLS = ["search", "search_code", "who_knows"]


def chat_model(model: str, temperature: float = 0.0, max_tokens: int = 800) -> Any:
    """A LangChain chat model on the configured OpenAI-compatible endpoint."""
    from langchain_openai import ChatOpenAI

    kwargs: dict[str, Any] = {
        "model": model,
        "api_key": LLM_API_KEY,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if LLM_BASE_URL:
        kwargs["base_url"] = LLM_BASE_URL
    return ChatOpenAI(**kwargs)


class RoutePlan(BaseModel):
    """Which search primitives to run for a question."""

    tools: list[str] = Field(description="Subset of: search, search_code, who_knows")
    project: str | None = Field(default=None, description="Restrict to this project, or null")
    rationale: str = ""


def plan_tools(question: str, available_tools: list[str]) -> dict[str, Any]:
    """Decide which primitives to run. Returns {tools, project, rationale}."""
    if not has_llm():
        return {"tools": list(available_tools), "project": None, "rationale": "offline: run all"}
    try:
        planner = chat_model(PLANNER_MODEL, max_tokens=300).with_structured_output(RoutePlan)
        plan = planner.invoke(
            "Route this team-knowledge-base question to the right search primitives.\n"
            f"Available: {available_tools}\n"
            "Use search_code only for code/implementation questions; who_knows for "
            "'who knows / who owns / who worked on' questions; search otherwise.\n\n"
            f"Question: {question}"
        )
        tools = [t for t in plan.tools if t in available_tools]
        return {
            "tools": tools or list(available_tools),
            "project": plan.project,
            "rationale": plan.rationale,
        }
    except Exception:  # noqa: BLE001 - planning is advisory
        return {"tools": list(available_tools), "project": None, "rationale": "fallback"}


SYNTH_SYSTEM = (
    "You answer questions about a team's knowledge base. Use ONLY the provided "
    "evidence. Cite each claim inline as [source - url]. If the evidence does not "
    "answer the question, say so plainly. Never invent facts or citations."
)


def synthesize(question: str, evidence: list[dict[str, Any]]) -> str:
    """Answer the question grounded ONLY in the evidence, with inline citations."""
    if not evidence:
        return "I couldn't find anything about that in the knowledge base."
    if not has_llm():
        return _extractive_answer(evidence)

    bundle = json.dumps(
        [
            {
                "n": i + 1,
                "title": e["title"],
                "source": e["source"],
                "url": e.get("url", ""),
                "snippet": e.get("snippet", ""),
            }
            for i, e in enumerate(evidence)
        ],
        indent=2,
    )
    resp = chat_model(SYNTH_MODEL, max_tokens=700).invoke(
        [
            ("system", SYNTH_SYSTEM),
            ("human", f"Question: {question}\n\nEvidence:\n{bundle}"),
        ]
    )
    text = resp.content if isinstance(resp.content, str) else str(resp.content)
    return text.strip() or _extractive_answer(evidence)


def _extractive_answer(evidence: list[dict[str, Any]]) -> str:
    """Deterministic, no-LLM answer: top snippets with citations."""
    lines = ["Here is what the knowledge base has (offline mode, no LLM synthesis):", ""]
    for e in evidence[:3]:
        cite = f"[{e['source']}" + (f" - {e['url']}" if e.get("url") else "") + "]"
        lines.append(f"- {e['title']}: {e.get('snippet', '')} {cite}")
    return "\n".join(lines)
