# Hosted MCP server for the Second Brain — serves the brain over HTTP + bearer auth.
# Build context = repo root:  docker build -f deploy/Dockerfile .
FROM python:3.12-slim

WORKDIR /app
# ffmpeg: audio extraction for the /diagram video intake
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
COPY deploy/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# the agent code (mcp_http reuses mcp_server's tools; db/content do the DB work)
COPY oracle/agent/ ./agent/
# the read-only web UI (served by webui.py from /app/web when UI_ENABLED; dark otherwise)
COPY web/ ./web/
COPY deploy/entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

WORKDIR /app/agent
ENV PORT=8000
EXPOSE 8000
# entrypoint unpacks the wallet (BRAIN_WALLET_B64) then runs uvicorn. Other config comes from
# Fly secrets (DB_DSN, DB_USER, APP_PWD, DB_WALLET_PASSWORD, MCP_AUTH_TOKEN).
CMD ["/app/entrypoint.sh"]
