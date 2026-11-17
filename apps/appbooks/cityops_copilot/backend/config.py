"""Settings for the CityOps Copilot appbook.

Values come from the environment, then from this folder's ignored ``.env``,
then from the notebook's own ``.env`` in
``notebooks/agent_memory/cityops_copilot/`` — so one file can configure both. The
defaults are the notebook's: the ``prism`` user on ``localhost:1522/FREEPDB1``,
the in-database ``ALL_MINILM_L12_V2`` model and ``llama3.2`` on the local
Ollama server.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

APPBOOK_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = APPBOOK_DIR.parents[2]
NOTEBOOK_DIR = REPO_DIR / "notebooks" / "agent_memory" / "cityops_copilot"
FRONTEND_DIR = APPBOOK_DIR / "frontend"
DIAGRAMS_DIR = NOTEBOOK_DIR / "diagrams"
NOTEBOOK_FILE = "cityops_copilot_agent_memory_ollama.ipynb"
NOTEBOOK_URL = f"https://github.com/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/agent_memory/cityops_copilot/{NOTEBOOK_FILE}"

load_dotenv(APPBOOK_DIR / ".env", override=False)
load_dotenv(
    NOTEBOOK_DIR / ".env", override=False
)  # the notebook's DBPASSWORD, DB_DSN, OLLAMA_BASE_URL


def _data_dir() -> Path:
    # The notebook reads the two datasets from the data folder beside it. So does the appbook.
    return NOTEBOOK_DIR / "data"


_PREFIX_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,15}_$")


@dataclass(frozen=True)
class Settings:
    db_user: str
    db_password: str
    db_dsn: str
    onnx_model: str
    ollama_base_url: str
    ollama_model: str
    table_prefix: str
    demo_finding_count: int
    demo_narrative_count: int
    data_dir: Path

    @property
    def password_set(self) -> bool:
        return bool(self.db_password) and self.db_password != "CHANGE_ME"


def load_settings() -> Settings:
    prefix = os.getenv("APPBOOK_TABLE_PREFIX", "CITYAPP_").upper()
    if not _PREFIX_RE.match(prefix) or prefix == "CITY_":
        # CITY_ belongs to the notebook; the appbook never writes there.
        raise ValueError(
            f"APPBOOK_TABLE_PREFIX={prefix!r} is not allowed: use letters, digits and _, "
            "end with _, and do not use the notebook's CITY_ prefix."
        )
    return Settings(
        db_user=os.getenv("DBUSER", "prism"),
        db_password=os.getenv("DBPASSWORD", os.getenv("PASSWORD", "")),
        db_dsn=os.getenv("DB_DSN", "localhost:1522/FREEPDB1"),
        onnx_model=os.getenv("ONNX_MODEL", "ALL_MINILM_L12_V2").upper(),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2"),
        table_prefix=prefix,
        demo_finding_count=max(1, int(os.getenv("DEMO_FINDING_COUNT", "15"))),
        demo_narrative_count=max(1, int(os.getenv("DEMO_NARRATIVE_COUNT", "4"))),
        data_dir=_data_dir(),
    )
