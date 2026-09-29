# team-brain

**A knowledge base for a whole team, where the database decides who sees what.**

This is the team-scale counterpart to a personal second brain. I built the first version with the Dynamous community in a workshop; this version moves the hard part, access control, out of the application and into the database. It runs on Oracle AI Database because the design needs three things on the same row: a native `VECTOR` column with the embedding computed inside the database, an Oracle Text index for the keyword leg, and a `DBMS_RLS` row policy that decides who may read the row, from any client. The structure is the part to take with you: one shared table, small connectors per source, hybrid search over the same rows, and a permission model the database enforces instead of the app.

By [Cole Medin](https://github.com/coleam00). Companion code for [my YouTube video](https://www.youtube.com/@ColeMedin) on evolving a personal AI second brain into a team brain.

> Setting this up? Open the folder in Claude Code (or the agent of your choice) and say: _"Read the README and get team-brain running end to end, then wire up the MCP server so I can query it."_ Everything it will run is in [Quick start](#quick-start).

## Your second brain is who. The team brain is what.

A personal second brain is an agent. It has a personality, it knows you, it works on your behalf, and only you feed it. A team produces far more than any one person can keep up with, so the team needs something else underneath: a shared, permissioned, well-ranked store that many different agents query. That store has no personality on purpose. If it synthesized answers, it would impose one voice on ten people. So it returns evidence, and each person's own agent does the interpreting.

What the team brain does own is the policy: which sources count, what a messy Slack thread actually meant, what "relevant" means, and who may see what. You cannot ask every teammate to build that into their own setup. Build it once, and every agent inherits it.

Centralize the policy. Distribute the personality. And the most central place for policy is the database.

The long version, including what this rules out, is in [docs/PERSONAL_VS_TEAM.md](docs/PERSONAL_VS_TEAM.md).

## What is in here

- **Connectors** (`team_brain/connectors/`): Slack export, GitHub, markdown docs, and a template. Each one is about forty lines and emits the same `Document` row (`team_brain/schema.py`). Adding a source does not touch anything downstream.
- **One table** (`team_brain/db.py`): text, a native `VECTOR` column, an Oracle Text index, and JSON columns for the access labels, all on the same row. The embedding is computed inside the `MERGE` that writes the row with `VECTOR_EMBEDDING(...)`, so the text never leaves the database to be embedded and there is no embedding service to run.
- **Hybrid search** (`team_brain/retrieval.py`, `team_brain/langchain_legs.py`): a keyword leg and a vector leg over the same rows, through Oracle's LangChain package (`OracleTextSearchRetriever` and `OracleVS`), fused by rank with Reciprocal Rank Fusion plus a light age decay. The tests assert the LangChain legs and the plain SQL legs return the same rows.
- **Labels at ingest, enforcement in the database** (`team_brain/access.py`): every row carries its domains and, for private channels, an ACL. Identity is a property of the database session, set through a trusted PL/SQL package (`tb_session`) from a token the database resolves itself. A `DBMS_RLS` row policy on the table appends the caller's predicate to every `SELECT`, from any client. The read code has no permission SQL in it. A session that never established an identity gets zero rows, and the kernel refuses a direct write to the context.
- **Clients**: an MCP server (`team_brain/mcp_server.py`) that exposes `search`, `search_code`, `who_knows`, and `get_document` and returns evidence rows rather than answers, a LangChain `create_agent` CLI (`team_brain/agent.py`), and a plain CLI.

## Quick start

Install Docker with Compose v2 (including `--wait`) and `uv`. Python 3.12 or newer is required; `uv` can install it. Allow several minutes for the first database boot and a roughly 117 MB embedding-model download during bootstrap. Pulling the Oracle image requires accepting its licence with a free Oracle account and running `docker login container-registry.oracle.com` first. Ports 1521 and, for the optional browser, 8181 must be free.

```bash
git clone https://github.com/oracle-devrel/oracle-ai-developer-hub.git
cd oracle-ai-developer-hub/apps/team-brain
docker compose up -d --wait --wait-timeout 900  # wait for the database health check
uv sync --extra dev --locked
uv run python scripts/bootstrap_db.py   # app users, grants, and the in-database embedding model

# Ingest some knowledge (offline, no API key: embeddings happen in the database)
uv run team-brain ingest markdown data/seed/docs
uv run team-brain ingest slack --export data/seed/slack_export.json
uv run team-brain ingest github coleam00/helpline      # optional; needs network

# Ask (offline: deterministic extractive answer; with an LLM key: a LangChain agent).
# --user and --as are operator assertions for this CLI, which holds the schema-owner
# credential. Only --token (and the MCP bearer header) is an identity the database resolves.
uv run team-brain ask "how do we deploy the billing service?" --user alice

# Measure retrieval quality
uv run team-brain eval

# Access control: label by domain, enforce in the database
uv run team-brain access seed          # seeds Jeff/Julia/Sam/Brian, prints their tokens
uv run team-brain ingest slack --export data/seed/slack_export_domains.json
uv run team-brain whoami --as jeff     # what the DATABASE resolved, and how many rows it may see
uv run team-brain ask "what is our enterprise discount ceiling?" --as jeff   # ops: nothing
uv run team-brain ask "what is our enterprise discount ceiling?" --as sam    # sales: the policy
uv run team-brain ask "what is our enterprise discount ceiling?" --token tb_exec_brian_9d4c7b13
```

For Database Actions in a browser, run this after the quick start. The optional Compose profile installs Oracle REST Data Services (ORDS), connects it to `oracle` on the shared Compose network, and waits for its HTTP endpoint before enabling the app schema:

```bash
docker compose --profile browser up -d --wait --wait-timeout 1200
uv run python scripts/enable_rest.py
```

Sign in as `TEAMBRAIN` with the demo password `TeamBrain123` at `http://localhost:8181/ords/sql-developer`. The table's Columns tab shows its structure. Its Data tab normally shows no rows because the browser has not established a Team Brain identity.

To inspect permitted rows, run the following as one script in the SQL worksheet (F5), then open Script Output. Identity setup, reads, and cleanup stay in the same database call because ORDS pools connections. Use `brian` instead of `jeff` to inspect the leadership view. These named identity setters are trusted operator actions in this demo.

```sql
SET SERVEROUTPUT ON
BEGIN
  tb_session.set_principal('jeff');
  FOR r IN (SELECT source, title FROM documents ORDER BY source, title) LOOP
    DBMS_OUTPUT.PUT_LINE(r.source || ': ' || r.title);
  END LOOP;
  tb_session.clear;
EXCEPTION WHEN OTHERS THEN
  tb_session.clear;
  RAISE;
END;
/
```

The one-liner that shows the lock is on the rows, not in the app:

```sql
-- as the schema owner, in any SQL client, with no identity established
SELECT COUNT(*) FROM documents;   -- 0
```

If startup times out, check `docker compose ps` and `docker compose logs oracle` (or `ords` for the browser profile), resolve the reported error, then rerun the same command. Bootstrap is idempotent. The test suite uses its own schema (`TEAMBRAIN_TEST`) so it never touches your dev knowledge base.

## Query it from Claude Code (MCP)

Two transports, same tools, same policy.

**Local, stdio** (one identity per process): copy `.mcp.json.example` to `.mcp.json` in this folder. It runs the server with a token in `env`, so open Claude Code in `apps/team-brain` for it to be picked up. Swap the token to change who Claude Code is. (`.mcp.json` is git-ignored across the hub, so your copy stays local.)

Run `uv run team-brain access seed` first; the example configuration uses Jeff's demo token. A local stdio process runs on the operator's machine and can access its database credentials. Use HTTP when teammates should receive only tokens.

**Remote service, HTTP** (one identity per request): `uv run team-brain serve` starts the server on `http://127.0.0.1:8765/mcp`. Clients send `Authorization: Bearer <token>`. The client config holds the URL and the token, never the database credential. Each tool opens a fresh database session and submits the token for the database to resolve. The service is trusted in this single-schema demo because it holds the owner credential; see the production separation below.

```json
{
  "mcpServers": {
    "team-brain": {
      "type": "http",
      "url": "http://127.0.0.1:8765/mcp",
      "headers": { "Authorization": "Bearer tb_ops_jeff_7f3a9c21" }
    }
  }
}
```

Ask Claude Code "who knows about the batch cluster autoscaler?" and watch it call `who_knows`, then `search`, and cite the rows. Call `whoami` to see the identity the database resolved and how many documents it may read. A request with no token is anonymous: a real identity with no grant that sees company-wide rows only. Over HTTP the server never falls back to its own environment, so a missing header can never inherit the operator's identity.

## How it fits together

```
connectors/*  -> Document rows (the contract)            data stays where it lives
ingest:  enrich -> MERGE (embedding computed IN the database) -> tombstone-missing
documents table: VECTOR column + Oracle Text index + acl/domains/project + row policy
retrieval: vector leg + keyword leg (OracleVS / OracleTextSearchRetriever, or SQL) -> RRF -> age decay
identity:  tb_session (trusted package) -> application context -> row policy on every SELECT
clients:   Claude Code over MCP (stdio or HTTP) | LangChain agent (`team-brain ask`) | CLI
```

## Write your own connector

Implement `fetch()`, register it, run `ingest`. See [docs/WRITE_A_CONNECTOR.md](docs/WRITE_A_CONNECTOR.md).

For Slack, private-channel ACLs use immutable Slack user IDs by default. Names in `users` are display text only. If your Team Brain principals have different IDs, create an operator-owned JSON mapping such as `{"U012345": "alice", "U067890": "bob"}` and pass `--identity-map slack-identities.json` to `team-brain ingest slack`, with or without `--export`. Only map IDs whose ownership you have verified; keep mappings separate per workspace. The sample export format also accepts a top-level `principal_map`, which the bundled fixtures use to preserve the demo identities. A command-line mapping overrides that field. Re-ingest an existing Slack snapshot after adopting this change to replace old name-based ACLs; changing code alone does not rewrite stored rows.

## Prove it works

`uv run team-brain doctor` (see `scripts/validate.py`) runs the static checks, the whole test suite against the test schema, and a real ingest, ask, and eval with a permission-leak assertion. The suite includes a module that proves the database-level facts: no identity means zero rows, the context cannot be written directly, unknown tokens are refused inside the database, a raw username never sees a domain-labelled row, and the LangChain legs match the SQL legs row for row. Without a reachable database, `pytest` skips the database-backed tests and runs the rest.

Three more scripts for a bigger corpus and a protocol-level check:

- `scripts/seed_full_kb.py` loads `data/seed_full/`, a 40-person company with 24 docs across ops, sales, finance, and marketing plus 34 Slack threads, labelled per domain, with seven principals.
- `scripts/eval_full.py` runs the 37-question golden set over that corpus and applies a stricter bar (recall at least 0.9, zero permission failures).
- `scripts/check_mcp.py` drives the MCP server over the real protocol, stdio and HTTP, and asserts the row policy holds for every identity, including an unknown token and no token at all.

## Honest limits

- Tokens are static, stored as unsalted SHA-256, and printed by `access seed` so you can paste them into a client. A production deployment issues short-lived tokens from an identity provider. The enforcement model does not change.
- The default database password (`TeamBrain123`) and the seeded tokens are demo values. Change both before anything leaves your laptop.
- Single-schema demo: the app connects as the schema owner, who also owns `tb_session` and the policy. That credential can call `set_ingest`, assume a named principal, or drop the policy. This demonstrates filtering on ordinary reads and token-bearing MCP requests, not protection from the schema owner or a compromised service. Production needs a separate policy-owner schema and a restricted application user. Oracle grants `EXECUTE` on a whole package, so do not grant the application access to this demo's `tb_session` package. Expose a separate token-only wrapper API, keep the identity setters and ingest helpers inaccessible to the application, and let the trusted internal package write the context. Schema separation and grants require a separate deployment setup; this sample does not implement it.
- GitHub repository visibility is read from the source. Private repositories always produce restricted rows, even if the connector was configured as public. With no ACL mapping, those rows are visible to nobody, including anonymous callers and principals with all domains. The CLI reports them in `fail_closed`; an operator can supply a trusted mapping through `GitHubConnector(..., acl=["alice", "bob"])`. Domains alone never grant access to private repositories. Rate limits, unavailable repositories, and incomplete responses abort the sync before tombstoning. Only a missing README is accepted as an optional absent item.
- Ingestion replaces a complete snapshot per `source`. Two GitHub repos, two markdown roots, or two Slack exports using the same source replace each other's rows. Combine them in one connector snapshot or assign distinct source names before ingesting multiple collections. GitHub issues and code files are capped for this sample; it does not mirror an entire large repository.
- Upserts, tombstones, and the success log commit together. A failed import rolls back document changes and records zero committed rows in its error log.
- Project-scoped keyword searches use the bound SQL implementation on the same policy-filtered session because `OracleTextSearchRetriever` 1.5 does not support a project predicate. Unscoped keyword search and vector search use the LangChain retrievers.
- Enrichment and the CLI agent call an LLM through an OpenAI-compatible endpoint. Without a key both degrade to deterministic offline behaviour, which is also why the test suite runs with no key.
- Oracle AI Database Free is capped at 2 CPUs, 2 GB RAM, and 12 GB of data. Plenty for a team, not the sizing for a company.
- Vector search here is exact. At scale you add a vector index and over-fetch, because the index builds its candidate set before the row policy filters it.

## License

MIT. Built for a Dynamous community workshop and the video that followed it.

## Disclaimer

ORACLE AND ITS AFFILIATES DO NOT PROVIDE ANY WARRANTY WHATSOEVER, EXPRESS OR IMPLIED, FOR ANY SOFTWARE, MATERIAL OR CONTENT OF ANY KIND CONTAINED OR PRODUCED WITHIN THIS REPOSITORY, AND IN PARTICULAR SPECIFICALLY DISCLAIM ANY AND ALL IMPLIED WARRANTIES OF TITLE, NON-INFRINGEMENT, MERCHANTABILITY, AND FITNESS FOR A PARTICULAR PURPOSE. FURTHERMORE, ORACLE AND ITS AFFILIATES DO NOT REPRESENT THAT ANY CUSTOMARY SECURITY REVIEW HAS BEEN PERFORMED WITH RESPECT TO ANY SOFTWARE, MATERIAL OR CONTENT CONTAINED OR PRODUCED WITHIN THIS REPOSITORY. IN ADDITION, AND WITHOUT LIMITING THE FOREGOING, THIRD PARTIES MAY HAVE POSTED SOFTWARE, MATERIAL OR CONTENT TO THIS REPOSITORY WITHOUT ANY REVIEW. USE AT YOUR OWN RISK.
