-- Typed tables adapted from the published multi-tenant schema notebook:
-- https://github.com/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/multitenant_schema_walkthrough.ipynb
-- Statement separator for the companion loader: -- @statement

CREATE TABLE jev_guideline_memory (
  id              VARCHAR2(64)  PRIMARY KEY,
  tenant_id       VARCHAR2(64)  NOT NULL,
  user_id         VARCHAR2(64),
  agent_id        VARCHAR2(64),
  thread_id       VARCHAR2(64),              -- session identifier
  guideline_key   VARCHAR2(128) NOT NULL,
  guideline_value JSON          NOT NULL,
  version         NUMBER(10)    NOT NULL,
  valid_from      TIMESTAMP     NOT NULL,
  valid_until     TIMESTAMP,
  written_by      VARCHAR2(64)  NOT NULL,
  source_event_id VARCHAR2(64),
  created_at      TIMESTAMP     NOT NULL,
  deleted_at      TIMESTAMP
)

-- @statement

CREATE TABLE jev_persona_memory (
  id              VARCHAR2(64)  PRIMARY KEY,
  tenant_id       VARCHAR2(64)  NOT NULL,
  user_id         VARCHAR2(64),
  agent_id        VARCHAR2(64),
  thread_id       VARCHAR2(64),
  persona_key     VARCHAR2(64)  NOT NULL,
  persona_value   JSON,                      -- nullable: erased on right-to-forget
  confidence      NUMBER(3,2),
  written_by      VARCHAR2(64)  NOT NULL,
  source_event_id VARCHAR2(64),
  valid_from      TIMESTAMP     NOT NULL,
  valid_until     TIMESTAMP,
  created_at      TIMESTAMP     NOT NULL,
  deleted_at      TIMESTAMP
)

-- @statement

CREATE TABLE jev_entity_memory (
  id              VARCHAR2(64)  PRIMARY KEY,
  tenant_id       VARCHAR2(64)  NOT NULL,
  user_id         VARCHAR2(64),
  agent_id        VARCHAR2(64),
  thread_id       VARCHAR2(64),
  subject         VARCHAR2(256) NOT NULL,
  predicate       VARCHAR2(64)  NOT NULL,
  content         CLOB,                      -- nullable: erased on right-to-forget
  content_hash    VARCHAR2(64)  NOT NULL,
  content_json    JSON,
  embedding       VECTOR(384, FLOAT32),
  confidence      NUMBER(3,2)   NOT NULL,
  written_by      VARCHAR2(64)  NOT NULL,
  source_event_id VARCHAR2(64)  NOT NULL,
  version         NUMBER(10)    NOT NULL,
  superseded_by   VARCHAR2(64),
  valid_from      TIMESTAMP     NOT NULL,
  valid_until     TIMESTAMP,
  created_at      TIMESTAMP     NOT NULL,
  deleted_at      TIMESTAMP
)

-- @statement

CREATE TABLE jev_conversation_memory (
  event_id        VARCHAR2(64)  PRIMARY KEY,
  tenant_id       VARCHAR2(64)  NOT NULL,
  user_id         VARCHAR2(64),
  agent_id        VARCHAR2(64),
  thread_id       VARCHAR2(64)  NOT NULL,
  run_id          VARCHAR2(64)  NOT NULL,
  turn_index      NUMBER(10)    NOT NULL,
  event_type      VARCHAR2(32)  NOT NULL,
  role            VARCHAR2(32),
  payload         JSON          NOT NULL,
  token_cost      NUMBER(10),
  latency_ms      NUMBER(10),
  retention_class VARCHAR2(16)  DEFAULT 'short' NOT NULL,
  created_at      TIMESTAMP     NOT NULL
) PARTITION BY RANGE (created_at)
  INTERVAL (NUMTODSINTERVAL(1, 'DAY'))
  ( PARTITION p0 VALUES LESS THAN (TIMESTAMP '2026-01-01 00:00:00') )

-- @statement

CREATE TABLE jev_summarization_memory (
  id              VARCHAR2(64)  PRIMARY KEY,
  tenant_id       VARCHAR2(64)  NOT NULL,
  user_id         VARCHAR2(64),
  agent_id        VARCHAR2(64),
  thread_id       VARCHAR2(64),
  task_type       VARCHAR2(64)  NOT NULL,
  title           VARCHAR2(256) NOT NULL,
  summary         CLOB,                      -- nullable: erased on right-to-forget
  key_steps       JSON,
  outcome         VARCHAR2(64),
  artifacts       JSON,
  embedding       VECTOR(384, FLOAT32),
  confidence      NUMBER(3,2)   NOT NULL,
  written_by      VARCHAR2(64)  NOT NULL,
  source_event_id VARCHAR2(64)  NOT NULL,
  version         NUMBER(10)    NOT NULL,
  superseded_by   VARCHAR2(64),
  valid_from      TIMESTAMP     NOT NULL,
  valid_until     TIMESTAMP,
  completed_at    TIMESTAMP     NOT NULL,
  created_at      TIMESTAMP     NOT NULL,
  deleted_at      TIMESTAMP
)
