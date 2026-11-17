# Security considerations

## Prototype status

This Codex plugin is a tutorial prototype that demonstrates how to connect
Codex hooks and MCP tools to Oracle AI Agent Memory. It is not a production
authentication gateway or a complete multi-user service.

The example assumes:

- a trusted developer controls the local environment;
- the MCP server listens only on loopback;
- tokens are issued manually to trusted users;
- test or otherwise appropriate data is used;
- the database, embedding endpoint, and LLM endpoint are trusted; and
- untrusted users cannot call the MCP endpoint directly.

> [!IMPORTANT]
> These assumptions and the guidance in this document are not a security
> checklist and are not exhaustive. Do not deploy this example unchanged,
> even if the assumptions appear to hold. Any shared or production deployment
> needs its own threat model, architecture review, security testing, and
> operational review by appropriately qualified people.

The prototype includes a few baseline safeguards: it validates signed token
expiry and required identity claims, derives stored thread identifiers from the
authenticated user and agent scope, verifies ownership when reopening a
thread, restricts the example server to loopback addresses, and gives hook HTTP
requests finite connection and response timeouts. These controls reduce risk
for the documented local use case; they do not provide production-grade
identity management, tenant isolation, revocation, or abuse prevention.

## Data handled by the prototype

After the bundled hooks are reviewed and trusted, the plugin sends each
submitted user prompt and final assistant message to the configured MCP
server. The server can persist that content in Oracle Database and can send
content to configured embedding or LLM endpoints as part of memory processing.

Prompts and responses can contain source code, credentials, personal data,
customer information, or other sensitive material. Use only data appropriate
for the configured database and model providers. Minimize or redact sensitive
content before it enters the memory pipeline.

Stored messages, retrieved memories, summaries, and extracted memories are
untrusted application data. They can contain persistent prompt-injection
content and must not authorize privileged actions or override application
policy.

The plugin configuration exposes `search` and `add` for model use. The
`add_messages` tool is registered so the hook can capture messages, but is not
enabled for model use by this plugin. That client-side tool selection is only a
presentation boundary, not an authorization boundary: another MCP client that
can reach the server could request any registered tool. The server therefore
continues to authenticate every request and enforce the user, agent, and
thread scope for hook writes.

## Starting points for a deployment security review

The topics below are starting points only. They are deliberately not a
definitive deployment checklist and satisfying them does not establish that a
system is secure or production-ready. Review the complete architecture,
deployment environment, data flows, dependencies, and applicable Oracle and
platform security documentation.

### Authentication and authorization

- Replace the example token workflow with an authentication design appropriate
  for the deployment, such as MCP-compatible OAuth 2.1.
- Derive user and tenant identity from authenticated context, not request data.
- Enforce user, agent, and thread ownership on every read and write.
- Assign a dedicated memory store to each application and environment; keep its
  identifier (at most 16 characters) under operator control rather than
  accepting it from users.
- Use separate scopes or permissions for searching, adding memory, and
  capturing messages.
- Use short-lived credentials with rotation and revocation.
- Consider database-enforced authorization such as Oracle Deep Data Security
  when multiple end users share a database-backed deployment.

Oracle AI Agent Memory scope identifiers are filtering values, not proof of
identity. The integrating service remains responsible for authentication and
authorization.

### Data governance

- Decide which prompts, responses, metadata, embeddings, and derived memories
  may be stored.
- Define retention, expiration, export, and deletion behavior for both raw and
  model-derived records.
- Obtain any consent required for automatic message capture.
- Review the retention and data-use policies of database, embedding, and LLM
  providers.
- Do not treat memory as an authoritative system of record.

### Network and secrets

- Use HTTPS for remote MCP and model endpoints.
- Configure MCP Host and Origin validation.
- Use encrypted Oracle Database connections.
- Store database passwords, API keys, and signing keys in a managed secret
  store rather than source files.
- Use least-privilege database and service credentials, separating schema
  administration from runtime access.

### Abuse resistance and operations

- Apply request-size limits, rate limits, quotas, timeouts, and concurrency
  controls.
- Bound message sizes, result counts, storage growth, and model consumption.
- Avoid logging tokens, prompts, memory content, personal data, or raw
  identifiers.
- Monitor authentication failures, denied cross-scope access, database growth,
  provider usage, and repeated hook failures.
- Pin and review dependencies, maintain a lockfile, and run dependency and
  secret scanning in CI.
