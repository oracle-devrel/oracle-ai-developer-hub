#!/usr/bin/env bash
set -euo pipefail
umask 077

# Runs as root. Feature inputs are data, never shell commands.
VERSION="${VERSION:-latest}"
ORAVIZ_MCP_REPO="${ORAVIZMCPREPO:-https://github.com/jasperan/oraviz-mcp}"
REMOTE_USER="${_REMOTE_USER:-root}"
ORACLE_USER="${ORACLEUSER:-oraviz_reader}"
ORACLE_PASSWORD="${ORACLEPASSWORD:-}"
ORACLE_HOST="${ORACLEHOST:-localhost}"
ORACLE_PORT="${ORACLEPORT:-1521}"
ORACLE_SERVICE="${ORACLESERVICE:-FREEPDB1}"

fail() {
    printf '%s\n' "$1" >&2
    exit 1
}

[[ "$REMOTE_USER" =~ ^[a-zA-Z_][a-zA-Z0-9_-]*\$?$ ]] || fail 'Invalid remote user'
[[ "$VERSION" =~ ^[a-zA-Z0-9][a-zA-Z0-9._/-]*$ ]] || fail 'Invalid version'
# HTTPS only; reject credentials, query strings, and shell/transport syntax.
[[ "$ORAVIZ_MCP_REPO" =~ ^https://[a-zA-Z0-9.-]+(:[0-9]+)?/[a-zA-Z0-9._/-]+$ ]] \
    || fail 'Repository must be an HTTPS URL without credentials or query parameters'

REMOTE_HOME="${_REMOTE_USER_HOME:-}"
if [[ -z "$REMOTE_HOME" ]]; then
    REMOTE_HOME="$(getent passwd "$REMOTE_USER" | cut -d: -f6)"
fi
[[ "$REMOTE_HOME" = /* && -d "$REMOTE_HOME" ]] || fail 'Remote user home is unavailable'
ENV_PATH="$REMOTE_HOME/.oraviz-mcp-env"
[[ ! -e "$ENV_PATH" && ! -L "$ENV_PATH" ]] || fail 'Environment file already exists; preserve or move it before reinstalling'

for name in ORACLE_USER ORACLE_PASSWORD ORACLE_HOST ORACLE_PORT ORACLE_SERVICE; do
    value="${!name}"
    # dotenv expands ${...} even inside single quotes. Runtime environment
    # injection is the supported path for secrets containing this sequence.
    if [[ "$value" == *$'\n'* || "$value" == *$'\r'* || "$value" == *'${'* ]]; then
        fail 'Connection options cannot contain newlines or dotenv interpolation; inject these secrets at runtime'
    fi
done

printf '%s\n' 'Setting up Oracle Viz MCP Server...'
(
    # The non-root devcontainer user must be able to build this source tree.
    # Credential-file creation below retains the outer private umask.
    umask 022
    mkdir -p /opt/oraviz-mcp
    cd /opt/oraviz-mcp
    if [[ "$VERSION" == latest ]]; then
        git clone -- "$ORAVIZ_MCP_REPO" .
    else
        git clone --no-checkout -- "$ORAVIZ_MCP_REPO" .
        git checkout --detach "$VERSION" --
    fi
)

# Create a private file atomically. Do not append stale credentials or suppress
# permission/write errors. dotenv quoting preserves literal shell metacharacters.
TEMP_ENV="$(mktemp "$REMOTE_HOME/.oraviz-mcp-env.XXXXXX")"
trap 'rm -f -- "$TEMP_ENV"' EXIT
write_setting() {
    local name="$1" value="$2"
    value="${value//\\/\\\\}"
    value="${value//\'/\\\'}"
    printf "%s='%s'\n" "$name" "$value"
}
{
    write_setting ORACLE_USER "$ORACLE_USER"
    # Omit empty passwords so an inherited runtime secret is not overwritten.
    if [[ -n "$ORACLE_PASSWORD" ]]; then
        write_setting ORACLE_PASSWORD "$ORACLE_PASSWORD"
    fi
    write_setting ORACLE_HOST "$ORACLE_HOST"
    write_setting ORACLE_PORT "$ORACLE_PORT"
    write_setting ORACLE_SERVICE "$ORACLE_SERVICE"
} > "$TEMP_ENV"
chmod 600 "$TEMP_ENV"
chown "$REMOTE_USER" "$TEMP_ENV"
mv -T -- "$TEMP_ENV" "$ENV_PATH"
trap - EXIT
