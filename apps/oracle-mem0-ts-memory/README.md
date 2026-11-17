# Oracle AI Database + Mem0 TypeScript Memory Assistant

Companion TypeScript application for the article [_Building a long-term memory assistant with Mem0, TypeScript, and Oracle_](./docs/article.md).

This sample shows JavaScript and TypeScript developers how to use Mem0 OSS with Oracle AI Database as the vector store. It is intentionally a runnable Node.js app, not a notebook: a React frontend calls a Hono API, the API runs a Mem0 memory workflow, and the `mem0ai` Oracle provider stores and searches user-scoped vectors in Oracle AI Database.

The sample demonstrates durable preferences for two demo users, strict memory isolation, deterministic no-key embeddings, optional OpenAI-powered inference, explicit memory CRUD, and inspection of the underlying Oracle collection.

## Pipeline

1. Load ten deterministic sample memories for User 1 and User 2.
2. Embed each memory with a deterministic TypeScript implementation for repeatable local runs.
3. Store the text, vector, user scope, and JSON metadata in Oracle AI Database through Mem0's native `oracledb` vector-store provider.
4. Search Mem0 with a `user_id` filter so retrieval remains isolated to the selected user.
5. Return an extractive answer from the retrieved Oracle memories, or generate an answer when OpenAI mode is enabled.
6. In optional OpenAI mode, let Mem0 infer durable facts from completed chat turns.
7. Inspect retrieved evidence, memory CRUD operations, the Oracle table, vector column, row count, and vector indexes in the browser UI.

## Prerequisites

- Node.js 22 or later
- pnpm 10 or later
- Oracle Database Free, Oracle Database 23ai, or Oracle AI Database 26ai with vector support
- An Oracle schema that can create, insert into, select from, and drop demo tables
- Optional: `OPENAI_API_KEY` only for generated answers, OpenAI embeddings, and Mem0 fact inference
- Podman or Docker only if Oracle or the application runs in a container

The Oracle Node.js driver uses Thin mode, so Oracle Instant Client is not required.

## Quickstart

```bash
pnpm install
cp .env.example .env
```

Choose one Oracle connection target and fill in `.env`:

| Target | When to use it | Connection values |
| --- | --- | --- |
| Local Oracle Database Free / Oracle AI Database | The app runs directly on your machine and Oracle is available through a local listener | `ORACLE_CONNECT_STRING=localhost:1521/FREEPDB1` |
| Oracle on the host from a Podman or Docker app container | The Mem0 application runs in a container while Oracle runs on the host | `ORACLE_CONNECT_STRING=host.containers.internal:1521/FREEPDB1` |
| Remote Oracle Database with password authentication | Oracle is reachable over the network with schema credentials | `ORACLE_CONNECT_STRING=<host>:<port>/<service>` or a full connection descriptor |

For example, a local Oracle Database Free setup usually looks like:

```env
ORACLE_USER=<database-user>
ORACLE_PASSWORD=<database-password>
ORACLE_CONNECT_STRING=localhost:1521/FREEPDB1
MEM0_MODE=demo
MEM0_DEMO_COLLECTION_NAME=MEM0_TS_LOCAL_DEMO
MEM0_CREATE_VECTOR_INDEX=false
```

`ORACLE_DSN` is accepted as an alias for `ORACLE_CONNECT_STRING`. The default `MEM0_MODE=demo` requires no model API key.

Check the database connection:

```bash
pnpm db:check
```

Seed the Oracle-backed memory collection:

```bash
pnpm seed
```

Run the API in one terminal:

```bash
pnpm dev:api
```

Run the web app in another terminal:

```bash
pnpm dev
```

Open:

```text
http://localhost:5173
```

In the UI, select **Load demo memories**, choose **User 1** or **User 2**, and use one of the suggested questions. The Oracle evidence pane shows the exact memories used for each answer.

## Container Deployment

The Dockerfile builds the React app and Hono API into one Node.js image. At runtime the API serves the compiled web app from the same origin, so `VITE_API_BASE_URL` can be omitted unless the browser must call a separate API host.

Build the image:

```bash
docker build -t oracle-mem0-ts-memory .
```

Run it with the same environment values used for local development:

```bash
docker run --rm --env-file .env -p 8787:8787 oracle-mem0-ts-memory
```

The equivalent `podman build` and `podman run` commands work as well. Open:

```text
http://localhost:8787
```

The container expects the Oracle target from `.env` to be reachable from inside the container. When Oracle runs on the host, use the host address exposed by the container runtime instead of `localhost`; Podman Desktop commonly uses `host.containers.internal`.

## Configuration

| Variable | Required | Description |
| --- | --- | --- |
| `ORACLE_USER` | yes | Oracle schema username |
| `ORACLE_PASSWORD` | yes | Oracle schema password |
| `ORACLE_CONNECT_STRING` | yes | Oracle connect string. A common local value is `localhost:1521/FREEPDB1` |
| `ORACLE_DSN` | alias | Accepted as an alias for `ORACLE_CONNECT_STRING` |
| `MEM0_MODE` | no | `demo` (default) for deterministic embeddings and extractive answers; `openai` for OpenAI embeddings, generated answers, and Mem0 inference |
| `MEM0_DEMO_COLLECTION_NAME` | no | Oracle collection for no-key mode. Defaults to `MEM0_TS_LOCAL_DEMO` |
| `MEM0_COLLECTION_NAME` | no | Oracle collection used in OpenAI mode. Defaults to `MEM0_TS_MEMORY_DEMO` |
| `MEM0_CREATE_VECTOR_INDEX` | no | Set `true` to let Mem0 attempt vector-index creation |
| `OPENAI_API_KEY` | OpenAI mode only | Enables OpenAI embeddings, generated answers, and Mem0 fact inference |
| `OPENAI_MODEL` | no | OpenAI answer and inference model. Defaults to `gpt-4o-mini` |
| `OPENAI_EMBEDDING_MODEL` | no | OpenAI embedding model. Defaults to `text-embedding-3-small` |
| `OPENAI_EMBEDDING_DIMENSION` | no | OpenAI vector dimension. Defaults to `1536` and must match the Oracle vector column |
| `PORT` | no | API port. Defaults to `8787` |
| `VITE_API_BASE_URL` | no | Web API base URL. Production defaults to same-origin; `.env.example` sets `http://localhost:8787` for Vite development |

Demo mode uses a 24-dimensional collection and OpenAI mode uses a separate 1536-dimensional collection. Keep demo collection names ending in `_DEMO` if the guarded reset command should remain available.

## Repo Layout

```text
apps/web        React + Vite UI for chat, memory management, retrieval evidence, and Oracle inspection
services/api    Hono API exposing status, chat, memory CRUD, inspect, seed, and reset endpoints
packages/core   Mem0 configuration, deterministic embeddings, memory services, and answer generation
packages/db     Oracle configuration, node-oracledb pool, table inspection, and guarded reset helpers
packages/shared Shared TypeScript contracts and request validation
scripts/        CLI scripts for db:check, seed, reset, and live verification
samples/        Ten categorized sample-user memories loaded by the seed workflow
docs/           Article, local development guide, architecture, API notes, and troubleshooting
```

## Scripts

| Command | Description |
| --- | --- |
| `pnpm db:check` | Validate environment variables and test the Oracle connection |
| `pnpm seed` | Add any missing deterministic sample memories without creating duplicates |
| `pnpm reset` | Interactively drop only the configured Mem0 demo collection |
| `pnpm reset -- --yes` | Run the guarded demo reset non-interactively |
| `pnpm dev:api` | Run the Hono API on `:8787` with watch mode |
| `pnpm dev` | Run the Vite web app on `:5173` |
| `pnpm typecheck` | Type-check all workspace packages |
| `pnpm test` | Run the automated tests without live providers |
| `pnpm build` | Build the packages, API, and web app |
| `pnpm check` | Run type-checking, tests, and the production build |
| `pnpm check:live` | Exercise Oracle storage, search, update, deletion, and cleanup |
| `pnpm start` | Serve the compiled API and web app together on `:8787` |

## Docs

- [Article: Building a long-term memory assistant with Mem0, TypeScript, and Oracle](./docs/article.md)
- [Architecture and request flow](./docs/architecture.md)
- [API reference](./docs/api.md)
- [Local development](./docs/local-development.md)
- [Troubleshooting](./docs/troubleshooting.md)

## What Is Intentionally Not Here

- Production authentication. The sample uses two fixed demo users; production code must derive `user_id` from trusted identity.
- A production embedding policy. Deterministic embeddings keep no-key runs reproducible, while OpenAI mode is an optional example rather than a provider requirement.
- A production table lifecycle. The reset command is restricted to configured `MEM0_*_DEMO` collections and should not be pointed at production data.
- A separate vector database. Oracle AI Database is the vector store in both demo and OpenAI modes.
- Automatic learning in no-key mode. Add memories explicitly through **Memory explorer**, or enable OpenAI mode for Mem0 fact inference from chat turns.
- Production operations such as rate limiting, audit logging, retention/export workflows, and secret-manager integration.

## Learn More

- [Mem0 JavaScript and TypeScript integration with Oracle](https://docs.oracle.com/en/database/oracle/oracle-database/26/aintg/mem0-oracledb-integration-guide/mem0-javascript.html)
- [Oracle AI Vector Search overview](https://docs.oracle.com/en/database/oracle/oracle-database/26/vecse/overview-ai-vector-search.html)
- [Mem0 Open Source documentation](https://docs.mem0.ai/open-source)
