# Workshop: Build a Team Knowledge Base

> **Oracle AI Database edition.** This run-of-show was written for the workshop build. In this edition the permission step no longer lives in the application's SQL: it is a row policy on the `documents` table, identity is a session property set through a trusted PL/SQL package, and embeddings are computed by the database. Segment 6 (access control) therefore opens with the one-liner `SELECT COUNT(*) FROM documents` returning 0 for a session with no identity. Everything else in the argument is unchanged.

~75 minutes. Attendees leave with a working knowledge base over **their own**
data, queried through Claude Code, and the reference architecture for a client
engagement.

**Two things to land, in this order:**

1. **The layering.** Your second brain is _who_. The team brain is _what_. You
   want both, and they do different jobs. Full argument in
   [PERSONAL_VS_TEAM.md](PERSONAL_VS_TEAM.md).
2. **The architecture.** Meet data where it lives. Every source becomes a small
   connector into one shared table, and one interface answers over all of them.

Retrieval quality, enrichment, and permissions are the policy that makes the
substrate worth sharing. They are co-equal beats under (2).

**Setup (do before the session):** complete the prerequisites in [Quick start](../README.md#quick-start), then run:

```bash
docker compose up -d --wait --wait-timeout 900
uv sync --extra dev --locked
uv run python scripts/bootstrap_db.py
uv run team-brain doctor
uv run team-brain access seed
```

Have Claude Code installed. Bootstrap creates both app and test users and loads the embedding model. `doctor` validates the test schema; `access seed` prepares the app principals required by the included MCP configuration. Add the workshop knowledge through the ingestion steps below.

## Run of show

### 1. Two layers, not one (10 min, FRAMING)

Open with the scattered-knowledge problem: answers stranded across Slack,
GitHub, and docs, no single search covering them, and a single-source RAG demo
that doesn't survive a real team.

Then immediately correct the assumption most people walk in with, because
everything after this depends on it. A team knowledge base is **not** "a second
brain for more people." They are two layers:

- **Personal second brain = an agent.** Personality, knows you, remembers your
  context, proactive, acts on your behalf. One per person.
- **Team brain = a substrate.** No persona, no memory of you, not proactive.
  Shared, permissioned, well-ranked knowledge that many agents query. One per
  team.

Say the reason out loud: **you cannot expect every teammate to build hybrid
retrieval, enrichment, freshness decay, and ACL enforcement into their own
personal setup.** Ten people implementing it means ten sets of bugs and ten
chances to leak a private channel. So you build it once in the shared layer, and
every client inherits it.

> **Centralize the policy. Distribute the personality.**

This also answers the question someone always asks: _does the team brain replace
my second brain?_ No. It's the layer underneath it.

### 2. The architecture: meet data where it lives (15 min, HEADLINE)

Open `team_brain/schema.py` (the `Document` contract) and `team_brain/db.py`
(the one table). One table with `visibility`/`acl`/`project` columns and
`UNIQUE(source, external_id)`, plus a connector contract so any source is a
~40-line plugin writing the same rows. Everything else in the repo hangs off
this.

Name the trap while you're here: connectors are per **source**, never per
person. Identity is a property of the database session (set through `tb_session`),
not a separate store per teammate.

### 3. Everyone writes a connector (20 min, the headline made hands-on)

Attendees copy `team_brain/connectors/TEMPLATE.py`, point it at _their_ source
(a repo, a docs folder, a Slack export), register it, and:

```bash
uv run team-brain ingest <their-source>
uv run team-brain stats
```

It becomes queryable through the exact same system as every other source. No
source handy? Use the seed data (`data/seed/`). Follow `docs/WRITE_A_CONNECTOR.md`.

### 4. Query it from Claude Code via MCP (12 min)

Copy `.mcp.json.example` to `.mcp.json` (Jeff's demo token is in it). In Claude Code, call `search` / `who_knows`, watch
the primitives return raw evidence and Claude synthesize.

**Tie it back to segment 1**, this is where the layering becomes concrete rather
than conceptual. Point out what the server does _not_ expose: there is no
`answer()` tool. Only primitives returning evidence rows. Ask the room why.

The answer: a server that synthesizes imposes one voice on every consumer. The
person debugging an incident and the person writing onboarding docs need the
same evidence shaped differently. Return evidence, and each person's own agent
does the interpreting with its own personality and context. Cerebras shipped
exactly this in [their knowledge base write-up](https://www.cerebras.ai/blog/how-we-built-our-knowledge-base)
and called them _LLM-free retrieval primitives_.

Worth noting: their system serves humans, automations, **and** agents from these
same primitives. A substrate with no personality is the only thing all three can
share.

### 5. The policy that makes it worth sharing (8 min)

Frame these as _policy the substrate owns on everyone's behalf_, not as
miscellaneous features. This is the payoff of segment 1.

- **Retrieval policy** (`retrieval.py`): `_naive_linear_blend` vs `search` on
  the same query. Run `uv run team-brain eval` and read the
  `RRF must-include hits vs linear` line, the win measured.
- **Enrichment policy** (`enrich.py`): enrich-raw vs enriched on a Slack thread.
  The corpus stores what a thread _meant_, not its chatter.

Each one is a standing decision made once, in one place, that every client
inherits for free. The biggest one gets its own segment next.

### 6. Access control, enforced in the database (12 min, SECOND DIAGRAM)

Put up `docs/team-brain-security.png`. Most retrieval write-ups, the Cerebras post
above included, stop at a relevance scope such as "projects", which is not
enforcement. A shared brain with no access layer is a leak generator.

Teach the two steps (keep them separate; the label and the enforcement are different jobs):

1. **Label at ingestion.** The connector stamps each document with the domain it
   came from (`--domain ops`; a Slack channel carries its domain). The label
   **decides nothing on its own**, and one item can carry more than one label.
2. **Enforce at retrieval.** The label only matters because every read path
   filters on it **in SQL, before the model sees a row**, fail-closed.

Demo it live:

```bash
uv run team-brain access seed          # prints Jeff/Julia/Sam/Brian + their tokens
uv run team-brain ingest slack --export data/seed/slack_export_domains.json
uv run team-brain ask "what's our enterprise discount ceiling?" --token <jeff>   # ops → blocked
uv run team-brain ask "what's our enterprise discount ceiling?" --token <brian>  # CEO → sees it
```

The key resolves to an identity; the identity resolves to the domains you may
see (`whoami` in the MCP client shows it). Land the load-bearing point:

> **Never let the model decide who may see what.** An LLM told "don't look at
> sales" can be talked out of it, and once a document is in the context window a
> prompt injection can exfiltrate it (EchoLeak, CVE-2025-32711). So the boundary
> is code, not instructions, and the _server_ owns identity, not the agent.

### 7. Where to take it (6 min)

Per-caller OAuth identity on the MCP server (spec 2025-11-25: audience-bound
tokens, no passthrough), permission mirroring of each source's real ACLs (the
Glean model), RBAC→ABAC, incremental sync at scale, a cross-encoder rerank,
relevance scopes ("projects") turned into _enforced_ grants, `who_knows` for org
routing, and the enterprise version.

## The takeaways to say out loud

- **Your second brain is _who_; the team brain is _what_.** You want both. The
  team brain is the layer underneath your agent, not a replacement for it.
- **Centralize the policy, distribute the personality.** Enrichment, retrieval
  and permissions are too hard to ask every teammate to rebuild. The substrate
  owns them once.
- **The team brain has no personality on purpose,** so that many personalities
  can consume it. That is why it ships primitives, not answers.
- One table + a connector contract is the entire multi-source story. Any new
  source plugs in behind the same rows. Connectors are per source, never per
  person.
- Search gets good when you fuse keyword and vector by rank, decay by age, and
  clean up noisy sources before you store them.
- **Label at ingestion, enforce at retrieval.** Permissions belong in the query,
  enforced in SQL, fail-closed, before the model. Never trust the LLM to redact,
  and make the server (not the agent) the trust boundary.
