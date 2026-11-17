# Troubleshooting

## Oracle connection fails

Run `pnpm db:check`. Confirm the Oracle Free container is healthy, port 1521 is published, the service name is correct, and the credentials in this app's `.env` can open a session. Local defaults commonly use `localhost:1521/FREEPDB1`.

## OpenAI returns 429

This matters only in `MEM0_MODE=openai`. For a no-cost workflow, set `MEM0_MODE=demo` and restart the API. That uses local deterministic embeddings and extractive answers while keeping Oracle as the vector store.

## Dimension mismatch

The Oracle vector column and embedding output must have the same dimension. Demo mode uses 24 dimensions in `MEM0_TS_LOCAL_DEMO`; OpenAI mode defaults to 1536 dimensions in `MEM0_TS_MEMORY_DEMO`. Never point both modes at one collection. If you change the OpenAI dimension after creating its table, reset that mode's demo collection before inserting new data.

## Reset is refused

This is intentional. `pnpm reset` accepts only uppercase Oracle identifiers matching `MEM0_*_DEMO`, preventing accidental deletion of unrelated tables.

## pnpm reports blocked build scripts

The workspace policy explicitly permits only the native/build packages required here: `oracledb`, `better-sqlite3`, and `esbuild`. Do not broadly approve dependency scripts.
