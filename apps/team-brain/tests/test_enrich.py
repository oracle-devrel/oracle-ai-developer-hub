"""Enrichment: distills threads, falls back gracefully, never drops a doc.

Oracle port: `enrich_thread` builds its distiller from `llm.chat_model(...)
.with_structured_output(Distilled)`, not a raw Anthropic client — see
test_llm.py for the same fake-chat-model pattern.
"""

from __future__ import annotations

from typing import Any

import team_brain.enrich as enrich
from team_brain.enrich import Distilled, embedding_text, enrich_thread


def test_offline_returns_none() -> None:
    # conftest forces offline; enrichment is a no-op that callers must tolerate.
    assert enrich_thread("some long thread text") is None


def test_embedding_text_falls_back_to_title_body() -> None:
    text = embedding_text("Title", "Body content", None)
    assert "Title" in text and "Body content" in text


def test_embedding_text_prefers_enriched() -> None:
    enriched = {"question": "why pin onnx?", "resolution": "fastembed breaks on 1.26+"}
    text = embedding_text("raw title", "raw body", enriched)
    assert "why pin onnx?" in text
    assert "fastembed breaks" in text
    assert "raw body" not in text


class _FakeStructuredModel:
    def __init__(self, output: Any) -> None:
        self._output = output

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        return self._output


class _FakeChatModel:
    def __init__(self, structured_output: Any) -> None:
        self._structured_output = structured_output

    def with_structured_output(self, schema: Any) -> _FakeStructuredModel:
        return _FakeStructuredModel(self._structured_output)


def test_online_enrichment_parses_structured_output(monkeypatch: Any) -> None:
    payload = Distilled(question="q", summary="s", resolution="r", systems=["billing"], refs=[])
    monkeypatch.setattr(enrich, "has_llm", lambda: True)
    monkeypatch.setattr(enrich, "chat_model", lambda *a, **kw: _FakeChatModel(payload))
    out = enrich_thread("bob: something\nalice: resolved it")
    assert out == payload.model_dump()


def test_online_enrichment_failure_falls_back(monkeypatch: Any) -> None:
    def boom(*a: Any, **kw: Any) -> Any:
        raise RuntimeError("api down")

    monkeypatch.setattr(enrich, "has_llm", lambda: True)
    monkeypatch.setattr(enrich, "chat_model", boom)
    assert enrich_thread("thread") is None  # best-effort: no crash, no doc lost


def test_offline_thread_with_no_text_returns_none() -> None:
    assert enrich_thread("") is None
    assert enrich_thread("   ") is None
