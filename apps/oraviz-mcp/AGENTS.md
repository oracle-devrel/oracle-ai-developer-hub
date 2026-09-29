# AGENTS.md — oraviz-mcp

Guidance for coding agents working in this repository.

## What this is

oraviz-mcp is a minimal, visualization-first MCP server for Oracle AI Database.
Seven tools cover bounded query execution, schema introspection, profiling, and
PNG chart rendering. The defining property is the **context contract**: every
tool result is bounded by configuration (rows, cell size, statement timeout) and
reports its own truncation instead of silently dumping data.

User-facing story: `README.md`. Token benchmark against the official SQLcl MCP
server: `benchmarks/`. Showcase site: `docs/` (GitHub Pages).

## Layout

```
src/oraviz_mcp/server.py   FastMCP app, config, Oracle client, validation, the 7 tools
src/oraviz_mcp/charts.py   pure chart rendering (bar/line/area/scatter/pie/histogram/vector -> PNG)
src/oraviz_mcp/main.py     entry point: env validation, transport selection
src/oraviz_mcp/query_policy.py     conservative SQL admission rules
src/oraviz_mcp/tool_policy.py      tool allowlist, input/output budgets, audit events
src/oraviz_mcp/transport_security.py  required JWT authentication for network transports
tests/                     hermetic unit tests (fake cursor) + tests/integration/ (live Oracle)
benchmarks/                token benchmark harness + results JSON/MD
docs/                      GitHub Pages site (index.html/styles.css/app.js) + testing.md
examples/demo-sales.sql    demo schema (96-row SALES_DEMO + PRODUCT_VECTORS)
```

## Commands

```bash
uv sync --extra dev                     # install (adds pytest, tiktoken for the benchmark)
uv run pytest                           # unit suite; keeps a 90% coverage gate (currently ~98%)
uv run pytest -k chart                  # focused subsets work as usual

# Live integration tests (Oracle 26ai Free container, see README Quick Start)
ORAVIZ_TEST_DSN=localhost:1530/FREEPDB1 ORAVIZ_TEST_USER=oraviz \
ORAVIZ_TEST_PASSWORD=OraViz2026 uv run pytest tests/integration -v --no-cov

# Token benchmark vs the official SQLcl MCP server (needs SQLcl 26.1)
uv run --extra dev python benchmarks/run_benchmarks.py \
  --dsn localhost:1530/FREEPDB1 --user oraviz --password OraViz2026 \
  --sqlcl /path/to/sqlcl/bin/sql          # writes benchmarks/results/

# Showcase site
python3 -m http.server 8123 --directory docs                     # preview the site locally
```

## Contracts you must not break

- **Context contract.** Every row-returning tool renders via `render_rows`
  (one metadata line, markdown header, escaped cells) and is bounded by
  `ORACLE_MCP_MAX_ROWS` / `ORACLE_MCP_PREVIEW_ROWS` / `ORACLE_MCP_MAX_CELL_CHARS`,
  with a timeout per database round trip (`ORACLE_CALL_TIMEOUT`, python-oracledb
  `call_timeout` in **milliseconds**, not a whole-statement deadline). Tests assert the metadata line, the
  truncation flag, cell escaping, and value formatting; change tests and docs
  together with any behavior change.
- **Tool surface.** Keep it at seven single-purpose tools. New capability means
  a new server or an explicit decision, not tool number eight with a 40-line
  schema.
- **stdout is the stdio transport.** All logging goes to stderr (structlog,
  JSON by default). Never `print()`.
- **Values in, constants out.** SQL values are always bound; identifiers are
  validated then quoted; numeric limits only ever interpolate validated ints.
- **Escaping everywhere.** `_escape_text` applies to cell values and column
  names so tables cannot be broken by data.
- **Security boundaries.** All network transports require verified scoped tokens,
  even behind a proxy. Preserve the denying provider on unconfigured stdio apps
  so programmatic transport overrides cannot expose them. Tool policy is an
  immutable operator allowlist; disabled tools cannot be called by guessing names.
- **Audit privacy.** Never log SQL, arguments, tokens, credentials, DSNs, results,
  or raw database errors. Preserve per-call JSON audit events on stderr and
  request IDs in Oracle session tags. See `SECURITY.md` for deployment duties.

## Conventions

- Conventional commits (`fix:`, `feat:`, `docs:`, ...), imperative subject under
  72 chars, body explains why. No AI attribution in commits.
- README claims must match behavior; if you change a guarantee, update README,
  CHANGELOG, and the benchmark text that cites it.
- Add tests with every behavior change; live tests are opt-in via
  `ORAVIZ_TEST_DSN` and must run with `--no-cov` (the coverage gate belongs to
  the unit suite).
- No new runtime dependencies unless justified; benchmark tooling (tiktoken)
  belongs to the dev extra; one-off tooling runs via `uv run --with`.

## Gotchas

- The bind name `:table` is reserved in Oracle — use `:table_name`.
- Do **not** reintroduce `SET TRANSACTION READ ONLY`: it raises ORA-01466 for
  tables created or modified shortly before the query (including our own demo
  data), which breaks the normal create-then-query workflow. The lexical guard
  restricts syntax; it cannot prove read-only semantics. Use a dedicated account
  with object-level READ grants and review inherited/PUBLIC routine privileges.
- Raw LOB locators must never be read. Keep the output type handler and `<LOB>`
  marker; do not materialize large objects just to truncate them afterward.
- `charts.py` must stay pyplot-free (`Figure` + `FigureCanvasAgg`): tool calls
  run on a worker pool and pyplot is not thread-safe.
- SQLcl MCP's `connect` tool only accepts saved SQLcl connections; the
  benchmark connects through `run-sqlcl` with a connect string instead.
- The demo credentials in README/benchmark defaults (`oraviz` / `OraViz2026`
  on port 1530) belong to a throwaway container. Do not reuse them anywhere
  real, and do not commit `.env`.
- The Docker job publishes to GHCR on every push to `main`; `server.json`
  advertises the image, so keep tags and versions aligned when bumping.
- Skill/config files under `~/.config/crush/` (the user's agent setup) are
  outside this repo; this file is the authority for work inside the repo.
