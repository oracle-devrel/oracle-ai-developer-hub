#!/usr/bin/env bash

# Inspect Deep Data Security roles, grants, policies, and protected objects.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=database_scripts/_common.sh
source "${script_dir}/_common.sh"

deepsec_require_env OAM_DEEPSEC_DSN OAM_DEEPSEC_ADMIN_PASSWORD

export OAM_DEEPSEC_ADMIN_USER="${OAM_DEEPSEC_ADMIN_USER:-ADMIN}"
deepsec_validate_oracle_identifier OAM_DEEPSEC_ADMIN_USER
admin_user="$OAM_DEEPSEC_ADMIN_USER"

sqlplus -L -s /nolog <<SQL
whenever oserror exit failure
whenever sqlerror exit sql.sqlcode
set define off
set echo off

connect "${admin_user}"/"${OAM_DEEPSEC_ADMIN_PASSWORD}"@"${OAM_DEEPSEC_DSN}"

set lines 240
set pages 200
set long 4000
set longchunksize 4000

PROMPT ========================================================================
PROMPT Database target
PROMPT ========================================================================
COLUMN db_name FORMAT A20
COLUMN service_name FORMAT A70
SELECT SYS_CONTEXT('USERENV', 'DB_NAME') AS db_name,
       SYS_CONTEXT('USERENV', 'SERVICE_NAME') AS service_name
  FROM dual;

PROMPT ========================================================================
PROMPT Deep Data Security roles and external IAM mappings
PROMPT ========================================================================
COLUMN data_role FORMAT A70
COLUMN mapped_to FORMAT A100
SELECT data_role, mapped_to
  FROM dba_data_roles
 ORDER BY data_role;

PROMPT ========================================================================
PROMPT Data role grants
PROMPT ========================================================================
COLUMN role_type FORMAT A16
COLUMN grantee FORMAT A70
COLUMN grantee_type FORMAT A24
SELECT data_role, role_type, grantee, grantee_type
  FROM dba_data_role_grants
 ORDER BY data_role, grantee_type, grantee;

PROMPT ========================================================================
PROMPT Data grants and row predicates
PROMPT ========================================================================
COLUMN owner FORMAT A20
COLUMN grant_name FORMAT A65
COLUMN privilege FORMAT A12
COLUMN object_owner FORMAT A20
COLUMN object_name FORMAT A50
COLUMN grantee FORMAT A60
COLUMN grantee_type FORMAT A16
COLUMN predicate FORMAT A100 WORD_WRAPPED
SELECT owner,
       grant_name,
       privilege,
       object_owner,
       object_name,
       grantee,
       grantee_type,
       use_data_grants_only,
       predicate
  FROM dba_data_grants
 WHERE grant_name IS NOT NULL
 ORDER BY owner, grant_name, privilege, grantee;

PROMPT ========================================================================
PROMPT Objects with mandatory Deep Data Security enforcement enabled
PROMPT ========================================================================
SELECT DISTINCT object_owner, object_name
  FROM dba_data_grants
 WHERE use_data_grants_only = TRUE
 ORDER BY object_owner, object_name;

PROMPT ========================================================================
PROMPT Local Deep Sec end users (external OCI IAM users are not listed here)
PROMPT ========================================================================
COLUMN username FORMAT A50
COLUMN account_status FORMAT A24
COLUMN authentication_type FORMAT A20
SELECT username, account_status, authentication_type
  FROM dba_end_users
 ORDER BY username;

exit;
SQL
