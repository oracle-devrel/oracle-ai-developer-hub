"""Planner + synthesizer: offline determinism and stubbed-online behavior.

Oracle port: the LLM is a LangChain chat model (`llm.chat_model(...)`, any
OpenAI-compatible endpoint) rather than a raw Anthropic client with tool-use
blocks. Online behaviour is stubbed by monkeypatching `llm.chat_model` to
return a fake object shaped like a LangChain chat model:
`.with_structured_output(Schema).invoke(prompt) -> Schema(...)` for
structured calls (the planner), and `.invoke(messages) -> SimpleNamespace(content=...)`
for plain text calls (the synthesizer).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import team_brain.llm as llm
from team_brain.agent import AVAILABLE_TOOLS
from team_brain.llm import RoutePlan, plan_tools, synthesize


def test_plan_offline_runs_all_tools() -> None:
    plan = plan_tools("anything", AVAILABLE_TOOLS)
    assert set(plan["tools"]) == set(AVAILABLE_TOOLS)


def test_synthesize_no_evidence_is_honest() -> None:
    out = synthesize("q", [])
    assert "couldn't find" in out.lower()


def test_synthesize_offline_is_extractive_with_citations() -> None:
    evidence = [
        {
            "title": "Deploy runbook",
            "source": "markdown",
            "url": "file://x",
            "snippet": "blue-green",
        }
    ]
    out = synthesize("how to deploy?", evidence)
    assert "Deploy runbook" in out
    assert "markdown" in out


class _FakeStructuredModel:
    def __init__(self, output: Any) -> None:
        self._output = output

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        return self._output


class _FakeChatModel:
    """Stands in for a LangChain chat model in both call shapes llm.py uses."""

    def __init__(self, structured_output: Any = None, text_output: str | None = None) -> None:
        self._structured_output = structured_output
        self._text_output = text_output

    def with_structured_output(self, schema: Any) -> _FakeStructuredModel:
        return _FakeStructuredModel(self._structured_output)

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        return SimpleNamespace(content=self._text_output)


def test_plan_online_filters_to_available(monkeypatch: Any) -> None:
    monkeypatch.setattr(llm, "has_llm", lambda: True)
    plan_output = RoutePlan(tools=["search", "bogus"], project="eng", rationale="code question")
    monkeypatch.setattr(
        llm, "chat_model", lambda *a, **kw: _FakeChatModel(structured_output=plan_output)
    )
    plan = plan_tools("code question", AVAILABLE_TOOLS)
    assert plan["tools"] == ["search"]  # 'bogus' filtered out
    assert plan["project"] == "eng"


def test_plan_online_failure_falls_back(monkeypatch: Any) -> None:
    monkeypatch.setattr(llm, "has_llm", lambda: True)

    def boom(*a: Any, **kw: Any) -> Any:
        raise RuntimeError("planner down")

    monkeypatch.setattr(llm, "chat_model", boom)
    plan = plan_tools("anything", AVAILABLE_TOOLS)
    assert set(plan["tools"]) == set(AVAILABLE_TOOLS)
    assert plan["rationale"] == "fallback"


def test_synthesize_online_returns_model_text(monkeypatch: Any) -> None:
    monkeypatch.setattr(llm, "has_llm", lambda: True)
    monkeypatch.setattr(
        llm,
        "chat_model",
        lambda *a, **kw: _FakeChatModel(text_output="You deploy via blue-green [markdown - x]"),
    )
    out = synthesize(
        "how to deploy?", [{"title": "t", "source": "markdown", "url": "x", "snippet": "s"}]
    )
    assert "blue-green" in out
