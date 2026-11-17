# MCP security hardening and validation

Validated locally on 2026-09-22, using Python 3.12, FastMCP 4.0.3,
python-oracledb 26.0.0, and an isolated Oracle AI Database 26ai Free container.

Scope: adopt the controls described in the Google Cloud MCP security guidance,
the NSA MCP design guidance, and the accompanying business-data blog.

1. Keep seven tools and reuse existing configuration, validation, and rendering.
2. Require validated authentication for every network transport; preserve local
   stdio's operating-system identity boundary.
3. Add a startup tool allowlist, strict bounded arguments, and conservative SQL
   validation. Database grants remain the authoritative access boundary.
4. Record correlated audit events without SQL, results, tokens, or passwords.
5. Bound result handling, protect error responses, and label returned data as
   untrusted content for the consuming agent.
6. Document deployment responsibilities for identities, human approval,
   database policies, private networking, TLS, log retention, and recovery.
7. Add regression tests, run the coverage suite and build, review the final
   diff, then commit and push as requested.

The implementation preserves seven tools and adds no runtime dependencies.
Historical benchmark results remain intact and are labeled as measurements of
the earlier implementation. The complete deployment contract is in
[SECURITY.md](../SECURITY.md).

## Verified boundaries

- Network entry points deny missing, malformed, expired, wrong-issuer,
  wrong-audience, unsigned, and insufficiently scoped tokens. Tests use locally
  generated signing keys and mocked JWKS retrieval, not a production IdP.
- Disabled tools are hidden and denied; strict argument schemas reject coercion,
  extra fields, excessive sizes, and unsupported SQL before opening a connection.
- Tool auditing correlates caller identity and Oracle session tags without query
  text, values, result data, credentials, or raw database exceptions.
  Authenticated SSE malformed-message regressions and streamable-HTTP body-read
  failures also verify that SDK transport logs are sanitized before tool middleware.
- Row, column, cell, text/JSON, image, vector-dimension, and concurrency limits
  are exercised. Raw LOB locators are not read. MCP cancellation retains a busy
  synchronous worker's admission slot until its work finishes.
- Live tests bypass connector SQL validation and confirm Oracle denies writes,
  locks, ungranted reads, and table creation for a synthetic reader with only
  `CREATE SESSION` and a reviewed object's `READ` grant. The test fixture removes
  its uniquely named users and synthetic tables; other database objects remain.
- The devcontainer installer treats inputs as data, refuses existing credential
  files, and creates owner-only files. Installer tests mock Git and ownership
  changes; they are not a full devcontainer installation.

## Reproduce

```bash
uv sync --frozen --extra dev
uv run pytest --cov-report=term-missing -q
uv build
bash -n devcontainer-feature/oraviz-mcp/install.sh
git diff --check
docker build -t oraviz-mcp:security-check .
```

For live checks, follow [docs/testing.md](testing.md); opt into only a disposable
local database. The final hermetic suite passed 521 tests with 17 live tests
skipped and 98.74% line coverage. The combined live integration suite separately
passed all 17 tests.
The wheel, source distribution, and container built successfully. A container
started in HTTP mode without auth configuration exited with code 1 and a
sanitized configuration error instead of opening an unauthenticated listener.
Network-isolated container smoke checks also verify `/health` returns 200 and
unauthenticated MCP access returns 401 for HTTP, streamable HTTP, and SSE.

## Not established by these checks

No production identity provider, TLS gateway, network policy, audit collector,
retention policy, host approval flow, backup restoration, or deployment rollback
was configured or certified. Shared database credentials do not isolate callers.
The lexical SQL guard cannot prove that a view, synonym, parameterless routine,
or inherited/PUBLIC execution privilege is harmless. Driver timeouts apply per
round trip, not to a whole tool invocation. Deployment owners must verify these
boundaries for their own infrastructure and data before rollout.
