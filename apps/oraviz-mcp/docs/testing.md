# Oracle Viz MCP Testing Guide

This document describes how the Oracle Viz MCP server is tested.

## Testing Philosophy

1. **Hermetic by default** - the unit suite never touches a database; `python-oracledb` is mocked.
2. **Live proof on demand** - integration tests run real SQL against a real Oracle AI Database and are skipped unless `ORAVIZ_TEST_DSN` is set.
3. **Both paths per tool** - every tool has success and failure tests (guards, missing objects, database errors).
4. **The context contract is tested** - result rendering is asserted to stay compact and bounded.

## Test Structure

### Unit tests (no database)

- `tests/test_config.py` - `OracleConfig`, `MCPServerConfig`, transport enum, env parsing
- `tests/test_validation.py` - read-only SQL guard, identifier validation, row caps, value formatting, `render_rows`
- `tests/test_charts.py` - every chart type plus its validation errors (Agg backend, headless)
- `tests/test_server_tools.py` - all seven MCP tools against a scripted fake cursor
- `tests/test_main.py` - environment validation and transport selection
- `tests/test_transport_security.py` - fail-closed network configuration and JWT verification
- `tests/test_query_security.py` - conservative SQL admission, bounded outputs,
  unread LOBs, strict wire arguments, and sanitized database failures
- `tests/test_tool_policy.py` - tool allowlisting, strict calls, admission, and sanitized audit records
- `tests/test_devcontainer.py` - installer command/line/interpolation injection, private files,
  existing-file preservation, and fatal ownership failures (no root, Docker, or network needed)

### Integration tests (live Oracle)

- `tests/integration/test_oracle_integration.py` - creates a scratch table, then exercises
  `execute_query`, `list_tables`, `get_table_schema`, `sample_table_data`, `get_table_details`,
  `profile_table`, `create_chart`, the write guard, and a `VECTOR(4, FLOAT32)` round trip.
- `tests/integration/test_security_boundary.py` - provisions uniquely named synthetic
  owner/reader accounts in an explicitly selected local container; verifies that
  Oracle itself denies writes, locks, ungranted reads, and table creation even
  when connector SQL validation is bypassed. Removes only its generated accounts.

## Running the Suite

```bash
# Everything hermetic (unit + skipped integration), with coverage
uv sync --extra dev
uv run pytest

# One file or one test
uv run pytest tests/test_server_tools.py -v
uv run pytest tests/test_charts.py::TestRenderChart::test_all_types_render_png

# Focused security/installer checks (coverage gate belongs to the full suite)
uv run pytest tests/test_transport_security.py tests/test_tool_policy.py tests/test_devcontainer.py --no-cov
bash -n devcontainer-feature/oraviz-mcp/install.sh

# Live integration: provision the disposable local database using README Quick Start.
# The fixture creates and drops scratch tables, so use the setup/test owner, not
# the MCP reader account. These test-only write grants are not deployment guidance.
export ORAVIZ_TEST_DSN=localhost:1530/FREEPDB1
export ORAVIZ_TEST_USER=oraviz
read -rsp 'Disposable test owner password: ' ORAVIZ_TEST_PASSWORD
export ORAVIZ_TEST_PASSWORD
uv run pytest tests/integration -v --no-cov
unset ORAVIZ_TEST_PASSWORD

# Optional permission-boundary tests: this must be a disposable local Oracle
# container with FREEPDB1. Provisioning uses its local OS-authenticated SYSDBA.
# Never select a production container. No privileged MCP credentials are needed.
export ORAVIZ_SECURITY_CONTAINER=oraviz-oracle
uv run pytest tests/integration/test_security_boundary.py -v --no-cov
unset ORAVIZ_SECURITY_CONTAINER
```

Coverage is configured in `pyproject.toml` (`fail_under = 90`); the unit suite is what owns that gate.
Run integration-only sessions with `--no-cov` so the partial run does not trip it.

## Security validation before deployment

Hermetic tests verify application behavior with fake database connections and synthetic
tokens. They do not prove database grants, TLS, network isolation, IdP policy, or recovery.
In an isolated environment, verify that:

- The dedicated reader can query the approved demo objects but cannot modify them, lock them,
  query an ungranted object, or execute an unapproved package. Inspect direct, inherited, and
  `PUBLIC` privileges; an account name is not proof of least privilege.
- Every HTTP/SSE entry path rejects missing/invalid/expired/wrong-audience tokens, missing/empty signed
  subjects, and missing scopes,
  including through the actual gateway. Check OAuth discovery against the configured public URL.
- Disabled tools disappear from discovery and direct invocation is denied. Oversized inputs,
  output limits, and excess concurrent calls fail safely; ordinary chart and metadata calls still work.
- Secured collectors receive request IDs and outcomes without SQL, tokens, DSNs, or raw errors.
  Verify Oracle session correlation and separately configured Unified Auditing.
- Gateway rate/body/time limits, private ingress, restricted egress, and process/database resource
  budgets work under load. Multi-round-trip and chart work can outlast `ORACLE_CALL_TIMEOUT`.
- The host enforces approval for sensitive reads/exports, isolates user state, and treats prompt-like
  database content as data. Exercise credential/scope revocation, a version rollback, and restoration
  from backups; record the tested version and evidence without secrets.

The deployment control inventory and limitations are in [SECURITY.md](../SECURITY.md).
Historical benchmark results are not current security test evidence. Do not overwrite
their measurements when running regression checks.

## Mocking Approach

`tests/test_server_tools.py` defines `FakeCursor`/`FakeConnection` helpers. Each `execute()` pops the
next scripted step (`description`, `rows`, `one`, or `raise`), which lets a test drive multi-query flows
(such as `get_table_details`' view fallback or `profile_table`'s metadata-then-aggregate) without a database.

## Adding New Tests

1. Add unit tests for the new behavior first, including the failure path.
2. Keep database access behind the `db`/`configured` fixtures in the integration module.
3. If a new tool returns rows, assert that its output stays compact (metadata line + markdown table).

## Continuous Integration

CI — `.github/workflows/ci.yml`, running the unit suite with coverage on Python 3.12, a distribution
build, and a Docker image build so the container path is exercised too — lives in the standalone
[oraviz-mcp](https://github.com/jasperan/oraviz-mcp) repository. This repository does not accept changes
under `.github`, so in this copy run the commands above locally.
