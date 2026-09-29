# Personal Second Brain vs Team Brain

> The single most important idea in this workshop. Read this before the code.

Most people arrive assuming a team knowledge base is "a second brain, but for
more people." It isn't. They are two different layers that do two different
jobs, and you want **both**. Getting this wrong produces one of two bad
outcomes: a team brain that tries to have opinions, or a personal brain that
tries to be shared infrastructure.

## The one-line version

**Your second brain is _who_. The team brain is _what_.**

|                     | Personal Second Brain             | Team Brain                             |
| ------------------- | --------------------------------- | -------------------------------------- |
| What it is          | an **agent**                      | a **substrate**                        |
| Has a personality   | yes (a persona file)              | **no, deliberately**                   |
| Knows who you are   | yes, deeply                       | only enough to filter what you may see |
| Curation            | you, by hand                      | nobody; it meets data where it lives   |
| Proactive           | yes (scheduled check-ins, drafts) | no, it answers when asked              |
| Acts on your behalf | yes                               | no                                     |
| Trust boundary      | everything in it is yours         | everything in it is permissioned       |
| How many            | one per person                    | one per team                           |

## Why the team brain has no personality

This is a design decision, not a missing feature.

Ten people query the same team brain through ten different clients. If the team
brain synthesized answers, it would impose **one voice and one interpretation**
on all ten. The person debugging a production incident and the person writing an
onboarding doc need the same evidence shaped very differently.

So the server returns **evidence, not answers**. Each person's own agent, with
its own personality, its own context, and its own instructions, does the
interpreting.

That's why `mcp_server.py` deliberately ships **no `answer()` tool**. Only
`search`, `search_code`, `who_knows`, and `get_document` (the full text of one
result), all returning raw evidence rows.
Cerebras made the same call in [their knowledge base write-up](https://www.cerebras.ai/blog/how-we-built-our-knowledge-base) and named it well:
_LLM-free retrieval primitives_.

> **The team brain is personality-free _so that_ many personalities can consume it.**

## But it is not "just a database"

The team brain is not a passive store you drop text into. It carries real capability, and specifically it carries
**policy**, the standing decisions about how team knowledge is treated:

| Policy                | Where                      | What it decides                                                                                         |
| --------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------- |
| **Ingestion policy**  | `connectors/`              | which sources count, how each maps into the shared contract, what gets tombstoned                       |
| **Enrichment policy** | `enrich.py`                | what a noisy thread actually _meant_ before it's stored (question, resolution, systems)                 |
| **Retrieval policy**  | `retrieval.py`             | what "relevant" means here: fuse keyword and vector by rank, decay by age, favor rare informative terms |
| **Permission policy** | `access.py` (the database) | who may see what, enforced by a row policy on the table itself, on every read from any client           |

None of that is personality. It's **policy**, and policy is shared by
definition.

## The argument for why this belongs in the substrate

Here is the practical reason the split matters, and the thing to say out loud in
the workshop:

**You cannot expect every person on the team to build this into their own second
brain.**

Hybrid retrieval with rank fusion, LLM enrichment before embedding, freshness
decay, tombstoning as sources change, ACL enforcement that fails closed: that
is real engineering. Asking ten teammates to each implement it in their personal
setup gives you ten different answers to the same question, ten different bugs,
and ten different chances to leak a private channel.

So you build it **once**, in the shared layer, and every client inherits it for
free. The individual keeps what is genuinely individual (their agent's
personality, their own notes, their working context) and inherits the hard parts
from the substrate.

That is the whole architecture in one sentence:

> **Centralize the policy. Distribute the personality.**

## How they compose

```
  Alice's second brain        Bob's second brain        an automation
  (her agent, her persona,    (his agent, his           (no personality
   her notes, proactive)       context, proactive)       at all)
          │                          │                        │
          └──────────────┬───────────┴────────────────────────┘
                         │   MCP: search / search_code / who_knows
                         │   (raw evidence rows, permission-filtered per caller)
                         ▼
                 ┌───────────────────┐
                 │    TEAM BRAIN     │   no persona · no memory of you
                 │  ingest · enrich  │   policy lives here
                 │ retrieve · permit │
                 └───────────────────┘
                         ▲
        connectors: Slack · GitHub · docs · yours
        (per source, never per person)
```

Note the third caller. The Cerebras system serves humans, automations, **and**
agents from the same primitives. A substrate with no personality is the only
thing all three can share.

## Things this rules out (and why that's good)

- **"Everyone syncs the team data into their personal vault."** Now you have N
  copies, N sync bugs, and permissions enforced N times. The ACL check belongs
  next to the data.
- **"The team brain should learn my preferences."** That's your agent's job. The
  moment the substrate has preferences, it has _someone's_ preferences.
- **"Let's add an `answer()` tool so it's easier to call."** Easier once, worse
  forever. You've just hard-coded one interpretation for every consumer.
- **"Write a connector per teammate."** Connectors are per **source**, not per
  person. Identity is a _property of the session_ the database filters on,
  never a separate store.

## One honest caveat in this POC

`agent.py` does implement plan → execute → synthesize behind the CLI `ask`
command, so this repo _can_ produce an answer directly. That path exists for
people not driving from Claude Code, it is stateless and evidence-bound (answer
only from retrieved rows, always cite), and the MCP path attendees actually use
bypasses it. It's a convenience, not a character.

Relatedly, the MCP server resolves a per-caller identity from a bearer token on
every request (over HTTP) or from one token per process (over stdio), and the
database, not the server, does the resolving. Tokens in this POC are static;
a real deployment issues short-lived ones from an identity provider. See
`docs/WORKSHOP.md` § "Where to take it."

## Where the policy lives (Oracle AI Database edition)

The workshop build enforced permissions with a `WHERE` clause the application had to remember on every read path. In this edition a `DBMS_RLS` row policy reads the caller's identity from an application context that only the `tb_session` package can write. The database appends the predicate to ordinary reads from MCP, LangChain, or a SQL client. A session that never established an identity sees zero rows, and a failed identity change clears the previous grant.

The schema owner remains trusted. It can set ingest mode, assume a named principal, or change the policy; this demo's service holds that credential. The benefit demonstrated here is filtering that every ordinary read inherits, including reads whose application code has no permission clause. Production must separate the policy owner from a restricted application user and expose a token-only authentication API. Enrichment and rank fusion remain application code. See the README's honest limits for the deployment boundary.
