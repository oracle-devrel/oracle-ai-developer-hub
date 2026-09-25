"""Load Oracle's augmented all-MiniLM-L12-v2 ONNX model into the connected schema.

The augmented variant includes pre- and post-processing (tokenisation → pooled
embedding) in a single ONNX graph, so VECTOR_EMBEDDING(model USING :text AS DATA)
takes plain text. The standard HuggingFace model.onnx will NOT work because it
requires separate tokenisation and only outputs last_hidden_state, not a pooled
"embedding".

The file goes from this process straight into the database through the BLOB
overload of DBMS_VECTOR.LOAD_ONNX_MODEL, so no directory object, docker cp, or
administrator step is needed. DB_DEVELOPER_ROLE includes the CREATE MINING MODEL
privilege it requires.
"""
from __future__ import annotations

import json
from urllib.request import urlopen

import oracledb

from memory.db import connect_sync
from memory.embeddings import MODEL_NAME, VECTOR_DIM

# Oracle OML resources object storage — L12 augmented variant (~130 MB)
ONNX_URL = (
    "https://objectstorage.us-ashburn-1.oraclecloud.com"
    "/n/adwc4pm/b/OML-Resources/o/all_MiniLM_L12_v2.onnx"
)

MODEL_METADATA = {
    "function": "embedding",
    "embeddingOutput": "embedding",
    "input": {"input": ["DATA"]},
}


def model_already_loaded(conn: oracledb.Connection) -> bool:
    """Return True if the ONNX model is already present in the connected schema."""
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM user_mining_models WHERE model_name = :name",
        name=MODEL_NAME,
    )
    (count,) = cur.fetchone()
    return count > 0


def load_model(conn: oracledb.Connection, url: str = ONNX_URL) -> None:
    """Download the ONNX file and load it as MODEL_NAME through the BLOB overload."""
    with urlopen(url, timeout=600) as response:
        model_bytes = response.read()

    # A ~130 MB upload can outlast a call timeout; lift it for this call only.
    timeout, conn.call_timeout = conn.call_timeout, 0
    try:
        blob = conn.createlob(oracledb.DB_TYPE_BLOB)
        blob.write(model_bytes)
        conn.cursor().execute(
            "BEGIN DBMS_VECTOR.LOAD_ONNX_MODEL(:name, :data, JSON(:meta)); END;",
            name=MODEL_NAME,
            data=blob,
            meta=json.dumps(MODEL_METADATA),
        )
    finally:
        conn.call_timeout = timeout


def ensure_model(conn: oracledb.Connection) -> str:
    """Load the model unless it is already in the schema. Returns a status line."""
    if model_already_loaded(conn):
        return f"ONNX model {MODEL_NAME} already loaded."
    load_model(conn)
    return f"Loaded ONNX model as {MODEL_NAME} (dim={VECTOR_DIM}) from {ONNX_URL}."


def main() -> None:
    """CLI entry point.

    Usage:
        python -m memory.onnx_loader
    """
    conn = connect_sync()
    try:
        print(ensure_model(conn))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
