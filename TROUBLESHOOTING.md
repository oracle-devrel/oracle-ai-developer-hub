# Troubleshooting

This guide covers common issues across the backend (Spring Boot), frontend (Oracle JET), OCI Generative AI Inference, Liquibase migrations, and Oracle ADB connectivity.

## Generative AI API errors

### 400 Invalid parameter (presencePenalty) on xAI Grok
- Symptom:
  - Error returned by Chat: “Model grok-4 does not support parameter presencePenalty” or “Invalid 'presencePenalty': This parameter is not supported by this model.”
- Cause:
  - xAI Grok models do not support `presencePenalty` (and may reject other penalties/params).
- Fix:
  - Backend already omits `presencePenalty`, `frequencyPenalty`, and `topK` for vendor `xai`. Ensure you’re on a recent backend build.
  - See MODELS.md for vendor-specific parameter behavior.

### Models list is empty or missing expected models
- Check OCI credentials and compartment ID in `backend/src/main/resources/application.yaml` under `genai.*`.
- Ensure your user has permissions for Generative AI in the target compartment.
- Try listing models:
  ```bash
  curl http://localhost:8080/api/genai/models
  ```
- Confirm your selected region in config matches your tenancy (e.g., US_CHICAGO_1).

### Endpoint vs On-Demand confusion
- If you configured a dedicated endpoint, validate endpoint OCID and region.
- For quick start, prefer On-Demand mode (no endpoint required).

## Liquibase and DB migrations

### ORA-06550 / PLS-00103 “Encountered the symbol 'CREATE'”
- Symptom:
  - Liquibase fails on startup with an error at the first `CREATE` after a PL/SQL block.
- Cause:
  - Oracle requires a trailing slash (`/`) on a new line after `END;` for anonymous PL/SQL blocks. Liquibase must be configured to not split the block incorrectly.
- Fix:
  - Ensure your changeSet with PL/SQL uses `endDelimiter:/` (and `splitStatements:false` when needed) and that the block ends with:
    ```
    END;
    /
    ```
  - Optionally split the drop PL/SQL block and DDL statements into separate changeSets.
- See DATABASE.md for examples and best practices.

### Vector index creation fails
- Symptom:
  - V2 KB migration attempts to create a VECTOR index but fails silently; RAG still ingests data.
- Cause:
  - Oracle version may not support the attempted index syntax or VECTOR feature.
- Fix:
  - Ensure you’re using Oracle AI Database (version details for compatibility only) with VECTOR support.
  - The script tries multiple syntaxes; if none apply, embeddings are stored but ANN search is unavailable. Retrieval may fall back to basic filters. Upgrade DB for best results.

### Embedding dimension mismatch
- Symptom:
  - Similarity search quality is poor, or ingestion fails when populating `kb_embeddings`.
- Cause:
  - `VECTOR(1024, FLOAT32)` must match the embedding model’s output dimension.
- Fix:
  - Adjust the dimension in `V2__kb_tables.sql` to match your chosen embedding model.
  - Recreate the table/index (or add a new migration) if you change the dimension.

## Oracle ADB connectivity

### Wallet not found / UnknownHost / Cannot resolve service
- Ensure you downloaded and unzipped the ADB wallet to a directory containing `sqlnet.ora` and `tnsnames.ora`.
- Set the JDBC URL to use the `_high` service and reference the same `TNS_ADMIN` path:
  ```yaml
  spring:
    datasource:
      url: jdbc:oracle:thin:@DB_SERVICE_high?TNS_ADMIN=/ABSOLUTE/PATH/TO/WALLET
  ```
- On Kubernetes (OKE), create a secret from the wallet and mount it to `/opt/adb/wallet`, then set `TNS_ADMIN=/opt/adb/wallet`. See K8S.md.

### Invalid credentials
- Verify `spring.datasource.username` and `spring.datasource.password`.
- Check that the user has privileges to create tables/indexes (Liquibase runs at startup).

### Validate schema
- Use SQL Developer Web, or run:
  ```sql
  SELECT COUNT(*) FROM conversations;
  SELECT COUNT(*) FROM kb_documents;
  SELECT index_name FROM user_indexes WHERE index_name = 'KB_VEC_IDX';
  ```

## RAG ingestion and Q&A

### Upload fails
- Endpoint: `POST /api/upload` with `multipart/form-data` key `file`.
- Ensure the file path is correct and accessible; try:
  ```bash
  curl -F "file=@/absolute/path/to/document.pdf" http://localhost:8080/api/upload
  ```

### Answers don’t reflect your document
- Confirm ingestion succeeded and data exists in KB tables (see “Validate schema” above).
- Ask specific questions referencing known sections to verify.
- For large PDFs, check server logs; ingestion may take time.

### RAG returns no context / results=0
- Check diagnostics:
  - `GET /api/kb/diag?tenantId=default` → expect `dbOk: true`
  - Confirm `chunksTenant > 0` and ideally `embeddingsNonNullTenant > 0`
  - `GET /api/kb/diag/embed?text=test` → expect `ok: true` and `vectorLen ~ 1024`
- Tenant consistency:
  - Ensure the same tenant is used for both upload and queries (default: `default`).
- Driver note:
  - If you see a WARN “getGeneratedKeys failed (Invalid conversion requested)”, the backend falls back to `SELECT id ...` so chunk inserts still succeed. This is expected and safe.
- VECTOR not available:
  - If `to_vector(?)` and `VECTOR(?)` are unavailable, the backend inserts `NULL` embeddings, allowing text-based snippet fallback (less accurate). Upgrade DB for vector search.

## Backend and UI

### Backend not starting
- Run a clean build:
  ```bash
  cd backend && ./gradlew clean build && ./gradlew bootRun
  ```
- Review logs for Liquibase or datasource errors (wallet path, credentials, permissions).

### UI cannot connect to backend
- UI runs on http://localhost:8000, backend on http://localhost:8080
- Check browser console (CORS/network errors).
- Ensure backend is running and accessible.

### WebSocket/STOMP errors
- Verify the backend WebSocket/STOMP configuration and ports (if used by your UI features).
- Check that no proxies/firewalls are blocking WebSocket upgrades.

### UI debug logging (quiet by default)
- By default the UI minimizes console noise (success keepalives are silent after the first info line).
- Enable verbose client-side logs:
  ```js
  localStorage.setItem("debug", "1")
  ```
  Refresh the page. Use:
  ```js
  localStorage.removeItem("debug")
  ```
  to disable.

## Performance tips

- Adjust `maxTokens` and `temperature` in backend service code to control response length/cost and creativity.
- Tune UCP pool sizes in `application.yaml` for concurrency:
  ```yaml
  initial-pool-size, min-pool-size, max-pool-size
  ```
- Use telemetry (`interactions` table) to monitor latency and tokens.

## Useful commands

- List models:
  ```bash
  curl http://localhost:8080/api/genai/models
  ```
- Upload PDF:
  ```bash
  curl -F "file=@/path/to/file.pdf" http://localhost:8080/api/upload
  ```
- Ask RAG:
  ```bash
  curl -X POST http://localhost:8080/api/genai/rag \
    -H "Content-Type: application/json" \
    -d '{"question":"What does section 2 cover?","modelId":"ocid1.generativeaimodel.oc1...."}'
