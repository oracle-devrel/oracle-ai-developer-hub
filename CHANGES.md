# Changelog

## [2025-11-03]
### Changed
- Updated branding in README to "Oracle AI Database"; removed legacy 23ai/26ai phrasing in keywords and branding mentions.
- Clarified references to "Oracle Autonomous Database (ADB)" where appropriate.
- UI: Moved model selector to the top of the main content and auto-selected the default model.
- UI: Removed backend service selection controls from Settings.
- UI: Removed the "Check RAG status" button from Settings.
- UI: Renamed "Document Upload" to "RAG Knowledge Base" and updated the "Upload" option label under "AI service options" to "RAG Knowledge Base".
- UI: Removed theme selector; UI is fixed to light mode.
- Backend/Runtime: Java-only backend for both local development and production; removed Python backend usage from UI and scripts.
- Security: Removed mixed-content calls and localhost Python endpoints; all frontend requests use same-origin Java /api/* paths.
- Scripts: Hardened serverStart.sh with set -euo pipefail, Node.js ≥ 18 and Java ≥ 17 checks, backend health readiness (Actuator), and graceful shutdown trap.
- Frontend: Removed WebSocket Python paths and websocket-interface usage; STOMP/REST is used universally for chat; RAG always uses Java endpoint.
- Upload/Summary: Document upload and summarization call only Java endpoints; "RAG Knowledge Base" wording applied consistently.
- Cleanup: Removed backend selection logic and Python-specific fallbacks; minimized attack surface by deleting unused code paths.

- Upload: Increased max PDF/TXT upload size to 100 MB across frontend and backend; UI messages updated to show MB.
- Backend: Configured spring.servlet.multipart max-file-size and max-request-size to 100MB in application.yaml and application-local.yaml; /api/upload now validates up to 100 MB.
- PDF parsing: Switched to PDFBox RandomAccessReadBufferedFile + Loader.loadPDF(RandomAccessRead) for streaming large, image-heavy PDFs.
- Kubernetes: Added nginx.ingress.kubernetes.io/proxy-body-size: "100m" to Ingress to allow 100 MB uploads.

This project recently received multiple backend and frontend enhancements to stabilize RAG ingestion/retrieval with Oracle AI Database and reduce noisy logs in the UI.

## 2025-10-21

### RAG ingestion stabilized (Oracle AI Database + Liquibase V2)
- Fix: chunk inserts now persist even when the Oracle driver cannot return generated keys via `getGeneratedKeys()`.
  - KbIngestService wraps `getGeneratedKeys()` in try/catch and falls back to:
    ```sql
    SELECT id FROM kb_chunks WHERE doc_id = ? AND tenant_id = ? AND chunk_ix = ?
    ```
  - Result: no transaction aborts; chunks are always inserted.
- Observability:
  - Logs before and after chunk insert:
    - `insertChunk: docId=... ix=... textLen=... metaLen=... metaSnippet=...`
    - `insertChunk: executed insert for docId=... ix=...`
  - WARN only when `getGeneratedKeys` fails (e.g., “Invalid conversion requested”), followed by fallback SELECT.

### Embeddings with OCI Generative AI Inference (decoupled from chat)
- Default embedding model is configured via `genai.embed_model_id` (e.g., `cohere.embed-english-v3.0`, 1024-dim).
- Embeddings are invoked through `GenerativeAiInferenceClient` using `EmbedTextDetails` with `OnDemandServingMode`.
- Chat model (`genai.chat_model_id`) remains separate and is not used for embeddings.
- Summarization for uploads uses `genai.summarization_model_id`.

### KB schema and vector index (Liquibase)
- `V2__kb_tables.sql` provides:
  - `kb_documents`, `kb_chunks`, `kb_embeddings` with `embedding VECTOR(1024, FLOAT32)`.
  - Multiple vector index creation attempts (HNSW/IVF and an older `USING ... WITH(...)` form) to cover DB variations.
- Insertion of embeddings:
  - Attempts `to_vector(?)` then `VECTOR(?)`.
  - If both fail, inserts a row with `NULL` embedding so joins still produce snippets (fallback retrieval still works).

### Diagnostics endpoints
- `GET /api/kb/diag?tenantId=default`
  - Returns `dbOk`, tenant-level counts (`docsTenant`, `chunksTenant`, `embeddingsTenant`, `embeddingsNonNullTenant`), recent docs list.
- `GET /api/kb/diag?tenantId=...&docId=...`
  - Adds per-doc counts.
- `GET /api/kb/diag/embed?text=... [&modelId=...]`
  - Calls OCI EmbedText and returns `ok`, `modelId`, `vectorLen` (expect ~1024 for default).
- `GET /api/kb/diag/schema`
  - Lists existence and columns for KB tables.

### Upload API and frontend behavior
- Upload controller (`/api/upload`) now treats `modelId` header as optional. Upload and ingest don&#39;t require the chat model.
- Frontend upload UI:
  - Removed the warning “No model selected. Upload will proceed without model context.”
  - Sends `modelId` header only if a model is selected.
  - After a successful upload, runs KB diagnostics; detailed JSON logs only when debug mode is enabled (see below).

### UI/UX improvements
- DB keepalive (JET UI startup):
  - On first successful ping: logs a single `DB: database active`.
  - Subsequent successes are quiet; failures warn; recovery logs an info.
- Chat input bar is fixed at the bottom of the viewport. The list area has extra bottom padding to avoid overlap.
- Introduced opt-in debug logging:
  - New helper: `app/src/libs/debug.ts`
  - Enable with `localStorage.setItem("debug", "1")` (per browser tab).
  - Use `localStorage.removeItem("debug")` to disable.
  - Verbose logs (e.g., KB DIAG payloads, internal scroll keys) only appear in debug mode, while warnings/errors remain visible.

### How to validate end-to-end
1. Backend config:
   - Set `genai.region`, `genai.compartment_id`, and datasource wallet/TNS in `application.yaml`.
   - Set `genai.embed_model_id` to a 1024-dim model (default: `cohere.embed-english-v3.0`) or adjust the migration and code if you use a different dimension.
   - Optionally adjust `genai.chat_model_id` and `genai.summarization_model_id`.
2. Start backend and web:
   - Watch logs for Spring/Liquibase startup and KB DIAG pings (`DB: database active`).
3. Verify diagnostics:
   - `GET /api/kb/diag?tenantId=default` ➜ `dbOk: true`
   - `GET /api/kb/diag/embed?text=test` ➜ `ok: true`, `vectorLen ~ 1024`
4. Upload a PDF in the UI (X-RAG-Ingest is enabled by the frontend):
   - Expect backend logs:
     - `KB ingest: chunking produced N chunks`
     - `insertChunk: ... executed insert ...`
     - Optional `getGeneratedKeys failed ... Falling back to SELECT id ...` (non-fatal)
     - `got embedding for chunk ... (len=1024)` or fallback to NULL embeddings.
   - UI shows “Upload successful...” confirmation.
5. Ask with RAG in Chat:
   - Enable RAG in Settings and keep the same tenant (`default` by default).
   - Ask a question about the document; backend logs show `RAG.topK ... results=N` (expect N>0 with embeddings or at least text fallback snippets).

### Troubleshooting tips
- RAG returns “I don’t know...”:
  - Check `/api/kb/diag` for `chunksTenant` and `embeddingsNonNullTenant`.
  - Confirm tenant consistency between upload and query.
  - If VECTOR DDL isn&#39;t supported, NULL embeddings will be inserted and a regex/recency fallback will still produce snippets (less accurate).
- Liquibase ORA-06550/PLS-00103:
  - Ensure changesets with PL/SQL blocks use `endDelimiter: /` or `splitStatements: false` as done in `V2__kb_tables.sql`.
- `getGeneratedKeys` fails:
  - This is handled by the fallback; ensure the WARN is present once and ingestion completes.

### File changes (high-level)
- Backend:
  - `KbIngestService`: resilient generated-key handling; detailed per-chunk logs; clear embedding insert fallback path.
  - `PDFConvertorController`: `modelId` header is optional.
  - `KbDiagController`: added `/diag/embed` & `/diag/schema` endpoints.
  - Liquibase: `db/migration/V2__kb_tables.sql`.
- Frontend:
  - `app.tsx`: DB keepalive quieted; debug logging gated.
  - `upload.tsx`: made model header optional; diagnostic logs moved to debug.
  - `chat.tsx`: switched noisy logs to debug.
  - `styles/app.css`: fixed chat input bar at bottom; added bottom padding for the list.
  - `libs/debug.ts`: new helper for opt-in debug logs.
