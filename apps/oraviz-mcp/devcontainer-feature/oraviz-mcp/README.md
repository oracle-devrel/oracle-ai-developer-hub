# Oracle Viz MCP devcontainer feature

Clones the source into `/opt/oraviz-mcp`, builds a Docker image after creation,
and configures a local stdio MCP client. Docker-in-Docker is for trusted local
development; access to its daemon is a powerful privilege.

```json
"features": {
  "ghcr.io/jasperan/oraviz-mcp/oraviz-mcp:0.1.0": {
    "version": "REVIEWED_COMMIT_SHA",
    "oracleUser": "oraviz_reader",
    "oracleHost": "YOUR_PRIVATE_DATABASE_HOST",
    "oraclePort": "1521",
    "oracleService": "FREEPDB1"
  }
}
```

Replace the placeholders and pin the feature to a reviewed release and server
source to a reviewed commit. `latest` follows the repository's default branch and
is a development convenience. The repository option accepts HTTPS URLs without
credentials. The database host must be reachable from the MCP container;
`localhost` inside it is not the devcontainer or host's database listener.

Use a dedicated database reader with `CREATE SESSION` and object-level `READ`
grants. Inject `ORACLE_PASSWORD` into the MCP host's environment using your local
secret mechanism before launching the client; Docker forwards it at runtime.
Keep `oraclePassword` empty. Feature options can persist in build metadata or
images, so never put real credentials in `devcontainer.json`, source URLs, or
image builds. The legacy password option is only for disposable local testing.

The installer creates `.oraviz-mcp-env` in the remote user's actual home with
`umask 077`, mode `0600`, and that user's ownership. It omits an empty password,
quotes values for dotenv readers, and never evaluates them through `bash -c`.
It refuses to overwrite existing files or symlinks, and installation fails if
writing, permission setting, or ownership changes fail. Newlines and `${...}`
are rejected because dotenv consumers can interpolate them; use runtime process
environment injection for such secrets. Do not `source` this dotenv file.

Stdio trusts the local OS account. For remote transports, configure all required
JWT settings, TLS and network restrictions from [SECURITY.md](../../SECURITY.md).
An unprotected listener is not an alternative to local stdio.
