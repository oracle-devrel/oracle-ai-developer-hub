"""Settings for the inventory handover appbook.

Values come from the environment, then this folder's ignored ``.env``, then
the notebook's own ``.env`` in ``notebooks/agent_memory/inventory_handover/`` —
so the file the notebook reads configures the app too. The defaults are the notebook's.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

APPBOOK_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = APPBOOK_DIR.parents[2]
NOTEBOOK_DIR = REPO_DIR / "notebooks" / "agent_memory" / "inventory_handover"
FRONTEND_DIR = APPBOOK_DIR / "frontend"
DIAGRAMS_DIR = NOTEBOOK_DIR / "diagrams"
DATA_FILE = NOTEBOOK_DIR / "inventory_data.json"
NOTEBOOK_FILE = "inventory_handover_agent_memory_oci.ipynb"
NOTEBOOK_URL = f"https://github.com/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/agent_memory/inventory_handover/{NOTEBOOK_FILE}"
OAMP_VERSION = "26.8.0"

load_dotenv(APPBOOK_DIR / ".env", override=False)
load_dotenv(NOTEBOOK_DIR / ".env", override=False)

_STORE_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,15}$")


@dataclass(frozen=True)
class Settings:
    db_user: str
    db_password: str
    db_dsn: str
    onnx_model: str
    oci_api_key: str | None
    oci_config_file: str
    compartment_id: str | None
    endpoint: str
    model: str
    store: str

    @property
    def password_set(self) -> bool:
        return bool(self.db_password) and self.db_password != "CHANGE_ME"

    @property
    def auth_mode(self) -> str:
        return "API key" if self.oci_api_key else "OCI config file signing"

    @property
    def region(self) -> str:
        m = re.search(r"inference\.generativeai\.([a-z0-9-]+)\.", self.endpoint)
        return m.group(1) if m else "?"


def load_settings() -> Settings:
    store = os.getenv("APPBOOK_STORE", "INVAPP").upper()
    if not _STORE_RE.match(store) or store == "ZH_INVENTORY":
        # ZH_INVENTORY is the notebook's store; the appbook never writes there.
        raise ValueError(
            f"APPBOOK_STORE={store!r} is not allowed: use letters, digits and _, and not the notebook's ZH_INVENTORY."
        )
    return Settings(
        db_user=os.getenv("DBUSER", "prism"),
        db_password=os.getenv("DBPASSWORD", os.getenv("PASSWORD", "")),
        db_dsn=os.getenv("DB_DSN", "localhost:1522/FREEPDB1"),
        onnx_model="ALL_MINILM_L12_V2",  # fixed in the notebook's connection cell
        oci_api_key=os.getenv("OCI_GENAI_API_KEY") or None,
        oci_config_file=os.path.expanduser(os.getenv("OCI_CONFIG_FILE", "~/.oci/config")),
        compartment_id=os.getenv("COMPARTMENT_OCID") or None,
        endpoint=os.getenv(
            "ENDPOINT", "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"
        ).rstrip("/"),
        model=os.getenv("OCI_GENAI_MODEL", "xai.grok-4.3"),
        store=store,
    )
