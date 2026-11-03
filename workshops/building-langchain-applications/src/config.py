"""Small configuration support; RAG operations remain visible in the notebook."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    oracle_user: str
    oracle_password: str
    oracle_dsn: str
    openai_api_key: str
    openai_model: str
    embedding_model: str
    corpus_version: str


def load_settings() -> Settings:
    load_dotenv()
    required = (
        "ORACLE_USER",
        "ORACLE_PASSWORD",
        "ORACLE_DSN",
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "OPENAI_EMBEDDING_MODEL",
    )
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
    return Settings(
        oracle_user=os.environ["ORACLE_USER"],
        oracle_password=os.environ["ORACLE_PASSWORD"],
        oracle_dsn=os.environ["ORACLE_DSN"],
        openai_api_key=os.environ["OPENAI_API_KEY"],
        openai_model=os.environ["OPENAI_MODEL"],
        embedding_model=os.environ["OPENAI_EMBEDDING_MODEL"],
        corpus_version=os.environ.get("CORPUS_VERSION", "2026.1"),
    )
