#!/usr/bin/env bash

# Shared environment loading and validation for this standalone example.

set -euo pipefail

database_scripts_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "${database_scripts_dir}/.." && pwd)"
deepsec_env_file="${OAM_DEEPSEC_ENV_FILE:-${project_dir}/.deepsec.env}"

if [[ ! -r "$deepsec_env_file" ]]; then
    echo "ERROR: Deep Sec environment file is not readable: ${deepsec_env_file}" >&2
    echo "Copy deepsec.env.example to .deepsec.env or set OAM_DEEPSEC_ENV_FILE." >&2
    exit 1
fi

if ! command -v sqlplus >/dev/null 2>&1; then
    echo "ERROR: sqlplus must be installed and available on PATH." >&2
    exit 1
fi

set -a
# shellcheck disable=SC1090
source "$deepsec_env_file"
set +a

deepsec_require_env() {
    local variable_name
    for variable_name in "$@"; do
        if [[ -z "${!variable_name:-}" ]]; then
            echo "ERROR: ${variable_name} must be set in ${deepsec_env_file}." >&2
            exit 1
        fi
    done
}

deepsec_validate_oracle_identifier() {
    local variable_name="$1"
    local value="${!variable_name:-}"
    if [[ ! "$value" =~ ^[A-Za-z][A-Za-z0-9_$#]{0,127}$ ]]; then
        echo "ERROR: ${variable_name} must be a valid unquoted Oracle identifier." >&2
        exit 1
    fi
}

deepsec_sql_literal() {
    local value="$1"
    value="${value//\'/\'\'}"
    printf "'%s'" "$value"
}

if [[ -n "${OAM_DEEPSEC_CONFIG_DIR:-}" ]]; then
    export TNS_ADMIN="$OAM_DEEPSEC_CONFIG_DIR"
fi
