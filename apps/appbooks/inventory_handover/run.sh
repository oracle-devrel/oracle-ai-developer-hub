#!/usr/bin/env bash
# Launch the inventory handover appbook.
#   Python: $PYTHON if set, else python3. Installs requirements.txt (OAMP 26.8 and
#   the notebook's pins) only when an import or version check fails. If the
#   notebook's first cell has created its .packages overlay, the backend puts
#   that first, as the notebook does.
#   HOST and PORT override the address (default 127.0.0.1:8735).
set -euo pipefail

cd "$(dirname "$0")"

PY="${PYTHON:-python3}"

"$PY" -c 'import backend, fastapi, uvicorn, dotenv, oracledb, pandas, langchain_openai, oracleagentmemory
from importlib.metadata import version; assert version("oracleagentmemory") == "26.8.0"' 2>/dev/null \
  || "$PY" -m pip install -q -r requirements.txt

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8735}"
echo "→ Inventory handover appbook on http://${HOST}:${PORT}/  (python: ${PY})"
exec "$PY" -m uvicorn backend.main:app --host "${HOST}" --port "${PORT}" "$@"
