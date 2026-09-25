# Security considerations

## Status and scope

This project is a learning example for OCI IAM application-mediated access,
Oracle Deep Data Security (Deep Sec), and Oracle AI Agent Memory. It is not a
production web service. Run it only on a dedicated development workstation and
against a dedicated non-production database.

The example intentionally lets a signed-in user enter a different target
username. This demonstrates that Oracle Database, rather than the Flask route,
rejects a cross-user write. Do not treat a submitted username, memory scope, or
decoded token claim as proof of identity in another application.

## Controls included in this example

The example includes these safeguards:

- The Flask development server and advertised browser URL are restricted to
  loopback hosts.
- The OCI IAM domain must be an HTTPS origin. Token requests refuse redirects,
  require JSON, and limit the response size so the OAuth client secret is not
  forwarded to an unexpected destination.
- Authorization Code login uses a random state value and PKCE with `S256`.
- Access tokens remain in the process-local server-side session store. Browser
  cookies contain only random session identifiers and use `HttpOnly` and
  `SameSite=Lax`; `Secure` is enabled when the configured browser origin uses
  HTTPS.
- The session identifier and CSRF token are replaced after authentication.
  Anonymous sessions expire after ten minutes, authenticated sessions expire
  with their end-user token, and the store has a fixed capacity.
- State-changing browser requests require a CSRF token. Invalid logout requests
  do not delete a valid session.
- Responses use a restrictive Content Security Policy, deny framing and MIME
  sniffing, suppress referrers, and disable caching.
- The runtime database account is separate from the schema owner and security
  administrator. It receives only `CREATE SESSION` and
  `CREATE END USER SECURITY CONTEXT` in the supplied setup script.
- Every list and add operation runs in an
  `OracleMemoryEndUserSecurityContext`. The database validates the end-user and
  database-access tokens and enforces the own-row data grant.
- Raw database, OAuth, token, memory, and submitted values are not returned in
  error messages.

> [!IMPORTANT]
> These controls reduce risk in the local exercise; they do not make the
> project production-ready. The assumptions, controls, and topics in this
> document are not exhaustive and must not be treated as a deployment
> checklist. Any shared or production deployment needs its own threat model,
> architecture review, security testing, and operational review by
> appropriately qualified people.

## Starting points for a deployment security review

The topics below are starting points only. Satisfying them does not establish
that a system is secure or production-ready. Review the complete architecture,
deployment environment, data flows, dependencies, and the official Oracle
documentation linked at the end of this document.

### Identity, OAuth, and sessions

Use a production OAuth/OIDC client library and validate the complete identity
provider metadata and token expectations required by your application. Keep
the authorization-code redirect URI exact, retain state and PKCE, allow only
the intended grants and scopes, and rotate client secrets. The `sub` claim
decoded in `oauth.py` is unverified and is used only as display text. It must
never drive authorization. In this design Oracle Database validates the token
when it establishes the end-user security context.

Authorization codes and state values arrive in the callback query string.
Configure reverse proxies, application servers, tracing, and access logs to
redact that query string and prevent it from entering telemetry.

Replace `DemoSessionStore` with a bounded, shared server-side session service
that provides encryption, expiration, atomic rotation, revocation, monitoring,
and cleanup across all application instances. Revoke tokens where the identity
provider supports it. Define idle and absolute session lifetimes. Use a
`__Host-` cookie over HTTPS, and reassess `SameSite` if the deployed login flow
requires cross-site cookie behavior.

### Web and network deployment

Do not expose Flask's development server. Use a maintained production WSGI
server behind an HTTPS reverse proxy, configure the exact trusted hosts and
proxy hop count, and keep certificate validation enabled for every outbound
connection. Add request, user, and provider quotas; concurrency limits;
end-to-end deadlines; and safe overload behavior. Review the CSP and other
headers whenever templates or external assets change.

Restrict ingress and egress at the network layer. Allow OAuth traffic only to
the expected OCI IAM origin, database traffic only to the intended database,
and embedding traffic only to the approved provider. Use TLS or mTLS for Oracle
Database connections and HTTPS for the embedding endpoint.

### Database authorization

Preserve the separation between the security administrator, schema owner,
runtime pool account, database application identity, and human end users. The
runtime account should retain only the privileges required to connect and
create an end-user security context. Review every data role, IAM group mapping,
data grant, and predicate as a production authorization policy.

Test authorization against a live database before release. Tests should prove
that each user can access only the intended rows, cross-user reads and writes
fail, expired or malformed tokens fail closed, and pooled connections never
retain a prior user's security context. Enable Oracle Unified Auditing for Deep
Sec configuration changes, security-context creation, and relevant end-user
data operations. Protect and retain the audit trail independently of
application diagnostics.

`SchemaPolicy.NO_CHECK` is appropriate here because setup creates the schema
first. A deployed service needs a controlled, versioned schema migration and
rollback process. It must not let a web process create, replace, or upgrade
database security objects.

### Data sent to providers

Memory text is persisted in Oracle Database and is sent to the configured
embedding provider when a memory is added. In this demonstration, embedding
may occur before the database rejects an intentionally cross-user insert. That
means an unauthorized write can still consume provider resources and disclose
the submitted text to the configured provider.

In a deployed application, derive the target user from authenticated context
or perform a cheap authorization check before calling any model or embedding
service. Apply data classification, minimization, residency, retention, and
deletion rules to raw content, metadata, derived memories, and embeddings.
Choose model endpoints that meet those rules, and prevent secrets or regulated
data from entering the workflow unless explicitly approved.

### Secrets and configuration

The `.deepsec.env` files are convenient local templates, not a production
secret-management mechanism. Store database passwords, wallet passwords,
OAuth client secrets, Flask signing keys, and embedding credentials in a
managed secret service such as OCI Vault. Give the workload access only to the
individual secrets it needs, rotate them, and audit retrieval. Never commit
populated environment files, copy them into images, expose them in process
arguments, or include them in logs and support bundles.

The shell helper sources `.deepsec.env` as shell code. Only source a file that
is owned and writable by the expected administrator, and restrict its mode
(for example, `0600`). A production setup tool should retrieve structured
configuration from a trusted secret source instead of evaluating a file.

### Destructive setup operations

Review every setup command before running it. `scripts/setup_memory.py` uses
`SchemaPolicy.RECREATE`, which deletes and recreates this example's managed
Agent Memory schema objects and their data.

`database_scripts/db_ociiam_setup.sh` uses `force => TRUE`, drops the fixed
`OCI_IAM_DOMAIN_DB_CRED$` credential, and recreates it. Oracle documents that
forcing external authentication can replace an existing provider and disrupt
users or applications. The credential is dropped before its replacement is
created, so a failure can also leave authentication unavailable. Inventory the
current configuration, take appropriate backups, coordinate an outage and
rollback plan, and use change-controlled, idempotent migrations in any shared
environment.

`database_scripts/db_deepsec_user_setup.sh` creates accounts and grants
privileges. Use dedicated accounts, password profiles, resource limits, and
the smallest tablespace quotas suitable for the deployment. Do not use an
unlimited quota without an explicit capacity decision.

### Dependencies, monitoring, and incident response

Resolve and lock dependencies in a trusted build, verify artifacts, scan both
direct and transitive packages, and rebuild regularly for security updates.
Run static analysis and secret scanning in CI. Keep the Python runtime,
`python-oracledb`, Flask, Oracle AI Agent Memory, database client, and database
release on supported patch levels.

Monitor failed logins, token exchanges, CSRF failures, rate-limit events,
provider consumption, session growth, database denials, data volume, and Deep
Sec policy changes without logging tokens, secrets, memory text, raw metadata,
or unnecessary personal identifiers. Define procedures to revoke OAuth
clients, rotate every affected credential, invalidate sessions, preserve audit
evidence, and notify data owners after an incident.

## Official Oracle documentation

- [Oracle AI Agent Memory security considerations](https://docs.oracle.com/en/database/oracle/agent-memory/26.6/guide/security.html)
- [Oracle Deep Data Security: IAM, database, and application configuration](https://docs.oracle.com/en/database/oracle/oracle-database/26/ddscg/iam-database-and-application-configuration.html)
- [About the end-user security context](https://docs.oracle.com/en/database/oracle/oracle-database/26/ddscg/end-user-security-context1.html)
- [Understand the application-mediated authentication flow](https://docs.oracle.com/en/database/oracle/oracle-database/26/ddscg/understand-authentication-flow-and-prerequisites.html)
- [Configure the database for IAM integration](https://docs.oracle.com/en/database/oracle/oracle-database/26/ddscg/configure-database-iam-integration.html)
- [Enable OCI IAM authentication on Autonomous AI Database](https://docs.oracle.com/en-us/iaas/autonomous-database-shared/doc/enable-iam-authentication.html)
- [Audit Oracle Deep Data Security operations](https://docs.oracle.com/en/database/oracle/oracle-database/26/ddscg/audit-oracle-deep-data-security-operations.html)
- [OCI Secret Management](https://docs.oracle.com/en-us/iaas/Content/secret-management/Concepts/manage-secrets.htm)
- [Secure python-oracledb network traffic](https://python-oracledb.readthedocs.io/en/latest/user_guide/connection_handling.html#securely-encrypting-network-traffic-to-oracle-database)
