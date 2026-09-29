# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security

- Network MCP transports now fail closed unless issuer, audience, HTTPS JWKS, and required scopes
  are configured. Bearer tokens require RS256 verification, expiry, a nonempty signed `sub`, and valid `nbf`; optional public
  HTTPS base URL enables discovery. Stdio retains local OS trust. Network identities share one
  configured Oracle principal; this is not per-user data authorization.
- Added `ORACLE_MCP_ALLOWED_TOOLS`, strict tool inputs, bounded serialized arguments, per-process
  concurrency admission, and metadata-only JSON call auditing with request IDs and Oracle session tags.
- Sanitized SDK transport logs before tool middleware runs, including SSE parse-error tracebacks
  and raw-body debug records; errors retain severity without exposing request payloads.
- Hardened SQL admission with a 32,000-character cap and conservative built-in function allowlist;
  unreviewed calls with parentheses, links, PL/SQL, sequences, and locking are denied. Bare parameterless
  routines and routines inside views/synonyms can evade lexical detection. Database `READ` grants and
  review of inherited/`PUBLIC` execution privileges remain essential.
- Bounded configuration now caps rows at 5,000, cell characters at 4,096, and result columns at 200
  (default 64). Combined text and serialized JSON structured content is limited to 256,000 characters
  per MCP response, counting mirrored data in both representations; oversized responses are rejected,
  even after table truncation. PNGs are limited
  to 2,000,000 bytes.
  Raw LOB locators are never read and render as `<LOB>`.
- Removed administrative Oracle account examples/defaults. The demo separates its setup owner from
  an `ORAVIZ_READER` account with `CREATE SESSION` and two object-level `READ` grants. Known admin
  account names are rejected; other accounts' grants still need operator review.
- The local Compose database binds to loopback and uses a separate admin-password variable.
  Devcontainer options are no longer evaluated as shell code; environment files are created privately,
  existing files are preserved, dotenv interpolation is rejected, and write/ownership failures are fatal.
- Added `SECURITY.md` covering deployment, host approvals, prompt injection, audit forwarding,
  resource limits, and recovery responsibilities. Benchmark figures remain unchanged
  historical snapshots from before hardening.

### Fixed

- `list_tables` and `get_table_schema` are bounded by `ORACLE_MCP_MAX_ROWS` with explicit truncation
  metadata, instead of fetching every row.
- Markdown column headers are escaped like cell values, so exotic identifiers cannot break the table.
- `get_table_schema` primary-key lookup is scoped by constraint owner, avoiding duplicate rows when
  another schema holds a same-named constraint.
- `profile_table` de-duplicates requested columns, no longer requests `MIN`/`MAX` for `LONG` columns
  (which Oracle rejects), and caps generated alias length for very long column names.
- `Decimal` values that a float cannot represent exactly (for example `NUMBER(38)` identifiers) are
  returned verbatim; raw LOB values are replaced with a marker without reading their contents.
- Docker healthcheck: the stdio probe no longer matches its own command line, and HTTP transports answer
  on a real `/health` route registered by the server.
- SQL, DSNs, credentials, and raw database error messages are excluded from application logs;
  MCP failures are sanitized before delivery to the host.

### Added

- `ORACLE_CALL_TIMEOUT` (default 60 s, range 1–300, cannot disable) sets python-oracledb `call_timeout`
  in milliseconds for each database round trip. It is not a whole-statement or whole-tool deadline.
- Non-positive values for the connect/max-rows/preview/cell env knobs now fall back to their defaults
  with a warning instead of flowing through as garbage.
- Token benchmark against the official Oracle SQLcl MCP server (`benchmarks/run_benchmarks.py` plus
  committed results): 53.3% fewer workflow tokens, 59.7% fewer on tool schemas, 80.5% on schema
  discovery, 61.4% on a wide result set.
- GitHub Pages showcase site in `docs/` (end-to-end query demo, benchmark summary, quick start) and
  `AGENTS.md` describing the repository for coding agents.
- `create_chart` gained a `vector` chart type: the first VECTOR column is projected to two dimensions
  with PCA (dense and sparse vectors, any dimension) and rendered as a labeled scatter, so 26ai embedding
  columns can be explored without leaving SQL. Chart rendering now imports `numpy` directly (previously
  only a matplotlib dependency) for the projection.

### Changed

- Removed the unused direct `mcp[cli]` dependency and raised the `fastmcp` floor to 4.0; CI installs with
  `uv sync --frozen` so lock drift fails fast.
- Chart rendering uses `Figure`/`FigureCanvasAgg` directly instead of pyplot, keeping concurrent
  `create_chart` calls safe on the worker-thread pool.

## [0.1.0] - 2026-09-14

### Added

- Minimal, visualization-first MCP server for Oracle AI Database (26ai Free included), modeled on
  [pab1it0/adx-mcp-server](https://github.com/pab1it0/adx-mcp-server).
- Tools: `execute_query`, `list_tables`, `get_table_schema`, `sample_table_data`, `get_table_details`,
  `profile_table`, `create_chart`.
- Context engineering: preview-capped results, one compact markdown table per result set with a metadata
  header, summarized large values (CLOB/BLOB/VECTOR), and per-column profiling instead of raw dumps.
- Chart rendering (bar, line, area, scatter, pie, histogram) to PNG via matplotlib, returned as MCP image
  content together with a short data preview.
- Read-only SQL enforcement, identifier validation, row and cell caps, and safe connection handling
  through python-oracledb thin mode (no Oracle client libraries required).
- stdio, http, sse, and streamable-http transports; structured JSON logging on stderr.
- Hermetic unit suite (~98% line coverage, gated at `fail_under = 90`) plus live Oracle integration tests.
- Packaging: Dockerfile (multi-stage, non-root), CI workflow, MCP registry `server.json`, Smithery config,
  dev container feature, and a ready-to-run demo schema in `examples/demo-sales.sql`.
