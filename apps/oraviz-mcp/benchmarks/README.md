# Token benchmark: oraviz-mcp vs. the official Oracle SQLcl MCP server

Script: [`run_benchmarks.py`](run_benchmarks.py) ·
Raw results: [`results/benchmark-results.json`](results/benchmark-results.json) ·
Recorded table: [`results/benchmark-results.md`](results/benchmark-results.md)

**Historical snapshot:** these measurements and charts predate the security
hardening. Values are preserved unchanged; the current tool schemas, validation,
LOB behavior, and limits can change token counts. These are not current security or
performance guarantees. See [SECURITY.md](../SECURITY.md) for current controls.

## What is measured

Both servers answer the same five questions against the same Oracle AI Database
(26ai Free) with the same demo data, and the harness counts the tokens of every
piece of text an agent must process to arrive at the answers:

- **tool schemas** -- the `tools/list` payload (name, description, input schema
  per tool), read once per session;
- **tool results** -- every text block returned by a tool call;
- **total** -- schemas + results for the whole workflow.

Counts are produced with `tiktoken` (`cl100k_base`; `o200k_base` is in the
JSON) as a tokenizer proxy. Chart images are a different modality, so the
chart step is measured on its text summary and reported separately, not in
the savings math.

The five questions (identical SQL where SQL is used):

1. list the schema objects
2. describe `SALES_DEMO`
3. aggregate revenue by region for the last 6 months
4. sample 10 rows
5. fetch the full 96-row table (the context-blow-up case)

oraviz-mcp answers with its own tools. SQLcl MCP answers with
`schema-information` and `run-sql` -- the path an agent actually has, because
its `connect` tool only accepts saved connections, so connecting goes through
`run-sqlcl` (counted as SQLcl-only setup).

## Results (cl100k_base tokens)

Negative savings mean the official server used fewer tokens for that step; they occur only on
small result sets, where markdown framing is heavier than raw CSV.

| Question | oraviz-mcp | sqlcl-mcp | Savings |
|---|---:|---:|---:|
| list objects | 69 | 354 | 80.5% |
| describe table | 143 | 93 | -53.8% |
| aggregate revenue by region | 63 | 40 | -57.5% |
| sample 10 rows | 375 | 242 | -55.0% |
| raw 96-row dump | 825 | 2136 | 61.4% |

| Aggregate | oraviz-mcp | sqlcl-mcp | Savings |
|---|---:|---:|---:|
| Tool schemas (read once per session) | 862 | 2139 | 59.7% |
| Tool results to answer the questions | 2337 | 5004 | 53.3% |
| Total | 2337 | 5006 | 53.3% |
| sqlcl-only setup (connect step) | 0 | 2 | 100.0% |

Capability add-on: rendering the aggregate as a bar chart costs 123 text
tokens plus the PNG image. SQLcl MCP has no chart tool.

With `o200k_base` the numbers move by less than one point: 2334 vs 4989
tokens, 53.2% total savings.

## Interpretation

- **Tool schemas: 59.7% cheaper.** Seven small, single-purpose tools beat seven
  general-purpose tool definitions with long descriptions and `model` /
  `executionType` parameters. Every agent session pays this cost before any
  work starts.
- **Discovery: 80.5% cheaper.** `list_tables` returns exactly the tables and
  views; SQLcl's `schema-information` also answers questions nobody asked
  (indexes, LOB segments, sequences, a DDL outline) and pays for them in
  context.
- **Wide result sets: 61.4% cheaper.** The preview cap plus the explicit
  `truncated` marker turns the 96-row dump into 25 rows of compact markdown;
  SQLcl returns the full formatted result and the agent pays for every row.
- **Small result sets cost ~55% more.** Markdown framing (header, divider,
  padding) is heavier than SQLcl's CSV for tiny payloads like a 10-row sample.
  That overhead is bounded by design: it cannot grow with the result size,
  while the unprotected dump cost grows with every row.
- **Net: 53.3% fewer tokens for the whole workflow** -- and the workflow parts
  that blow up most (schemas, discovery, unfiltered dumps) are exactly where
  the savings are largest.

## Reproduce

```bash
# 1) Isolated Oracle 26ai Free container + disposable demo owner (see README Quick Start)
# 2) SQLcl 26.1 available (SQLCL_BIN=/path/to/sql) and the dev extra installed
read -rsp 'Disposable benchmark owner password: ' ORAVIZ_BENCH_PASSWORD
export ORAVIZ_BENCH_PASSWORD
uv run --extra dev python benchmarks/run_benchmarks.py \
  --dsn localhost:1530/FREEPDB1 --user oraviz
unset ORAVIZ_BENCH_PASSWORD
```

Environment overrides: `ORAVIZ_BENCH_DSN`, `ORAVIZ_BENCH_USER`,
`ORAVIZ_BENCH_PASSWORD`, `SQLCL_BIN`. Results are written to
`benchmarks/results/`. The harness has legacy demo defaults: always override the password.
Reproduce in a separate checkout at the recorded revision to preserve committed evidence;
running the current code produces a new experiment, not the historical snapshot.

This legacy comparison uses the disposable owner because SQLcl creates its audit table and
the harness queries owner-local metadata. It does not represent the production reader-account
deployment. SQLcl receives connection credentials as part of benchmark setup; keep the entire
run, subprocess traces, and artifacts private and never use real service credentials.

## Limitations

- `tiktoken` is a proxy, not the tokenizer of a specific agent model; relative
  comparisons are stable (cl100k and o200k agree within ~2 points).
- One scenario set against one demo schema; per-step ratios depend on result
  shapes. The aggregate step is deliberately small so the markdown-overhead
  case is visible.
- SQLcl MCP writes an audit table (`DBTOOLS$MCP_LOG`) into the connected
  schema on first use; it exists for both servers' sessions, so the
  comparison stays symmetric.
- SQLcl output formats dates using the database NLS format (`01-OCT-25`);
  oraviz renders ISO-8601 (`2025-10-01`). Neither choice is scored.
