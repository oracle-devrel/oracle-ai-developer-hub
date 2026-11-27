# FitTrack API Dockerfile
# Development image with hot-reload support

FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy files the build backend needs, then install Python dependencies
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --upgrade pip && \
    pip install -e ".[dev]"

COPY tests/ ./tests/

# Create non-root user
RUN useradd --create-home --shell /bin/bash fittrack && \
    chown -R fittrack:fittrack /app
USER fittrack

# Expose port
EXPOSE 8000

# Default command
CMD ["uvicorn", "fittrack.main:app", "--host", "0.0.0.0", "--port", "8000"]
