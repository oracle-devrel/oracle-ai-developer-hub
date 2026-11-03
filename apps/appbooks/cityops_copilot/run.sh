#!/usr/bin/env bash
# Launch the CityOps Copilot appbook.
#   Python: $PYTHON if set, else python3.
#   Installs requirements.txt only when an import check fails.
#   HOST and PORT override the address (default 127.0.0.1:8730).
set -euo pipefail

cd "$(dirname "$0")"

PY="${PYTHON:-python3}"

"$PY" -c 'import fastapi, uvicorn, dotenv, oracledb, requests, numpy, langchain_ollama, langchain_oracledb, oracleagentmemory' 2>/dev/null \
  || "$PY" -m pip install -q -r requirements.txt

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8730}"
echo "→ CityOps Copilot appbook on http://${HOST}:${PORT}/  (python: ${PY})"
exec "$PY" -m uvicorn backend.main:app --host "${HOST}" --port "${PORT}" "$@"
