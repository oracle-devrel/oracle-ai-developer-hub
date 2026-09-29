"""The query agent for `team-brain ask`: a LangChain agent over the search primitives.

The primitives (`search`, `search_code`, `who_knows`) are the same ones the MCP
server exposes to Claude Code. Here they are bound as LangChain tools to ONE
database session whose identity was established up front. The model never sees
or passes an identity; it cannot ask for someone else's rows because there is no
way to say so. The row policy in the database does the filtering.

SCOPE NOTE: this answer path is a CONVENIENCE for the CLI and for anyone not
driving from an MCP client. It is stateless and evidence-bound (answer only from
retrieved rows, always cite), so it is not a personality. The primary interface
is `mcp_server.py`, which returns evidence and lets each caller's own agent do the
interpreting. See docs/PERSONAL_VS_TEAM.md.

Offline (no LLM key) it degrades to a deterministic plan -> execute -> extractive
answer so the app and the test suite run without a key.
"""

from __future__ import annotations

from typing import Any

from team_brain.access import Identity
from team_brain.config import SYNTH_MODEL, has_llm
from team_brain.db import DocumentDB
from team_brain.llm import AVAILABLE_TOOLS, chat_model, plan_tools, synthesize
from team_brain.retrieval import Evidence, search

AGENT_SYSTEM = (
    "You are a team knowledge base assistant. Answer ONLY from what the tools return. "
    "Call `search` for most questions, `search_code` for code/implementation questions, "
    "and `who_knows` for 'who knows / who owns' questions. You may call several tools. "
    "Cite each claim inline as [source - url] using the rows the tools returned. "
    "If the tools return nothing relevant, say the knowledge base does not cover it. "
    "Never invent facts, names, or citations."
)


def _run_search(question: str, project: str | None, db: DocumentDB) -> list[Evidence]:
    return search(question, project=project, db=db)


def _run_search_code(question: str, project: str | None, db: DocumentDB) -> list[Evidence]:
    """Code-only view: evidence tagged as code, or sourced from a repo."""
    hits = search(question, project=project, db=db, limit=20)
    return [e for e in hits if e.metadata.get("kind") == "code" or e.source == "github"][:10]


def _run_who_knows(question: str, project: str | None, db: DocumentDB) -> list[dict[str, Any]]:
    return db.who_knows(question, project, 5)


class _Trace:
    """What the agent actually retrieved, so citations come from real rows."""

    def __init__(self) -> None:
        self.evidence: list[Evidence] = []
        self.experts: list[dict[str, Any]] = []
        self.tools_called: list[str] = []


def build_tools(db: DocumentDB, project: str | None, trace: _Trace) -> list[Any]:
    """The three primitives as LangChain tools, bound to this session's identity."""
    from langchain_core.tools import tool

    @tool
    def search_kb(query: str) -> list[dict[str, Any]]:
        """Search the team knowledge base across every source the caller may see."""
        hits = _run_search(query, project, db)
        trace.tools_called.append("search")
        trace.evidence.extend(hits)
        return [e.to_row() for e in hits]

    @tool
    def search_code(query: str) -> list[dict[str, Any]]:
        """Search only code and repository knowledge the caller may see."""
        hits = _run_search_code(query, project, db)
        trace.tools_called.append("search_code")
        trace.evidence.extend(hits)
        return [e.to_row() for e in hits]

    @tool
    def who_knows(topic: str) -> list[dict[str, Any]]:
        """Find who owns or knows the most about a topic (ranked authors)."""
        experts = _run_who_knows(topic, project, db)
        trace.tools_called.append("who_knows")
        trace.experts = experts
        return experts

    @tool
    def get_document(row_id: str) -> dict[str, Any]:
        """Full text of one search result by its `id` (search rows only carry a snippet)."""
        trace.tools_called.append("get_document")
        row = db.get_document(row_id)
        if row is None:
            return {"found": False, "id": row_id}
        return {"found": True, "id": row["id"], "title": row["title"], "url": row["url"],
                "author": row["author"], "text": row["body"]}  # fmt: skip

    search_kb.name = "search"
    return [search_kb, search_code, who_knows, get_document]


def _dedupe(evidence: list[Evidence]) -> list[Evidence]:
    best: dict[str, Evidence] = {}
    for e in evidence:
        if e.id not in best or e.score > best[e.id].score:
            best[e.id] = e
    return sorted(best.values(), key=lambda e: e.score, reverse=True)[:10]


def _result(
    text: str, merged: list[Evidence], experts: list[dict[str, Any]], plan: Any
) -> dict[str, Any]:
    return {
        "answer": text,
        "citations": [
            {"source": e.source, "title": e.title, "url": e.url} for e in merged if e.url
        ],
        "evidence": [e.to_row() for e in merged],
        "experts": experts,
        "plan": plan,
    }


def answer(
    question: str,
    identity: Identity | None = None,
    project: str | None = None,
    db: DocumentDB | None = None,
) -> dict[str, Any]:
    """Answer a question as `identity`. Returns answer + citations + evidence + plan.

    The identity goes onto the database session once; every tool call after that
    is filtered by the row policy. The LLM only ever sees rows the caller may see.
    """
    owns_db = db is None
    if db is None:
        if identity is None:
            raise ValueError("answer() needs an Identity when no DocumentDB session is given")
        db = DocumentDB(identity=identity)
    elif identity is not None and db.identity != identity:
        db.set_identity(identity)
    try:
        if has_llm():
            return _answer_with_agent(question, project, db)
        return _answer_offline(question, project, db)
    finally:
        if owns_db:
            db.close()


def _answer_with_agent(question: str, project: str | None, db: DocumentDB) -> dict[str, Any]:
    from langchain.agents import create_agent

    trace = _Trace()
    agent = create_agent(
        chat_model(SYNTH_MODEL, max_tokens=900),
        tools=build_tools(db, project, trace),
        system_prompt=AGENT_SYSTEM,
    )
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    final = result["messages"][-1]
    text = final.content if isinstance(final.content, str) else str(final.content)
    merged = _dedupe(trace.evidence)
    if not trace.tools_called:
        # The model answered without looking. Not acceptable for a knowledge base.
        merged = _dedupe(_run_search(question, project, db))
        text = synthesize(question, [e.to_row() for e in merged])
    return _result(
        text.strip(), merged, trace.experts, {"tools": trace.tools_called, "mode": "agent"}
    )


def _answer_offline(question: str, project: str | None, db: DocumentDB) -> dict[str, Any]:
    """Deterministic plan -> execute -> extractive synthesis (no LLM)."""
    plan = plan_tools(question, AVAILABLE_TOOLS)
    tools = plan.get("tools") or AVAILABLE_TOOLS
    proj = project if project is not None else plan.get("project")
    evidence: list[Evidence] = []
    experts: list[dict[str, Any]] = []
    if "search" in tools:
        evidence.extend(_run_search(question, proj, db))
    if "search_code" in tools:
        evidence.extend(_run_search_code(question, proj, db))
    if "who_knows" in tools:
        experts = _run_who_knows(question, proj, db)
    merged = _dedupe(evidence)
    text = synthesize(question, [e.to_row() for e in merged])
    return _result(text, merged, experts, plan)
