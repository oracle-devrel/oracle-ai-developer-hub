"""Configuration and constants for team-brain (Oracle AI Database edition).

Everything comes from the environment (see env.example). The defaults match the
local docker-compose container so a fresh clone runs with no configuration.
"""

from __future__ import annotations

import os
from pathlib import Path

import oracledb
from dotenv import load_dotenv

load_dotenv()

# Identify this app's connections the way the rest of the Developer Hub does.
oracledb.defaults.program = "devrel-developerhub-team-brain"

# --- Paths ---
PACKAGE_DIR = Path(__file__).resolve().parent
REPO_DIR = PACKAGE_DIR.parent
DATA_DIR = REPO_DIR / "data"

# --- Oracle AI Database (the one shared table lives here, and so does the policy) ---
ORACLE_DSN = os.getenv("ORACLE_DSN", "localhost:1521/FREEPDB1")
ORACLE_USER = os.getenv("ORACLE_USER", "TEAMBRAIN").upper()
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD", "TeamBrain123")
# The test suite uses its own schema so it never wipes the dev knowledge base.
ORACLE_USER_TEST = os.getenv("ORACLE_USER_TEST", f"{ORACLE_USER}_TEST").upper()
ORACLE_PASSWORD_TEST = os.getenv("ORACLE_PASSWORD_TEST", ORACLE_PASSWORD)

# --- Embeddings: an ONNX model loaded INTO the database (scripts/bootstrap_db.py).
# `VECTOR_EMBEDDING(<model> USING <text> AS DATA)` is a SQL function, so the text
# being embedded never leaves the database and there is no embedding service.
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "ALL_MINILM_L12_V2")
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "384"))
# MiniLM reads ~128 tokens; anything past this is ignored by the model anyway.
EMBEDDING_MAX_CHARS = int(os.getenv("EMBEDDING_MAX_CHARS", "1500"))

# --- Retrieval legs: "langchain" runs the vector + keyword legs through Oracle's
# LangChain package (OracleVS + OracleTextSearchRetriever); "sql" runs the same
# two queries as plain SQL. Both hit the same table, so the row policy applies
# either way. The test suite asserts they agree.
RETRIEVAL_BACKEND = os.getenv("RETRIEVAL_BACKEND", "langchain").lower()

# --- Agent LLM (planner + synthesizer + the CLI agent). Any OpenAI-compatible
# endpoint; OpenRouter by default so one key covers many models.
LLM_API_KEY = (
    os.getenv("LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
)
LLM_BASE_URL = os.getenv("LLM_BASE_URL") or (
    "https://openrouter.ai/api/v1" if os.getenv("OPENROUTER_API_KEY") else ""
)
PLANNER_MODEL = os.getenv("PLANNER_MODEL", "anthropic/claude-haiku-4.5")
SYNTH_MODEL = os.getenv("SYNTH_MODEL", "anthropic/claude-sonnet-4.6")

# --- Connectors ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")

# --- Retrieval tunables ---
RRF_K = int(os.getenv("RRF_K", "60"))
AGE_HALF_LIFE_DAYS = float(os.getenv("AGE_HALF_LIFE_DAYS", "180"))
SEARCH_DEFAULT_LIMIT = int(os.getenv("SEARCH_DEFAULT_LIMIT", "10"))

# The identity the CLI uses when none is supplied. A raw username with no group
# grant: it sees public, company-wide content only. Never an implicit superuser.
DEFAULT_USER = os.getenv("TEAMBRAIN_DEFAULT_USER", "demo")

# --- MCP service ---
MCP_HOST = os.getenv("TEAMBRAIN_MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.getenv("TEAMBRAIN_MCP_PORT", "8765"))


def has_llm() -> bool:
    """True when a real LLM is configured; otherwise the deterministic fallback is used."""
    return bool(LLM_API_KEY)
