"""Database schema definitions for ragcli."""

def get_create_schemas_sql(config: dict) -> list:
    """Return list of SQL statements to create schemas based on config."""
    dimension = config['vector_index']['dimension']

    DOCUMENTS_TABLE = f"""
CREATE TABLE DOCUMENTS (
    document_id         VARCHAR2(36) PRIMARY KEY,
    filename            VARCHAR2(512) NOT NULL,
    file_format         VARCHAR2(10) NOT NULL,  -- TXT, MD, PDF
    file_size_bytes     NUMBER NOT NULL,
    extracted_text_size_bytes NUMBER,
    upload_timestamp    TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_modified       TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    chunk_count         NUMBER NOT NULL,
    total_tokens        NUMBER NOT NULL,
    embedding_dimension NUMBER DEFAULT {dimension},
    approximate_embedding_size_bytes NUMBER,
    ocr_processed       VARCHAR2(1) DEFAULT 'N',
    status              VARCHAR2(20) DEFAULT 'READY',  -- PROCESSING, READY, ERROR
    metadata_json       CLOB,
    created_at          TIMESTAMP DEFAULT SYSTIMESTAMP,
    updated_at          TIMESTAMP DEFAULT SYSTIMESTAMP
);
"""

    CHUNKS_TABLE = f"""
CREATE TABLE CHUNKS (
    chunk_id            VARCHAR2(36) PRIMARY KEY,
    document_id         VARCHAR2(36) NOT NULL,
    chunk_number        NUMBER NOT NULL,
    chunk_text          CLOB NOT NULL,
    token_count         NUMBER NOT NULL,
    character_count     NUMBER NOT NULL,
    start_position      NUMBER,
    end_position        NUMBER,
    chunk_embedding     VECTOR({dimension}, FLOAT32),
    embedding_model     VARCHAR2(50),
    created_at          TIMESTAMP DEFAULT SYSTIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES DOCUMENTS(document_id) ON DELETE CASCADE,
    CONSTRAINT unique_chunk_per_doc UNIQUE(document_id, chunk_number)
);
"""

    QUERIES_TABLE = f"""
CREATE TABLE QUERIES (
    query_id            VARCHAR2(36) PRIMARY KEY,
    query_text          CLOB NOT NULL,
    query_embedding     VECTOR({dimension}, FLOAT32),
    embedding_model     VARCHAR2(50),
    selected_documents  VARCHAR2(2000),  -- Comma-separated doc IDs
    top_k               NUMBER DEFAULT 5,
    similarity_threshold NUMBER DEFAULT 0.5,
    response_text       CLOB,
    response_tokens     NUMBER,
    response_time_ms    NUMBER,
    embedding_time_ms   NUMBER,
    search_time_ms      NUMBER,
    generation_time_ms  NUMBER,
    retrieved_chunks    VARCHAR2(4000),  -- JSON: chunk IDs and scores
    status              VARCHAR2(20),    -- SUCCESS, FAILED, PARTIAL
    error_message       VARCHAR2(500),
    created_at          TIMESTAMP DEFAULT SYSTIMESTAMP
);
"""

    QUERY_RESULTS_TABLE = """
CREATE TABLE QUERY_RESULTS (
    result_id           VARCHAR2(36) PRIMARY KEY,
    query_id            VARCHAR2(36) NOT NULL,
    chunk_id            VARCHAR2(36) NOT NULL,
    similarity_score    FLOAT,
    rank                NUMBER,
    created_at          TIMESTAMP DEFAULT SYSTIMESTAMP,
    FOREIGN KEY (query_id) REFERENCES QUERIES(query_id) ON DELETE CASCADE,
    FOREIGN KEY (chunk_id) REFERENCES CHUNKS(chunk_id) ON DELETE CASCADE
);
"""

    SESSIONS_TABLE = """
CREATE TABLE SESSIONS (
    session_id          VARCHAR2(36) PRIMARY KEY,
    created_at          TIMESTAMP DEFAULT SYSTIMESTAMP,
    last_active         TIMESTAMP DEFAULT SYSTIMESTAMP,
    title               VARCHAR2(500),
    summary             CLOB,
    metadata_json       JSON
);
"""

    SESSION_TURNS_TABLE = """
CREATE TABLE SESSION_TURNS (
    turn_id             VARCHAR2(36) PRIMARY KEY,
    session_id          VARCHAR2(36) NOT NULL,
    turn_number         NUMBER NOT NULL,
    user_query          CLOB NOT NULL,
    rewritten_query     CLOB,
    response            CLOB,
    trace_id            VARCHAR2(36),
    chunk_ids_json      CLOB,
    created_at          TIMESTAMP DEFAULT SYSTIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES SESSIONS(session_id) ON DELETE CASCADE
);
"""

    KG_ENTITIES_TABLE = f"""
CREATE TABLE KG_ENTITIES (
    entity_id           VARCHAR2(36) PRIMARY KEY,
    entity_name         VARCHAR2(500) NOT NULL,
    entity_type         VARCHAR2(50) NOT NULL,
    description         CLOB,
    embedding           VECTOR({dimension}, FLOAT32),
    metadata_json       JSON,
    first_seen_doc      VARCHAR2(36),
    mention_count       NUMBER DEFAULT 1,
    created_at          TIMESTAMP DEFAULT SYSTIMESTAMP,
    FOREIGN KEY (first_seen_doc) REFERENCES DOCUMENTS(document_id) ON DELETE SET NULL
);
"""

    KG_RELATIONSHIPS_TABLE = """
CREATE TABLE KG_RELATIONSHIPS (
    rel_id              VARCHAR2(36) PRIMARY KEY,
    source_id           VARCHAR2(36) NOT NULL,
    target_id           VARCHAR2(36) NOT NULL,
    rel_type            VARCHAR2(50) NOT NULL,
    description         CLOB,
    weight              NUMBER DEFAULT 1.0,
    chunk_id            VARCHAR2(36),
    document_id         VARCHAR2(36),
    created_at          TIMESTAMP DEFAULT SYSTIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES KG_ENTITIES(entity_id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES KG_ENTITIES(entity_id) ON DELETE CASCADE,
    FOREIGN KEY (chunk_id) REFERENCES CHUNKS(chunk_id) ON DELETE SET NULL,
    FOREIGN KEY (document_id) REFERENCES DOCUMENTS(document_id) ON DELETE SET NULL
);
"""

    KG_ENTITY_CHUNKS_TABLE = """
CREATE TABLE KG_ENTITY_CHUNKS (
    entity_id           VARCHAR2(36) NOT NULL,
    chunk_id            VARCHAR2(36) NOT NULL,
    PRIMARY KEY (entity_id, chunk_id),
    FOREIGN KEY (entity_id) REFERENCES KG_ENTITIES(entity_id) ON DELETE CASCADE,
    FOREIGN KEY (chunk_id) REFERENCES CHUNKS(chunk_id) ON DELETE CASCADE
);
"""

    AGENT_TRACES_TABLE = """
CREATE TABLE AGENT_TRACES (
    trace_id            VARCHAR2(36) PRIMARY KEY,
    query_id            VARCHAR2(36),
    session_id          VARCHAR2(36),
    created_at          TIMESTAMP DEFAULT SYSTIMESTAMP,
    FOREIGN KEY (query_id) REFERENCES QUERIES(query_id) ON DELETE SET NULL,
    FOREIGN KEY (session_id) REFERENCES SESSIONS(session_id) ON DELETE SET NULL
);
"""

    TRACE_STEPS_TABLE = """
CREATE TABLE TRACE_STEPS (
    step_id             VARCHAR2(36) PRIMARY KEY,
    trace_id            VARCHAR2(36) NOT NULL,
    agent_role          VARCHAR2(20) NOT NULL,
    input_data          CLOB,
    output_data         CLOB,
    reasoning           CLOB,
    duration_ms         NUMBER,
    token_count         NUMBER,
    step_order          NUMBER NOT NULL,
    created_at          TIMESTAMP DEFAULT SYSTIMESTAMP,
    FOREIGN KEY (trace_id) REFERENCES AGENT_TRACES(trace_id) ON DELETE CASCADE
);
"""

    FEEDBACK_TABLE = """
CREATE TABLE FEEDBACK (
    feedback_id         VARCHAR2(36) PRIMARY KEY,
    query_id            VARCHAR2(36),
    chunk_id            VARCHAR2(36),
    target_type         VARCHAR2(20) NOT NULL,
    rating              NUMBER NOT NULL,
    comment_text        CLOB,
    created_at          TIMESTAMP DEFAULT SYSTIMESTAMP,
    FOREIGN KEY (query_id) REFERENCES QUERIES(query_id) ON DELETE SET NULL,
    FOREIGN KEY (chunk_id) REFERENCES CHUNKS(chunk_id) ON DELETE SET NULL
);
"""

    CHUNK_QUALITY_TABLE = """
CREATE TABLE CHUNK_QUALITY (
    chunk_id            VARCHAR2(36) PRIMARY KEY,
    positive_count      NUMBER DEFAULT 0,
    negative_count      NUMBER DEFAULT 0,
    quality_score       NUMBER DEFAULT 0.5,
    last_updated        TIMESTAMP DEFAULT SYSTIMESTAMP,
    FOREIGN KEY (chunk_id) REFERENCES CHUNKS(chunk_id) ON DELETE CASCADE
);
"""

    EVAL_RUNS_TABLE = """
CREATE TABLE EVAL_RUNS (
    run_id              VARCHAR2(36) PRIMARY KEY,
    eval_mode           VARCHAR2(20) NOT NULL,
    started_at          TIMESTAMP DEFAULT SYSTIMESTAMP,
    completed_at        TIMESTAMP,
    avg_faithfulness    NUMBER,
    avg_relevance       NUMBER,
    avg_context_precision NUMBER,
    avg_context_recall  NUMBER,
    total_pairs         NUMBER DEFAULT 0,
    config_snapshot     CLOB
);
"""

    EVAL_RESULTS_TABLE = """
CREATE TABLE EVAL_RESULTS (
    result_id           VARCHAR2(36) PRIMARY KEY,
    run_id              VARCHAR2(36) NOT NULL,
    document_id         VARCHAR2(36),
    question            CLOB NOT NULL,
    expected_answer     CLOB,
    actual_answer       CLOB,
    faithfulness        NUMBER,
    relevance           NUMBER,
    context_precision   NUMBER,
    context_recall      NUMBER,
    chunk_ids_json      CLOB,
    duration_ms         NUMBER,
    created_at          TIMESTAMP DEFAULT SYSTIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES EVAL_RUNS(run_id) ON DELETE CASCADE
);
"""

    SYNC_SOURCES_TABLE = """
CREATE TABLE SYNC_SOURCES (
    source_id           VARCHAR2(36) PRIMARY KEY,
    source_type         VARCHAR2(20) NOT NULL,
    source_path         VARCHAR2(2000) NOT NULL,
    glob_pattern        VARCHAR2(500),
    poll_interval       NUMBER DEFAULT 300,
    enabled             NUMBER(1) DEFAULT 1,
    last_sync           TIMESTAMP,
    metadata_json       JSON,
    created_at          TIMESTAMP DEFAULT SYSTIMESTAMP
);
"""

    SYNC_EVENTS_TABLE = """
CREATE TABLE SYNC_EVENTS (
    event_id            VARCHAR2(36) PRIMARY KEY,
    source_id           VARCHAR2(36) NOT NULL,
    file_path           VARCHAR2(2000) NOT NULL,
    event_type          VARCHAR2(20) NOT NULL,
    document_id         VARCHAR2(36),
    chunks_added        NUMBER DEFAULT 0,
    chunks_removed      NUMBER DEFAULT 0,
    chunks_unchanged    NUMBER DEFAULT 0,
    processed_at        TIMESTAMP DEFAULT SYSTIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES SYNC_SOURCES(source_id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES DOCUMENTS(document_id) ON DELETE SET NULL
);
"""

    return [
        ("DOCUMENTS", DOCUMENTS_TABLE),
        ("CHUNKS", CHUNKS_TABLE),
        ("QUERIES", QUERIES_TABLE),
        ("QUERY_RESULTS", QUERY_RESULTS_TABLE),
        ("SESSIONS", SESSIONS_TABLE),
        ("SESSION_TURNS", SESSION_TURNS_TABLE),
        ("KG_ENTITIES", KG_ENTITIES_TABLE),
        ("KG_RELATIONSHIPS", KG_RELATIONSHIPS_TABLE),
        ("KG_ENTITY_CHUNKS", KG_ENTITY_CHUNKS_TABLE),
        ("AGENT_TRACES", AGENT_TRACES_TABLE),
        ("TRACE_STEPS", TRACE_STEPS_TABLE),
        ("FEEDBACK", FEEDBACK_TABLE),
        ("CHUNK_QUALITY", CHUNK_QUALITY_TABLE),
        ("EVAL_RUNS", EVAL_RUNS_TABLE),
        ("EVAL_RESULTS", EVAL_RESULTS_TABLE),
        ("SYNC_SOURCES", SYNC_SOURCES_TABLE),
        ("SYNC_EVENTS", SYNC_EVENTS_TABLE),
    ]

# TODO: Auto-select index type based on data size (HNSW/IVF/HYBRID)
