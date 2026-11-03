#!/usr/bin/env bash
# Runs after each Lite-image database startup. It is idempotent.
# This is database bootstrap, not tutorial RAG implementation.
set -euo pipefail

: "${ORACLE_PWD:?ORACLE_PWD must be set by the Oracle Free container}"

# Escape characters that have meaning in the PL/SQL literal and in Oracle's
# quoted password syntax. The escaped value is never printed.
ORACLE_PWD_SQL=$(printf '%s' "$ORACLE_PWD" | sed "s/'/''/g; s/\"/\"\"/g")

sqlplus -s / as sysdba <<SQL
WHENEVER SQLERROR EXIT SQL.SQLCODE
ALTER SESSION SET CONTAINER = FREEPDB1;

DECLARE
  tablespace_count NUMBER;
BEGIN
  SELECT COUNT(*) INTO tablespace_count
    FROM dba_tablespaces
   WHERE tablespace_name = 'TUTORIAL_DATA';
  IF tablespace_count = 0 THEN
    EXECUTE IMMEDIATE q'[
      CREATE TABLESPACE TUTORIAL_DATA
        DATAFILE '/opt/oracle/oradata/FREE/FREEPDB1/tutorial_data01.dbf'
        SIZE 256M
        AUTOEXTEND ON NEXT 64M MAXSIZE 2G
        EXTENT MANAGEMENT LOCAL
        SEGMENT SPACE MANAGEMENT AUTO
    ]';
  END IF;
END;
/

DECLARE
  user_count NUMBER;
BEGIN
  SELECT COUNT(*) INTO user_count
    FROM dba_users
   WHERE username = 'TUTORIAL_USER';
  IF user_count = 0 THEN
    EXECUTE IMMEDIATE 'CREATE USER TUTORIAL_USER IDENTIFIED BY "${ORACLE_PWD_SQL}" '
      || 'DEFAULT TABLESPACE TUTORIAL_DATA QUOTA UNLIMITED ON TUTORIAL_DATA';
  ELSE
    EXECUTE IMMEDIATE 'ALTER USER TUTORIAL_USER IDENTIFIED BY "${ORACLE_PWD_SQL}" '
      || 'DEFAULT TABLESPACE TUTORIAL_DATA QUOTA UNLIMITED ON TUTORIAL_DATA';
  END IF;
END;
/

-- OracleVS needs to create its own table. Its owner can create indexes on
-- that table without a broad CREATE ANY INDEX grant.
-- Agent Memory uses identity columns (CREATE SEQUENCE) and creates a managed
-- expiry-purge scheduler job (CREATE JOB). Both are narrowly scoped object
-- creation privileges for objects owned by TUTORIAL_USER.
GRANT CREATE SESSION, CREATE TABLE, CREATE SEQUENCE, CREATE JOB TO TUTORIAL_USER;
SQL
