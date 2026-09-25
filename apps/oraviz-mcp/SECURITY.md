# Security and deployment

OraViz exposes seven query, discovery, profiling, and chart tools. It has no write
tools. Reads can still disclose sensitive data, consume database resources, and
carry prompt injection. Database grants, deployment controls, and the MCP host's
policy are required alongside the server's checks.

This deployment guidance applies the principles in [Google Cloud's MCP security
guidance](https://docs.cloud.google.com/mcp/ai-security-safety) and the [NSA's MCP
security design considerations](https://www.nsa.gov/Portals/75/documents/Cybersecurity/CSI_MCP_SECURITY.pdf).
It is not a certification or a claim that all recommendations are implemented.
Choose managed or self-hosted services according to verified controls, operating
capacity, data boundaries, and recovery requirements; either needs review.

## Trust and identity boundaries

- **Stdio:** the local operating-system account, MCP host, and child-process
  environment form the trust boundary. Run under a dedicated account; protect
  client configuration, credentials, and wallet files. Do not bridge stdio to a
  network listener to bypass authentication.
- **HTTP, streamable HTTP, and SSE:** network MCP entry points require bearer
  authentication. Missing or invalid auth configuration fails closed, including
  direct application use. Tokens must have a valid RS256 signature, the configured
  issuer and audience, an expiry, a nonempty signed `sub`, an applicable `nbf` if
  present, and every required scope. Invalid tokens are rejected; insufficient scopes are denied. `/health`
  is a minimal liveness response, not proof of database access or authorization.
- **Oracle:** every HTTP identity uses the same configured database principal.
  JWT identity is audit context, not per-user database authorization. This server
  does not provide tenant isolation or map scopes to rows. Deploy a separate
  instance and dedicated database account for each agent or trust domain that
  needs different data access. Keep host memory and conversations isolated too.

Grant `CREATE SESSION` and object-level `READ` only on approved tables or reviewed
views. Oracle's [`READ` privilege](https://docs.oracle.com/en/database/oracle/oracle-database/26/dbseg/configuring-privilege-and-role-authorization.html)
does not grant `SELECT ... FOR UPDATE` or explicit table-locking privileges, while
`SELECT` can. Do not grant `DBA`, `RESOURCE`, `SELECT ANY TABLE`, `READ ANY TABLE`,
write privileges, or unnecessary package execution. Inspect inherited roles,
`PUBLIC` grants, synonyms, views, and functions as well as direct grants. Known
administrative account names are rejected, but renaming a privileged account does
not make it safe. See the [reader-account demo](README.md#quick-start).

## Server controls and limits

| Control | Behavior |
|---|---|
| Tool policy | `ORACLE_MCP_ALLOWED_TOOLS` is a comma-separated list of exact names: `execute_query`, `list_tables`, `get_table_schema`, `sample_table_data`, `get_table_details`, `profile_table`, `create_chart`. Unset enables these seven. Empty values, empty entries, or unknown names reject startup. Disabled tools are hidden and direct calls are denied. Restart to apply changes. |
| Input validation | Strict tool schemas bound SQL, identifiers, row counts, column lists, and chart labels. Arguments are limited to 65,536 serialized UTF-8 bytes; this is not an HTTP body limit. |
| SQL admission | At most 32,000 characters, one `SELECT`/`WITH`, conservative built-in function allowlist. The guard rejects unreviewed function calls with parentheses, writes, PL/SQL, database links, sequences, and locking constructs. |
| Rows and cells | Defaults: 25 preview rows, 500 maximum rows, 500 characters per cell. Configurable maxima: 5,000 rows and 4,096 characters per cell. Preview size is also limited by the row cap. |
| Columns and output | Default 64 result columns, maximum 200. The sum of text content and serialized JSON structured content is limited to 256,000 characters per MCP tool response. Mirrored data counts in both representations. Over-limit responses are rejected, even if a table was already truncated by the renderer. PNG output is limited to 2,000,000 bytes before base64 encoding. |
| Large objects | Raw CLOB/NCLOB/BLOB/BFILE locators are never read; they render as `<LOB>`. Vectors and binary values are summarized. |
| Database timeout | `ORACLE_CALL_TIMEOUT` defaults to 60 seconds, valid range 1–300; it cannot be disabled. It is converted to milliseconds for the driver's timeout on each database round trip. |
| Admission | `ORACLE_MCP_MAX_CONCURRENT` defaults to 4, valid range 1–32, per server process. Excess calls are rejected without an admission queue. |

Invalid numeric environment settings fall back to bounded defaults with a warning;
they do not disable the limits. Review startup warnings. An explicitly invalid
tool allowlist or network auth setting instead prevents startup.

The SQL guard is lexical, not a full Oracle parser or proof of no side effects.
It cannot detect bare parameterless routine references such as
`SELECT some_function FROM dual`, or routines reached indirectly through views or
synonyms. `READ` grants alone do not deny routines executable through `PUBLIC`
or inherited `EXECUTE` privileges. Review these grants and object definitions;
database permissions remain mandatory. A row cap limits fetched
data, not the work of an aggregate, sort, join, or exact count. The driver's
[`call_timeout`](https://python-oracledb.readthedocs.io/en/latest/api_manual/connection.html#Connection.call_timeout)
limits a single round trip, not an entire statement or tool invocation. Multi-query
profiling, fetches, and chart rendering may take longer in total. Request
cancellation does not establish a hard deadline for synchronous database work.

## Network deployment

Use the following as environment configuration with operator-chosen endpoints;
the `.example` names are placeholders, not a working identity provider:

```dotenv
ORACLE_MCP_SERVER_TRANSPORT=streamable-http
ORACLE_MCP_BIND_HOST=127.0.0.1
ORACLE_MCP_BIND_PORT=8080
ORACLE_MCP_AUTH_ISSUER=https://idp.example/realms/agents
ORACLE_MCP_AUTH_AUDIENCE=oraviz-mcp
ORACLE_MCP_AUTH_JWKS_URL=https://idp.example/realms/agents/protocol/openid-connect/certs
ORACLE_MCP_AUTH_REQUIRED_SCOPES=oraviz:read
ORACLE_MCP_AUTH_BASE_URL=https://mcp.example/oraviz
ORACLE_MCP_ALLOWED_TOOLS=list_tables,get_table_schema,create_chart
ORACLE_MCP_MAX_CONCURRENT=4
```

Required scopes are **space-separated** and apply to all enabled tools. The
optional HTTPS `ORACLE_MCP_AUTH_BASE_URL` enables OAuth resource discovery; include
the reverse-proxy mount prefix but omit `/mcp` or `/sse`. Configure clients and the
identity provider to issue short-lived access tokens for this resource. OraViz is
a token verifier, not a token issuer, and does not forward tokens to Oracle.

Terminate TLS at a trusted gateway and restrict the backend to that gateway on a
private network. Network auth remains mandatory behind a proxy and on loopback.
For containers, bind within the container as needed but publish only to loopback
or the private gateway network. Encrypt database connections with Oracle TLS/mTLS
and protect wallets. Restrict runtime egress to the approved database listener and
IdP/JWKS endpoints, with only required infrastructure such as controlled DNS.

Set gateway request-body, connection, rate, and request/idle-time limits, plus
container CPU, memory, and process budgets. Account for SSE connections and base64
image expansion when choosing limits. Configure database resource management for
costly queries. Concurrency is per process; multiple replicas multiply capacity.
Gateway disconnection alone cannot stop a database worker. Test limits under load.
These controls are operator configuration, not infrastructure installed by OraViz.

## Host policy, prompt injection, and secrets

Treat database rows, metadata, chart labels, and all other tool outputs as
untrusted data. Keep them separate from system instructions; never turn returned
text into commands for another tool. Review tool sources, pin versions or commit
IDs and container digests, and review schema/tool changes before upgrades. Restrict
tools in both the host and server. Content screening can complement these controls;
no detector, delimiter, or system instruction prevents every prompt injection.

The MCP host must enforce human approval for sensitive reads, exports, and onward
transfers according to the organization's policy. There is no server-side approval
workflow or write tool here. A model-supplied `approved=true` is not evidence of
human approval. Check the actual data scope and destination before authorizing
disclosure, and minimize what enters model context and memory.

Inject credentials through a protected runtime environment or secret store. Do
not put them in prompts, URLs, shell command arguments, repository files, images,
or committed client settings. Local `.env` files need owner-only permissions and
must not be sourced as shell scripts. Be aware of `${...}` interpolation in dotenv
consumers; inject such literal values through the process environment. Rotate
database credentials and IdP keys under a tested procedure.

## Audit and incident response

Each MCP tool call produces JSON audit records on stderr before and after execution,
including a generated request ID, known tool name, verified token identity or local
OS identity, configured database user, outcome, and elapsed time. Oracle sessions
set `module=oraviz-mcp` and `client_identifier` to the request ID for correlation.
SQL, bind values, result data, credentials, tokens, DSNs, and raw database error
messages are excluded from application audit records. Tool errors use sanitized
messages with a request ID. Identity metadata may itself be sensitive.

Forward stderr through a secured collector with access control, retention,
integrity protection, and alerts for denials, unusual volume, and failures. Capture
gateway/IdP authentication failures separately: requests rejected before the tool
pipeline do not have tool-call audit records. Check framework, proxy, host, and
database logging for accidental secret capture. Configure and verify Oracle
Unified Auditing separately; session tags and JSON logs do not enable it. Audit
delivery, durable storage, retention, and alerts are not provided by this server.

Before rollout, record the approved version, grants, tool policy, auth configuration,
and owners; validate backup restoration and incident response in an isolated
environment. On an incident, isolate the endpoint, revoke scopes and access tokens
at the IdP (accounting for already-issued JWT lifetime and key caches), rotate or
revoke database credentials/grants, and preserve protected logs. Offline JWT
verification does not guarantee immediate token revocation; stopping access at
the gateway or stopping the service may be necessary. Roll back to a reviewed
version with its compatible configuration, revalidate access boundaries, and
restore data only through the approved recovery process. OraViz does not change
infrastructure, configure backups, restore data, or perform rollback automatically.

## Reporting a vulnerability

Use the repository's [private vulnerability report](https://github.com/jasperan/oraviz-mcp/security/advisories/new)
when available. If it is unavailable, request a private contact route from the
maintainer without disclosing exploit details publicly. Include affected versions,
a minimal reproduction using synthetic data, and the expected boundary. Never
include credentials, bearer tokens, wallets, production SQL, or database contents.

The [benchmarks](benchmarks/README.md) and their result figures are historical
snapshots from before this hardening. They are not evidence that the current
deployment controls have been tested in production.
