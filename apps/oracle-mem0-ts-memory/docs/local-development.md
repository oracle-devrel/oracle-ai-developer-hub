# Local development

## 1. Start Oracle Free

This app expects an Oracle Free pluggable database on port 1521. With the existing container:

```bash
podman start oracle-free
podman ps --filter name=oracle-free
```

Wait until its status is healthy. The default application connection string is `localhost:1521/FREEPDB1`.

## 2. Configure this app only

Copy `.env.example` to `.env` in the application root and fill in the Oracle values. The default `MEM0_MODE=demo` needs no model API key. The runtime resolves only that local file; it never reads the parent notebook `.env`. The private file is ignored by Git and the container build context.

Keep these values aligned:

- `MEM0_MODE=demo`
- `MEM0_DEMO_COLLECTION_NAME=MEM0_TS_LOCAL_DEMO` (24 dimensions)
- `MEM0_CREATE_VECTOR_INDEX=false` for the local demo

To opt into AI-generated answers and Mem0 fact inference later, set `MEM0_MODE=openai` and provide `OPENAI_API_KEY`. That mode uses the separate `MEM0_COLLECTION_NAME` and 1536-dimensional OpenAI embeddings.

## 3. Install and verify connectivity

```bash
pnpm install
pnpm db:check
```

The check names the collection and dimension and confirms the connection without printing credentials.

## 4. Start both development processes

Terminal one:

```bash
pnpm dev:api
```

Terminal two:

```bash
pnpm dev
```

Vite serves `http://localhost:5173` and proxies same-origin API requests to port 8787.

Open the app in Google Chrome on macOS with:

```bash
open -a "Google Chrome" http://localhost:5173
```

## 5. Seed, inspect, and reset

Use **Load demo memories** in the UI or run `pnpm seed`. Seed insertion is explicit (`infer: false`) so the written sentence becomes the memory. In no-key mode, chat retrieves and presents memories but does not automatically retain new facts; use **Memory explorer** to add them. In OpenAI mode, chat uses Mem0 inference to retain useful facts.

Choose **User 1** and ask, “What drink do I prefer, and where should I sit when travelling?” Then choose **User 2** and ask, “What should I order for lunch, and how should you format my meeting notes?”

`pnpm reset` asks you to type the configured collection name. Non-interactive runs must use `pnpm reset -- --yes`. The database package independently refuses any collection name that does not match `MEM0_*_DEMO`.

## 6. Verification

```bash
pnpm check
pnpm db:check
pnpm check:live
```

The automated suite does not require providers. In default demo mode, the live check needs only Oracle; it performs create, update, vector search, delete, and cleanup under a unique temporary user.

## Security boundaries

- Every memory operation requires a non-empty user id.
- Update and delete verify ownership before mutation.
- Provider error bodies are not exposed through the API.
- The web client receives status flags, never credentials or the connection string.
- Oracle identifiers are validated before interpolation; values use bind variables.
- Production is same-origin and does not enable broad CORS.
