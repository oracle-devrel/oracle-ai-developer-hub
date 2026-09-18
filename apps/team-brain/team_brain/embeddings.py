"""Embeddings are a SQL function.

Oracle's augmented all-MiniLM-L12-v2 ONNX model is loaded INTO the database once
(scripts/bootstrap_db.py). After that:

    VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING :text AS DATA)

returns a 384-dim VECTOR inside any SQL statement. The ingest MERGE computes the
embedding as part of the write, and the vector search computes the query
embedding as part of the read. No embedding service, no model download in
Python, and the text being embedded never leaves the database.

This module only holds the two helpers that make that explicit.
"""

from __future__ import annotations

from typing import Any

from team_brain.config import EMBEDDING_MAX_CHARS, EMBEDDING_MODEL


def embedding_sql(bind_name: str = "embed_text", model: str = EMBEDDING_MODEL) -> str:
    """The SQL expression that embeds a bound string in-database."""
    return f"VECTOR_EMBEDDING({model} USING :{bind_name} AS DATA)"


def clip_for_embedding(text: str) -> str:
    """MiniLM reads about 128 tokens; sending more changes nothing but the bind size."""
    return text[:EMBEDDING_MAX_CHARS]


def embed_text(conn: Any, text: str) -> list[float]:
    """Embed one string through the database (used by tests and the parity check)."""
    cur = conn.cursor()
    cur.execute(f"SELECT {embedding_sql('t')} FROM dual", t=clip_for_embedding(text))
    (vec,) = cur.fetchone()
    return [float(x) for x in vec]
