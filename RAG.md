# RAG (Retrieval-Augmented Generation) Guide

This app supports Retrieval-Augmented Generation over your own PDFs. You upload documents; the backend indexes them into Oracle AI Database via Liquibase-managed KB tables. Questions are answered by grounding prompts with retrieved content using embeddings stored as VECTOR(1024, FLOAT32).

## How it works (high level)

- Upload: a PDF is uploaded to the backend.
- Ingest: the backend extracts text and persists it (and related metadata) into ADB KB tables.
- Retrieve: when you ask a question, the backend retrieves relevant chunks from the KB.
- Generate: the backend composes a prompt with retrieved context and calls OCI Generative AI (Cohere/Meta/xAI) to generate the final answer.

## Endpoints

- POST /api/upload
  - Multipart form-data with key "file"
  - Stores PDF content into the knowledge base for retrieval

- POST /api/genai/rag
  - JSON body with question and modelId
  - Executes the RAG pipeline and returns an answer string

## Example requests (curl)

- Upload a document:
```
curl -F "file=@/absolute/path/to/document.pdf" \
  http://localhost:8080/api/upload
```

- Ask a question:
```
curl -X POST http://localhost:8080/api/genai/rag \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Summarize section 2 for me.",
    "modelId": "ocid1.generativeaimodel.oc1...."
  }'
```

Notes:
- Use GET /api/genai/models to list supported models in your compartment and pick a modelId.
- Vendor-aware parameters: for xAI Grok the backend omits presencePenalty, frequencyPenalty, and topK to avoid 400 errors; see MODELS.md for full guidance.

## UI flow

- Open the web UI.
- Use the Upload panel to upload PDFs.
- In Settings, enable "Use RAG" and set Tenant (default is "default").
- In Chat, select a chat model and ask questions; the backend will use your KB to enhance prompts.

## Where data is stored

- Liquibase migrations create core tables (conversations, messages, memory, telemetry) and KB tables for RAG, including embeddings stored as VECTOR(1024, FLOAT32) with an ANN index where supported.
- See DATABASE.md for the exact schema overview and Liquibase details.

## Tips

- Large PDFs: ingestion can take longer; watch backend logs.
- Models: if you see 400 invalid parameter errors, switch to another model or vendor. The backend already omits unsupported parameters for xAI Grok.
- Validation: after uploading, ask targeted questions about the document content to verify KB ingestion.
- Tenant alignment: ensure the same tenant is used for both upload and chat queries; mismatch results in empty retrievals.

## End-to-end flow (detailed)

- Upload
  - Frontend posts to `POST /api/upload` with the file and headers (see below).
  - `PDFConvertorController` saves to storage, converts to text (PDF → text or uses plain text), and optionally triggers KB ingestion.
- Ingest
  - `KbIngestService` chunks the text and stores rows in:
    - `kb_documents` (document record)
    - `kb_chunks` (one row per chunk)
    - `kb_embeddings` (one row per chunk with `embedding VECTOR(1024, FLOAT32)`)
  - Embeddings are produced by OCI Generative AI Inference `EmbedText` using `OnDemandServingMode` with `genai.embed_model_id` (defaults to `cohere.embed-english-v3.0`).
  - If vector insert helpers are unavailable (`to_vector(?)` and `VECTOR(?)` both fail), a row is inserted with `NULL` embedding so retrieval can still fall back to text-based snippets.
- Retrieve
  - `RagService` performs top-K retrieval against `kb_embeddings` using `VECTOR_DISTANCE` where available.
  - If no vectors exist, it falls back to non-vector retrieval (e.g., recent or textual matches) to still provide some context.
- Generate
  - The final prompt is composed with retrieved context and sent to OCI Generative AI Chat using the user-selected chat model (separate from the embedding model).
  - Response is returned to the UI and stored in telemetry tables.

## API quick reference

- `GET /api/genai/models` — list available chat and embedding models in your compartment
- `POST /api/upload` (multipart)
  - form-data: `file=@...`
  - headers:
    - `X-RAG-Ingest: true` to ingest into KB on upload
    - `X-Tenant-Id: default` (or your tenant)
    - `modelId: <chat model id>` (optional; upload no longer requires it)
    - `Embedding-Model-Id: <embed model id>` (optional; override server default)
- `POST /api/genai/rag`
  - body: `{ "question": "...", "modelId": "ocid1.generativeaimodel.oc1...." }`
  - runs RAG pipeline and returns answer
- `GET /api/kb/diag?tenantId=default[&docId=...]`
  - returns DB health, tenant/doc counts, and recent docs list
- `GET /api/kb/diag/embed?text=hello[&modelId=...]`
  - calls EmbedText and returns `{ ok, modelId, vectorLen }`
- `GET /api/kb/diag/schema`
  - lists schema status for KB tables

## Tenant and model configuration

- Tenant
  - Default tenant is `"default"`. Use the same tenant value for both ingestion and query in Settings/UI.
- Models
  - Chat model (`genai.chat_model_id`) is independent from the embedding model (`genai.embed_model_id`).
  - The KB schema defines `VECTOR(1024, FLOAT32)`. Use a 1024-dimension embedding model (e.g., `cohere.embed-english-v3.0`) or update both the schema and the code paths if you choose a different dimension.
- Summarization
  - File summaries on upload use `genai.summarization_model_id` and are stored in interactions/telemetry.

## Validation checklist

1. Backend running and DB reachable:
   - `GET /api/kb/diag?tenantId=default` → expect `dbOk: true`
2. Embedding API functioning:
   - `GET /api/kb/diag/embed?text=test` → expect `ok: true` and `vectorLen ~ 1024`
3. Upload a PDF from the UI (Upload panel):
   - Confirm “Upload successful…” confirmation toast
   - In backend logs: chunk insert logs, and `got embedding for chunk ... (len=1024)` if vectors are available
4. Ask with RAG (Chat panel):
   - Enable RAG in Settings and use the same tenant as the upload
   - Ask targeted questions about the uploaded content

## Debug logging in the UI

- Enable verbose client-side logs by running in the browser console:
  ```js
  localStorage.setItem("debug", "1")
  ```
  Refresh the page. This enables detailed diagnostics (e.g., KB DIAG payloads) while keeping normal operation quiet.
- Disable with:
  ```js
  localStorage.removeItem("debug")
  ```
