# Oracle AI Agent Memory Codex Plugin

This plugin exposes Oracle AI Agent Memory to Codex as **Memory**, providing both
automated message ingestion as well as manual `add` and `search` tools usable by
Codex throughout the session.

> [!WARNING]
> This directory is a local tutorial prototype, not a production-ready MCP
> service. When enabled, its hooks persist user prompts and assistant messages.
> Review [SECURITY.md](SECURITY.md) before using real data or adapting the
> example for a shared deployment.

## User setup

This section is for users connecting Codex to an already deployed Oracle AI
Agent Memory MCP server. A deployment operator must provide an
`OAM_MCP_TOKEN` for the relevant `user_id` and `agent_id`. The bundled
`.mcp.json` points to the loopback prototype by default. Before distributing
the plugin for use with an approved remote service, the operator must replace
that URL with the service endpoint.

### Install the plugin

Add the local plugin marketplace:

```bash
codex plugin marketplace add path/to/codex_plugin
```

Or add it directly to `~/.codex/config.toml`:

```
[marketplaces.codex-oam]
source_type = "local"
source = "path/to/codex_plugin"
```

Then add the plugin:

```bash
codex plugin add oracle-ai-agent-memory@codex-oam
```

The automatic message-capture hooks use the third-party `requests` package.
Before launching Codex, make sure the `python` executable in the environment
from which you launch Codex has it installed:

```bash
python -m pip install requests
```

The hooks invoke `python`, so use the same environment when starting Codex.

### Use the plugin in Codex

Export the user token provided by the deployment operator:

```bash
export OAM_MCP_TOKEN="eyJhbGciOiJI..."
```

Start Codex with the MCP server running:

```bash
OAM_MCP_TOKEN="eyJhbGciOiJI..." codex
```

Codex requires command hooks, including plugin-bundled hooks, to be reviewed
and trusted before they execute. After installing and restarting Codex, inspect
`/hooks` and trust the Oracle AI Agent Memory `UserPromptSubmit` and `Stop`
hooks to enable automatic message capture.

Run `/mcp` to verify that the Memory MCP server is available:

```
  • memory
    • Auth: Bearer token
    • Tools: add, search
```

To remove the plugin:

```bash
codex plugin remove oracle-ai-agent-memory@codex-oam
```

To disable it without removing it, add this to `~/.codex/config.toml`:

```
[plugins."oracle-ai-agent-memory@codex-oam"]
enabled = false
```

## Prototype server setup

This section is for the operator running the Memory MCP server and issuing
tokens. The example server is intentionally restricted to a loopback address.
Run the commands below from the extracted or source `codex_plugin` directory.

Install the reference server dependencies in its Python environment:

```bash
python -m pip install oracleagentmemory fastmcp PyJWT python-dotenv
```

### Generate the signing secret

`JWT_SECRET` is the randomly generated signing secret used both to create and
validate MCP tokens. Generate it once and keep it secret:

```bash
export JWT_SECRET="$(openssl rand -hex 32)"
```

This creates 32 random bytes encoded as 64 hexadecimal characters (256 bits of
entropy), suitable for the HS256 JWT signing algorithm. The variable must be
loaded in the environment when running `create_token.py` and the MCP server.

### Configure and start the MCP server

Copy the supplied template and populate `misc/.env` with values for your
environment:

```bash
cp misc/.env.sample misc/.env
```

Choose a distinct `MEMORY_STORE_ID` of at most 16 characters for this plugin
and environment. Do not derive it from request data or let plugin users select
it.

`remote_mcp_server.py` loads `JWT_SECRET` from `misc/.env` when it starts. The
server must use the same secret that was loaded when creating each
`OAM_MCP_TOKEN`. Changing `JWT_SECRET` invalidates all existing MCP tokens;
generate new tokens after rotating the secret.

Start the server with:

```bash
python misc/remote_mcp_server.py --host 127.0.0.1 --port 8000
```

Make sure that the host and port match the values from `.mcp.json`.

### Create a user token

Create a token for the user and agent that should access the server. The
`JWT_SECRET` environment variable must contain the same secret configured in
`misc/.env`:

```bash
python misc/create_token.py \
  --user-id "john.doe@example.com" \
  --agent-id "codex-memory"
# eyJhbGciOiJI...
```

Provide the resulting token to the user as `OAM_MCP_TOKEN`.
