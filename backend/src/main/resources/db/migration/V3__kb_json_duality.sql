-- liquibase formatted sql
-- Introduce JSON-first source of truth for documents and a JSON Relational Duality View.
-- This keeps ingestion JSON-native while preserving relational projections via the duality view.
-- Tested syntax may vary across Oracle AI Database releases; this script is defensive.

-- changeset victor:kb_json_duality_1_drop endDelimiter:/
-- comment: Drop DV + JSON table if present (idempotent dev workflow). Set v_drop=FALSE in prod.
DECLARE
  v_drop BOOLEAN := TRUE;
BEGIN
  IF v_drop THEN
    BEGIN EXECUTE IMMEDIATE 'DROP VIEW kb_documents_dv'; EXCEPTION WHEN OTHERS THEN NULL; END;
    BEGIN EXECUTE IMMEDIATE 'DROP TABLE kb_documents_json CASCADE CONSTRAINTS'; EXCEPTION WHEN OTHERS THEN NULL; END;
  END IF;
END;
/
-- rollback SELECT 1 FROM DUAL;

-- changeset victor:kb_json_duality_2_table
-- JSON source of truth. Keep doc_id aligned with existing schema to avoid join/key rewrites.
-- data JSON is expected to include at least: title (string), uri (string), tags (array)
CREATE TABLE kb_documents_json (
  doc_id     VARCHAR2(128) PRIMARY KEY,
  tenant_id  VARCHAR2(64) NOT NULL,
  data       JSON NOT NULL,
  created_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL
);
-- rollback DROP TABLE kb_documents_json;

-- changeset victor:kb_json_duality_3_index
CREATE INDEX idx_kb_docs_json_tenant ON kb_documents_json(tenant_id);
-- rollback DROP INDEX idx_kb_docs_json_tenant;

-- changeset victor:kb_json_duality_4_duality endDelimiter:/
-- JSON Relational Duality View projecting from kb_documents_json
-- NOTE: Some versions accept "CREATE JSON RELATIONAL DUALITY VIEW ... AS data FROM ... KEY doc_id"
-- If your version requires an explicit mapping clause, adjust accordingly.
BEGIN
  EXECUTE IMMEDIATE 'CREATE JSON RELATIONAL DUALITY VIEW kb_documents_dv AS data FROM kb_documents_json KEY doc_id';
EXCEPTION
  WHEN OTHERS THEN
    -- Fallback for environments lacking DV syntax: create a conventional projection view.
    -- This keeps the app functional while you upgrade DB to a DV-capable version.
    BEGIN
      EXECUTE IMMEDIATE '
        CREATE OR REPLACE VIEW kb_documents_dv AS
        SELECT
          j.doc_id                              AS doc_id,
          j.tenant_id                           AS tenant_id,
          JSON_VALUE(j.data, ''$.title'')       AS title,
          JSON_VALUE(j.data, ''$.uri'')         AS uri,
          JSON_QUERY(j.data, ''$.tags'')        AS tags_json,
          j.created_at                          AS created_at
        FROM kb_documents_json j
      ';
    EXCEPTION WHEN OTHERS THEN NULL;
    END;
END;
/
-- rollback DROP VIEW kb_documents_dv;

-- changeset victor:kb_json_duality_5_notes
-- DV usage notes (not executed):
-- 1) Insert JSON-first:
--    INSERT INTO kb_documents_json (doc_id, tenant_id, data)
--    VALUES (:docId, :tenantId, JSON(:jsonString));
-- 2) Read relational-style:
--    SELECT doc_id, tenant_id, title, uri, tags_json FROM kb_documents_dv WHERE tenant_id = :tenantId;
-- 3) Join with existing KB:
--    SELECT e.chunk_id, VECTOR_DISTANCE(e.embedding, TO_VECTOR(:q)) AS dist, v.title, v.uri
--    FROM kb_embeddings e
--    JOIN kb_chunks c ON c.id = e.chunk_id
--    JOIN kb_documents_dv v ON v.doc_id = c.doc_id
--    WHERE c.tenant_id = :tenantId
--    ORDER BY dist
--    FETCH FIRST :k ROWS ONLY;
