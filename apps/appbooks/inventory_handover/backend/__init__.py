"""Inventory handover appbook backend.

OAMP 26.8 and its companions come from ``requirements.txt``. If the notebook's
first cell has already installed them into its package overlay
(``notebooks/agent_memory/inventory_handover/.packages``), put that overlay
first, as the notebook does, so both run the same packages.
"""

import sys
from pathlib import Path

_PACKAGES = (
    Path(__file__).resolve().parents[4]
    / "notebooks"
    / "agent_memory"
    / "inventory_handover"
    / ".packages"
)
if _PACKAGES.is_dir() and str(_PACKAGES) not in sys.path:
    sys.path.insert(0, str(_PACKAGES))
