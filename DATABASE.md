# Database and Liquibase

This application uses Oracle Autonomous Database (ADB) to persist conversation history, long/short-term memories, telemetry, and a knowledge base (KB) for RAG. Schema changes are managed by Liquibase and applied automatically at backend startup.

Key files:
- backend/src/main/resources/db/changelog/db.changelog-master.yaml
- backend/src/main/resources/db/migration/V1__core_tables.sql
- backend/src/main/resources/db/migration/V2__kb_tables.sql

## What Liquibase brings

- Versioned, automated schema migrations (idempotent)
- Repeatable deployment to local and OKE
- Clear rollback strategy and audit of changes

## Schemas created

### V1__core_tables.sql (Core)

- conversations
  - conversation_id (PK), tenant_id, user_id, created_at, status
- messages
  - message_id (PK), conversation_id (FK), role, content, tokens_in/out, created_at
  - idx_messages_conv_created
- memory_long
  - conversation_id (PK, FK), summary_text, updated_at
- memory_kv
  - (conversation_id, key) PK, value_json, ttl_ts
- interactions (Telemetry)
  - id (identity PK), tenant_id, route, model_id, params_json, latency_ms, tokens_in/out, cost_est, created_at
  - idx_interactions_tenant_time

Why it helps:
- Durable chat history for analytics and compliance
- Long-term and key-value memory for better UX and tool state
- Telemetry for observability, cost/trend tracking, SLOs

### V2__kb_tables.sql (Knowledge Base for RAG)

- kb_documents
  - doc_id (PK), tenant_id, title, uri, mime, version, tags_json, hash, active, created_at
  - idx_kb_docs_tenant_active
- kb_chunks
  - id (identity PK), doc_id (FK), tenant_id, chunk_ix, text, source_meta
  - idx_kb_chunks_doc_ix, idx_kb_chunks_tenant_doc
- kb_embeddings
  - chunk_id (PK, FK), embedding VECTOR(1024, FLOAT32)
  - kb_vec_idx (vector index) created via best-effort PL/SQL block
- kb_chunks_with_docs (VIEW)
  - Convenience join of chunk + doc metadata

Why it helps:
- Structured storage of document chunks for retrieval
- Oracle Database 26ai VECTOR support for embeddings and ANN search (HNSW/IVF)
- KB supports accurate and explainable RAG pipelines

## ADB Connection (JDBC + Wallet)

application.yaml example:
```yaml
spring:
  datasource:
    driver-class-name: oracle.jdbc.OracleDriver
    url: jdbc:oracle:thin:@DB_SERVICE_high?TNS_ADMIN=/ABSOLUTE/PATH/TO/WALLET
    username: ADMIN
    password: "YOUR_PASSWORD"
    type: oracle.ucp.jdbc.PoolDataSource
    oracleucp:
      sql-for-validate-connection: SELECT 1 FROM dual
      connection-pool-name: pool1
      initial-pool-size: 5
      min-pool-size: 5
      max-pool-size: 10
```

Notes:
- Download the ADB Wallet from the OCI Console and unzip to a folder.
- The folder must contain sqlnet.ora and tnsnames.ora.
- Use the _high service name in the JDBC URL with the same TNS_ADMIN path.

## OKE: ADB Wallet

1) Create a K8S Secret from your wallet directory:
```bash
kubectl create secret generic adb-wallet --from-file=./wallet/ -n backend
```

2) Mount it and set TNS_ADMIN in the backend Deployment (deploy/k8s/backend/backend.yaml):
```yaml
spec:
  template:
    spec:
      volumes:
        - name: adb-wallet
          secret:
            secretName: adb-wallet
      containers:
        - name: backend
          volumeMounts:
            - name: adb-wallet
              mountPath: /opt/adb/wallet
          env:
            - name: TNS_ADMIN
              value: /opt/adb/wallet
```

3) Ensure application.yaml (or env) points JDBC URL to _high service with TNS_ADMIN=/opt/adb/wallet.

## Liquibase: PL/SQL + DDL tip

When a changeSet mixes an anonymous PL/SQL block (DECLARE...BEGIN...END;) followed by DDL (CREATE...), Oracle requires a trailing slash (/) on a new line after END; and Liquibase must be configured to avoid splitting the block incorrectly.

Patterns used in this repo:
- For drop blocks, we use endDelimiter:/ and/or splitStatements:false as needed in the formatted SQL.
- Example from V2:
```sql
-- changeset author:id endDelimiter:/
DECLARE
  ...
END;
/
```

If you create new changeSets:
- Option A: Split blocks: one changeSet for PL/SQL (with endDelimiter:/, splitStatements:false), another for DDL.
- Option B: Keep a single file but ensure the PL/SQL block ends with a slash and Liquibase parsing options are set.

## Verifying the schema

Connect with SQL Developer Web or SQL*Plus and run:
```sql
SELECT COUNT(*) FROM conversations;
SELECT COUNT(*) FROM kb_documents;

-- Check vector index exists (26ai):
SELECT index_name FROM user_indexes WHERE index_name = 'KB_VEC_IDX';

-- Optional: quick vector distance sanity check (requires embeddings)
-- Replace :tenant with your tenant; the vector literal below is illustrative only
SELECT c.id, VECTOR_DISTANCE(e.embedding, VECTOR('[0,0,0]')) AS dist
FROM kb_chunks c
JOIN kb_embeddings e ON e.chunk_id = c.id
WHERE c.tenant_id = 'default'
ORDER BY dist
FETCH FIRST 5 ROWS ONLY;
```

Quick REST diagnostics:
- GET /api/kb/diag?tenantId=default
- GET /api/kb/diag/schema
- GET /api/kb/diag/embed?text=test

## Troubleshooting

- ORA-06550 / PLS-00103 with "CREATE" after PL/SQL:
  - Missing "/" after END; or Liquibase not configured with a proper endDelimiter/splitStatements.
- UnknownHost / DB connection:
  - Verify tnsnames.ora service name matches URL, and TNS_ADMIN points to wallet directory.
- Vector index creation:
  - The script tries multiple syntaxes (HNSW/IVF). If none work (older DB version), embeddings still persist, but ANN search is disabled until supported.

## Additional notes

- Oracle driver generated keys:
  - Some environments return “Invalid conversion requested” when calling `getGeneratedKeys()` for identity columns.
  - The backend (KbIngestService) falls back to:
    ```sql
    SELECT id FROM kb_chunks WHERE doc_id = ? AND tenant_id = ? AND chunk_ix = ?
    ```
    to retrieve the generated key. Ingestion proceeds and transactions are committed.
- Embedding insert fallbacks:
  - The backend first tries `to_vector(?)`, then `VECTOR(?)`.
  - If both are unavailable, a row is inserted with `NULL` embedding to keep joins working; vector search will be unavailable until VECTOR is supported in your database version.
