# Token benchmark: oraviz-mcp vs the official SQLcl MCP server

Generated: 2026-09-16T14:15:14.032942+00:00

Token counts use `tiktoken` (`cl100k_base`; `o200k_base` numbers are in the JSON).
Lower is better; savings are relative to the official SQLcl MCP server.
Negative savings mean the official server used fewer tokens for that step.

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

## Capability add-on (not part of the token race)

SQLcl MCP has no chart tool, so these steps cannot be compared; they are reported
for reference (image bytes are a different modality and are not counted as text tokens).

| Step | oraviz-mcp text tokens | sqlcl-mcp |
|---|---:|---:|
| chart the aggregate (result set to PNG) | 123 (+ PNG image) | n/a |

