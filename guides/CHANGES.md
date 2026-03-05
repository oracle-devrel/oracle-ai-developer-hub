# Changelog

## How to Use This Changelog
This changelog documents changes in reverse chronological order, building on previous versions. Each entry includes sections like Added, Changed, Fixed for modularity. Use it to track evolution and learn from updates. Cross-reference with README.md for overview and SERVICES_GUIDE.md for backend details.

## [2026-03-05]
### Added
- Guides: New comprehensive guide `AGENT_MEMORY_SPRING_AI_ORACLE_AI_DATABASE.md` covering AI agent memory architecture with Spring AI, OCI GenAI, and Oracle AI Database (migrated/expanded from specFile.md).
- DevRel: Platform-optimized articles in `devrel-writes/oci-genai-jet-ui/`:
  - Medium: Thought leadership on cognitive architecture and enterprise impact.
  - dev.to: Technical deep dive with code snippets and best practices.
  - DataCamp: Hands-on tutorial with step-by-step implementation exercises.
- Cross-references: Updated README.md and DATABASE.md with links to new guide.

### Changed
- Branding: Enforced "Oracle AI Database" throughout new content; corrected legacy "23ai" references.
- Backend memory architecture alignment:
  - Added `ProceduralMemoryService` to persist workflow state in `memory_kv` using `workflow.*` keys.
  - Updated `/api/genai/rag` flow to persist episodic user/assistant turns and refresh rolling summary after response.
  - Added tag-aware filtering in `RagService` retrieval SQL paths (`VECTOR`, regex fallback, recency fallback).
  - Hardened backend `application.yaml` with environment-driven datasource/OCI/memory settings.
- Java baseline upgrade for backend runtime/build:
  - Updated backend toolchain/source compatibility from Java 17 to Java 21 in `backend/build.gradle`.
  - Updated Gradle toolchain guidance in `backend/gradle.properties` to Java 21.
  - Updated local guides/scripts references to Java 21 (`guides/LOCAL.md`, `guides/FAQ.md`, `guides/TROUBLESHOOTING.md`, `local/serverStart.sh`, `local/localStart.sh`).
- Setup docs resilience improvements:
  - Updated `guides/K8S.md` and `guides/LOCAL.md` to avoid requiring `nvm` explicitly.
  - Environment setup now validates `node -v`/`npm -v` with Node.js 18+ requirement and uses `npm ci`.
  - Added Podman-specific OCIR pull-secret remediation in `guides/K8S.md` for `ImagePullBackOff` / `Unauthorized` scenarios.

### Fixed
- RAG interactions now contribute to durable episodic memory instead of being transient-only responses.
- Retrieval now honors request `tags` filters across all retrieval fallbacks.

### Build
- Backend tests could not be executed in this environment due to local JDK/Gradle incompatibility (`Unsupported class file major version 69` with Gradle semantic analysis under Java 25 only runtime present). Code-level test additions were made but runtime verification is pending Java 17/21 toolchain availability.
- Java 21 verification run was not executed in this pass by request (no local JDK installation). Local machine currently exposes Java 25 only.

### Documentation
- All new content includes secure placeholders (no real secrets), Mermaid diagrams, and repo links.

## [2025-11-04]
### Added
- UI: Added a visible Close button to the Settings drawer on mobile, allowing users to return to the main page.
- Scripts: Added --target flag to scripts/setenv.mjs to scope setup to app, backend, or all (default: all).
- DevRel: Added platform-specific articles on agent memory (Medium, dev.to, DataCamp) under devrel-writes/oci-genai-jet-ui/, enforcing “Oracle AI Database” branding.

### Fixed
- Backend: Replaced deprecated OCI Generative AI SDK constructor usage in `OCIGenAIService` with the supported builder API. No functional changes.

### Build
- Gradle: Observed a Gradle 8.x deprecation warning from build tooling (`LenientConfiguration.getArtifacts(Spec)`). Application code compiles cleanly. Refer to the Gradle 9.0 upgrade guide when updating plugins/Gradle.

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
  - Attempts `to_vector(?)` then `VECTOR(?)` with a JSON array literal
  - If both fail, insert NULL embedding (joins still work; no vector search)

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

## Q&A
Q: How do I contribute a new feature? A: See CONTRIBUTING.md for PR guidelines, then add an entry here under the appropriate section.
Q: What does the 'Build' section cover? A: Non-functional updates to tooling or dependencies, like Gradle warnings, that don't affect runtime but improve development.
