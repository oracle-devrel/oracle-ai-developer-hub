# Troubleshooting

This guide covers common issues across the backend (Spring Boot), frontend (Oracle JET), OCI Generative AI Inference, Liquibase migrations, and Oracle ADB connectivity. It is organized into sections with steps for diagnosis and fixes. For quick answers, see FAQ.md.

## Sections

- [Generative AI API Errors](#generative-ai-api-errors)
- [Liquibase and DB Migrations](#liquibase-and-db-migrations)
- [Oracle ADB Connectivity](#oracle-adb-connectivity)
- [RAG Ingestion and Q&A](#rag-ingestion-and-qa)
- [Backend and UI](#backend-and-ui)
- [Performance Tips](#performance-tips)
- [Useful Commands](#useful-commands)
- [Q&A](#qa)

## Generative AI API Errors

### 400 Invalid parameter (presencePenalty) on xAI Grok
- Symptom: Error returned by Chat: “Model grok-4 does not support parameter presencePenalty” or “Invalid 'presencePenalty': This parameter is not supported by this model.”
- Steps: 1) Check MODELS.md for vendor constraints. 2) Backend omits penalties for Grok; update to recent build. 3) Test with curl omitting the param.

### Models list is empty or missing expected models
- Symptom: GET /api/genai/models returns empty array.
- Steps: 1) Verify genai.compartment_id and OCI credentials in application.yaml. 2) Ensure permissions for Generative AI. 3) Test curl; check region matches tenancy.

### Endpoint vs On-Demand confusion
- Symptom: 404 or auth errors on dedicated endpoint.
- Steps: 1) Set genai.serving.chat.mode to ON_DEMAND. 2) Remove endpoint OCID if present. 3) See MODELS.md for quick start.

## Liquibase and DB Migrations

### ORA-06550 / PLS-00103 “Encountered the symbol 'CREATE'”
- Symptom: Liquibase fails on startup at first CREATE after PL/SQL.
- Steps: 1) Ensure changeset uses endDelimiter:/ and splitStatements:false. 2) Add trailing / after END;. 3) See DATABASE.md for examples.

### Vector index creation fails
- Symptom: V2 KB migration attempts VECTOR index but fails silently.
- Steps: 1) Confirm Oracle AI Database supports VECTOR. 2) Script tries multiple syntaxes; if none work, embeddings store but ANN unavailable. 3) Upgrade DB.

### Embedding dimension mismatch
- Symptom: Poor similarity search or ingestion failures.
- Steps: 1) Check model dimension in MODELS.md. 2) Adjust VECTOR(1024, FLOAT32) in V2__kb_tables.sql. 3) Recreate table/index.

## Oracle ADB Connectivity

### Wallet not found / UnknownHost / Cannot resolve service
- Symptom: Datasource init fails.
- Steps: 1) Verify wallet unzipped with sqlnet.ora/tnsnames.ora. 2) Set JDBC URL with _high service and TNS_ADMIN path. 3) In K8s, mount secret to /opt/adb/wallet (K8S.md).

### Invalid credentials
- Symptom: ORA-01017 login denied.
- Steps: 1) Check spring.datasource.username/password. 2) Ensure user has CREATE TABLE/INDEX privileges. 3) Test with SQL Developer.

### Validate schema
- Symptom: Tables missing after startup.
- Steps: 1) Run SELECT COUNT(*) FROM conversations;. 2) Check for KB index: SELECT index_name FROM user_indexes WHERE index_name = 'KB_VEC_IDX';. 3) See DATABASE.md.

## RAG Ingestion and Q&A

### Upload fails
- Symptom: 500 or timeout on POST /api/upload.
- Steps: 1) Verify file path and size (<100MB). 2) Test curl -F "file=@/path". 3) Check backend logs for PDFBox errors.

### Answers don’t reflect your document
- Symptom: RAG ignores uploaded content.
- Steps: 1) Confirm ingestion: GET /api/kb/diag?tenantId=default (chunksTenant >0). 2) Ask specific questions. 3) Check tenant match.

### RAG returns no context / results=0
- Symptom: “I don’t know” despite uploads.
- Steps: 1) GET /api/kb/diag → check dbOk, chunksTenant, embeddingsNonNullTenant. 2) Confirm tenant. 3) If no vectors, fallback to text (upgrade DB).

## Backend and UI

### Backend not starting
- Symptom: Gradle/Spring errors on bootRun.
- Steps: 1) ./gradlew clean build. 2) Review logs for Liquibase/datasource. 3) Align with build.gradle (Spring Boot 3.2.x/Java 21).

### UI cannot connect to backend
- Symptom: CORS/network errors in console.
- Steps: 1) Ensure backend on 8080, UI on 8000. 2) Check browser console. 3) Verify backend accessible.

### WebSocket/STOMP errors
- Symptom: Stuck connecting or no messages.
- Steps: 1) Check backend config/CORS. 2) Test echo endpoint. 3) See stomp-interface.tsx.

### UI debug logging (quiet by default)
- Symptom: Minimal console output.
- Steps: 1) Enable: localStorage.setItem("debug", "1"); refresh. 2) Disable: localStorage.removeItem("debug").

### Gradle deprecation warnings (8.x → 9.0)
- Symptom: LenientConfiguration.getArtifacts(Spec) deprecated.
- Steps: 1) ./gradlew compileJava -Xlint:deprecation (app code clean). 2) ./gradlew build --warning-mode all. 3) See CHANGES.md.

## Performance Tips

- Adjust maxTokens/temperature in requests to control length/cost.
- Tune UCP pool sizes in application.yaml for concurrency.
- Monitor latency/tokens via interactions table.

## Useful Commands

- List models: curl http://localhost:8080/api/genai/models
- Upload PDF: curl -F "file=@/path/to/file.pdf" http://localhost:8080/api/upload
- Ask RAG: curl -X POST http://localhost:8080/api/genai/rag -H "Content-Type: application/json" -d '{"question":"What does section 2 cover?","modelId":"ocid1.generativeaimodel.oc1...."}'

## Q&A

Q: How do I debug Liquibase? A: Step 1: Check logs for ORA errors. Step 2: Verify changeset delimiters. Step 3: See DATABASE.md.

Q: Why no embeddings? A: Step 1: Check /api/kb/diag/embed. Step 2: Confirm model in MODELS.md. Step 3: Ensure VECTOR support.
