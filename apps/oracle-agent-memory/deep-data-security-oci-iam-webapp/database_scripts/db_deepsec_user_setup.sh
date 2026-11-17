#!/usr/bin/env bash

# Create the schema-owner and application-pool accounts for this example.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=database_scripts/_common.sh
source "${script_dir}/_common.sh"

deepsec_require_env \
    OAM_DEEPSEC_DSN \
    OAM_DEEPSEC_ADMIN_PASSWORD \
    OAM_DEEPSEC_OWNER_USER \
    OAM_DEEPSEC_OWNER_PASSWORD \
    OAM_DEEPSEC_APP_DB_USER \
    OAM_DEEPSEC_APP_POOL_PASSWORD

OAM_DEEPSEC_ADMIN_USER="${OAM_DEEPSEC_ADMIN_USER:-ADMIN}"
deepsec_validate_oracle_identifier OAM_DEEPSEC_ADMIN_USER
deepsec_validate_oracle_identifier OAM_DEEPSEC_OWNER_USER
deepsec_validate_oracle_identifier OAM_DEEPSEC_APP_DB_USER

admin_user="$OAM_DEEPSEC_ADMIN_USER"
owner_user="$OAM_DEEPSEC_OWNER_USER"
app_pool_user="$OAM_DEEPSEC_APP_DB_USER"

for password in \
    "$OAM_DEEPSEC_ADMIN_PASSWORD" \
    "$OAM_DEEPSEC_OWNER_PASSWORD" \
    "$OAM_DEEPSEC_APP_POOL_PASSWORD"; do
    if [[ "$password" == *'"'* || "$password" == *$'\n'* || "$password" == *$'\r'* ]]; then
        echo 'ERROR: Example passwords cannot contain double quotes or line breaks.' >&2
        exit 1
    fi
done

sqlplus -L -s /nolog <<SQL
whenever oserror exit failure
whenever sqlerror exit sql.sqlcode
set define off
set echo off

connect "${admin_user}"/"${OAM_DEEPSEC_ADMIN_PASSWORD}"@"${OAM_DEEPSEC_DSN}"

CREATE USER ${owner_user}
    IDENTIFIED BY "${OAM_DEEPSEC_OWNER_PASSWORD}"
    DEFAULT TABLESPACE DATA
    TEMPORARY TABLESPACE TEMP
    QUOTA UNLIMITED ON DATA;

GRANT CREATE SESSION,
      CREATE TABLE,
      CREATE SEQUENCE,
      CREATE VIEW,
      CREATE PROCEDURE,
      CREATE JOB
TO ${owner_user};

CREATE USER ${app_pool_user}
    IDENTIFIED BY "${OAM_DEEPSEC_APP_POOL_PASSWORD}";

GRANT CREATE SESSION,
      CREATE END USER SECURITY CONTEXT
TO ${app_pool_user};

exit;
SQL
