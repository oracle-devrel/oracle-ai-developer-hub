"""Embeddings are a SQL function in the Oracle edition.

`VECTOR_EMBEDDING(...)` runs entirely in-database — there is no local model,
no batching, and no numpy array to compare; `embed_text(conn, text)` returns
a plain list[float] of length EMBEDDING_DIMENSIONS.
"""

from __future__ import annotations

import pytest

from team_brain.config import EMBEDDING_DIMENSIONS, EMBEDDING_MAX_CHARS
from team_brain.db import DocumentDB
from team_brain.embeddings import clip_for_embedding, embed_text

pytestmark = pytest.mark.requires_oracle


def test_embed_text_shape(db: DocumentDB) -> None:
    v = embed_text(db.connection, "hello")
    assert len(v) == EMBEDDING_DIMENSIONS
    assert all(isinstance(x, float) for x in v)


def test_embed_is_deterministic(db: DocumentDB) -> None:
    a = embed_text(db.connection, "the billing service deploys via blue-green")
    b = embed_text(db.connection, "the billing service deploys via blue-green")
    assert a == b


def test_embed_differs_for_different_text(db: DocumentDB) -> None:
    a = embed_text(db.connection, "alpha")
    b = embed_text(db.connection, "beta")
    assert a != b


def test_clip_for_embedding_truncates_long_text() -> None:
    long_text = "x" * (EMBEDDING_MAX_CHARS + 500)
    clipped = clip_for_embedding(long_text)
    assert len(clipped) == EMBEDDING_MAX_CHARS
    assert clip_for_embedding("short") == "short"
