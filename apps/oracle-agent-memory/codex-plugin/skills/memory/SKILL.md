---
name: memory
description: Use memory-as-tool to add and search memories throughout the Codex session.
---

# Memory

You have access to persistent tool-based memory. Memories contain knowledge from architects, maintainers, prior agents, debugging sessions, design reviews, and earlier implementation work. They preserve durable facts that are useful across turns and sessions: architecture rationale, repo conventions, product constraints, decisions, pitfalls, working commands, and lessons learned from repeated errors. Search results can also include prior Codex messages captured by Memory hooks; treat those as transcript evidence rather than distilled durable facts.

In these instructions, Memory means the persistent MCP-backed Memory tools, not your internal recollection. Searching Memory is an evidence-gathering step like reading repository files or checking command output. Use Memory to avoid guessing from unaudited recollection.

Decision boundary: should you search Memory for a new user query?

- Skip Memory only when the request is clearly self-contained and does not need workspace history, conventions, or prior decisions.
- Hard skip examples: current time/date, simple translation, simple sentence rewrite, one-line shell command, trivial formatting.
- Search Memory early for most non-trivial repository work. Current files are the source of truth, but they do not replace Memory; Memory may contain prior decisions, pitfalls, maintainer preferences, debugging lessons, and context that has not been written into the repo.
- Use search by default when any of these are true:
  - the query mentions a repository, module, path, subsystem, integration, plugin, MCP server, build, test, migration, or deployment detail;
  - the user asks for prior context, consistency, previous decisions, remembered preferences, or "what did we do before";
  - the task is ambiguous and could depend on earlier project choices;
  - the work is non-trivial and prior implementation notes, conventions, or debugging history could save time;
  - you hit repeated errors, surprising behavior, or suspect a known project-specific issue.
- For any non-trivial coding, debugging, design, review, build, or planning task, run at least one quick Memory search before substantial exploration or implementation unless a hard skip applies.
- Search Memory again when the topic changes materially: a new subsystem or path, a new design choice, a surprising failure, a test/build/debugging issue, before asserting that no prior context exists, or before committing to a durable project decision.
- If unsure, do a quick Memory search before deeper exploration.

Quick Memory pass:

1. Extract a few task-relevant keywords from the user request and current workspace context.
2. Call search with a concise query.
3. Use the retrieved memories as hints and verify drift-prone facts against the repo, tools, or current environment when needed.
4. If there are no relevant hits, stop the memory lookup and continue normally.

Updating Memory:

- Call add when the user asks you to remember something or when you have a compact, durable project fact that future agents should know.
- Good memories are self-contained and specific: include the repo/module, the decision or lesson, and the reason or evidence when it matters.
- Write selectively. Most task progress, command output, logs, and short-lived observations should not become memories.
- Do not store secrets, credentials, private personal data, transient logs, or facts that are only useful inside the current turn.
