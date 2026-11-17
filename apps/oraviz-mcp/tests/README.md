# Tests for Oracle Viz MCP

This directory contains the test suite for the Oracle Viz MCP server.

## Test Structure

- `conftest.py` - adds `src/` to `sys.path` so tests import the installed-from-source package
- `test_config.py` - configuration dataclasses, env parsing, transports
- `test_validation.py` - SQL guard, identifier validation, value formatting, context-engineered rendering
- `test_charts.py` - chart rendering for every chart type (no database required)
- `test_server_tools.py` - every MCP tool with `python-oracledb` mocked (success + failure paths)
- `test_main.py` - entry point, environment validation, transport selection
- `integration/test_oracle_integration.py` - live tests against a real Oracle AI Database (skipped by default)

## Running Tests

```bash
# Install the development dependencies if not already installed
uv sync --extra dev

# Run the whole unit suite (coverage is configured in pyproject.toml)
uv run pytest

# Run a single file
uv run pytest tests/test_server_tools.py -v

# Run one test
uv run pytest tests/test_charts.py::TestRenderChart::test_all_types_render_png
```

## Live integration tests

The integration tests need a real Oracle AI Database. A local 26ai Free container works:

```bash
docker run -d --name oraviz-oracle -p 1530:1521 \
  -e ORACLE_PWD=OraViz2026 container-registry.oracle.com/database/free:latest

export ORAVIZ_TEST_DSN=localhost:1530/FREEPDB1
export ORAVIZ_TEST_USER=oraviz
export ORAVIZ_TEST_PASSWORD=OraViz2026
uv run pytest tests/integration -v --no-cov   # --no-cov: the unit suite owns the coverage gate
```

Without `ORAVIZ_TEST_DSN` the integration module is skipped, so plain `uv run pytest` stays hermetic.

## Coverage

The suite aims to cover:

1. Configuration validation and environment parsing
2. Read-only query enforcement and identifier validation
3. Compact, bounded result rendering (the context-engineering contract)
4. Every tool's success and failure paths, with the database mocked out
5. Chart rendering for every supported chart type and its validation errors
6. The entry point's environment checks and transport selection
