# Multi-stage build for Oracle Viz MCP Server
# Build stage - uses uv for dependency management
FROM python:3.12-slim-bookworm AS builder

# Copy uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy project files (README.md is required by the pyproject readme field)
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Create the virtual environment and install runtime dependencies.
# --no-editable installs the project as a wheel so the runtime stage only needs .venv.
RUN uv venv && \
    . .venv/bin/activate && \
    uv sync --frozen --no-dev --no-editable

# Runtime stage
FROM python:3.12-slim-bookworm

WORKDIR /app

# Runtime dependencies: curl + pgrep power the health check, ca-certificates for TLS
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    procps \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from the builder
COPY --from=builder /app/.venv /app/.venv

# Create a non-root user for security
RUN groupadd -r app -g 1000 && \
    useradd -r -u 1000 -g app -d /app -s /bin/false app && \
    chown -R app:app /app && \
    chmod -R 755 /app && \
    chmod -R go-w /app

# Defaults for container use; override with -e as needed
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ORACLE_MCP_BIND_HOST="0.0.0.0" \
    ORACLE_MCP_BIND_PORT="8080"

# Expose the port for HTTP/SSE/streamable-http transports
EXPOSE 8080

# Switch to the non-root user
USER app

# Health check: HTTP transports answer on /health, stdio checks the process
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD if [ "$ORACLE_MCP_SERVER_TRANSPORT" = "http" ] || [ "$ORACLE_MCP_SERVER_TRANSPORT" = "sse" ] || [ "$ORACLE_MCP_SERVER_TRANSPORT" = "streamable-http" ]; then \
            curl -f "http://localhost:${ORACLE_MCP_BIND_PORT}/health" || exit 1; \
        else \
            pgrep -f "[o]raviz-mcp" || exit 1; \
        fi

# Entrypoint
ENTRYPOINT ["oraviz-mcp"]

# OCI labels for metadata
LABEL org.opencontainers.image.title="Oracle Viz MCP Server" \
      org.opencontainers.image.description="Minimal, visualization-first Model Context Protocol server for Oracle AI Database: compact read-only queries, table profiling, and PNG chart rendering for AI assistants" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.authors="jasperan" \
      org.opencontainers.image.url="https://github.com/jasperan/oraviz-mcp" \
      org.opencontainers.image.source="https://github.com/jasperan/oraviz-mcp" \
      org.opencontainers.image.documentation="https://github.com/jasperan/oraviz-mcp/blob/main/README.md" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="jasperan" \
      io.mcp.server.name="oraviz-mcp" \
      io.mcp.server.version="0.1.0" \
      io.mcp.server.transport="stdio,http,sse,streamable-http"
