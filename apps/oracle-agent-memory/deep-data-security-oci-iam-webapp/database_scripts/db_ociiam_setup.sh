#!/usr/bin/env bash

# Configure this Autonomous Database to validate OCI IAM access tokens.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=database_scripts/_common.sh
source "${script_dir}/_common.sh"

deepsec_require_env \
    OAM_DEEPSEC_DSN \
    OAM_DEEPSEC_ADMIN_PASSWORD \
    OAM_DEEPSEC_OCI_DB_APP_ID \
    OAM_DEEPSEC_OCI_DOMAIN_URL \
    OAM_DEEPSEC_OCI_DB_CLIENT_ID \
    OAM_DEEPSEC_OCI_DB_CLIENT_SECRET

export OAM_DEEPSEC_ADMIN_USER="${OAM_DEEPSEC_ADMIN_USER:-ADMIN}"
deepsec_validate_oracle_identifier OAM_DEEPSEC_ADMIN_USER

admin_user="$OAM_DEEPSEC_ADMIN_USER"
database_app_id_sql="$(deepsec_sql_literal "$OAM_DEEPSEC_OCI_DB_APP_ID")"
domain_url_sql="$(deepsec_sql_literal "$OAM_DEEPSEC_OCI_DOMAIN_URL")"
database_client_id_sql="$(deepsec_sql_literal "$OAM_DEEPSEC_OCI_DB_CLIENT_ID")"
database_client_secret_sql="$(deepsec_sql_literal "$OAM_DEEPSEC_OCI_DB_CLIENT_SECRET")"

sqlplus -L -s /nolog <<SQL
whenever oserror exit failure
whenever sqlerror exit sql.sqlcode
set define off
set echo off

connect "${admin_user}"/"${OAM_DEEPSEC_ADMIN_PASSWORD}"@"${OAM_DEEPSEC_DSN}"

set serveroutput on
set lines 180

BEGIN
  DBMS_CLOUD_ADMIN.ENABLE_EXTERNAL_AUTHENTICATION(
    type => 'OCI_IAM',
    params => JSON_OBJECT(
      'app_id'     VALUE ${database_app_id_sql},
      'domain_url' VALUE ${domain_url_sql}
    ),
    force => TRUE
  );
END;
/

BEGIN
  BEGIN
    DBMS_CLOUD.DROP_CREDENTIAL(credential_name => 'OCI_IAM_DOMAIN_DB_CRED$');
  EXCEPTION
    WHEN OTHERS THEN
      IF SQLCODE NOT IN (-27476, -20000) THEN
        RAISE;
      END IF;
  END;

  DBMS_CLOUD.CREATE_CREDENTIAL(
    credential_name => 'OCI_IAM_DOMAIN_DB_CRED$',
    username        => ${database_client_id_sql},
    password        => ${database_client_secret_sql}
  );
END;
/

COLUMN name FORMAT A40
COLUMN value FORMAT A120
SELECT name, value
  FROM v\$parameter
 WHERE name IN ('identity_provider_type', 'identity_provider_oauth_config');

exit;
SQL
