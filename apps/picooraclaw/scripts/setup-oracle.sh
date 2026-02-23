#!/bin/bash
# setup-oracle.sh — One-shot Oracle AI Database setup for picooraclaw
#
# Usage:
#   ./scripts/setup-oracle.sh                  # uses default password
#   ./scripts/setup-oracle.sh MyPassword123    # custom password
#
# Requirements: docker, picooraclaw binary built (make build)

set -euo pipefail

ORACLE_PWD="${1:-PicoOraclaw123}"
CONTAINER_NAME="oracle-free"
ORACLE_IMAGE="container-registry.oracle.com/database/free:latest"
PICO_BIN="./build/picooraclaw-$(uname -s | tr '[:upper:]' '[:lower:]')-$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')"
CONFIG_FILE="$HOME/.picooraclaw/config.json"

# ── helpers ──────────────────────────────────────────────────────────────────
info()    { echo "  $*"; }
ok()      { echo "✓ $*"; }
fail()    { echo "✗ $*" >&2; exit 1; }
section() { echo; echo "── $* ─────────────────────────────────────────"; }

# ── preflight ─────────────────────────────────────────────────────────────────
section "Preflight"
command -v docker >/dev/null 2>&1 || fail "docker not found. Install Docker first."
[ -f "$PICO_BIN" ] || fail "Binary not found at $PICO_BIN. Run 'make build' first."
[ -f "$CONFIG_FILE" ] || fail "Config not found at $CONFIG_FILE. Run 'picooraclaw onboard' first."
ok "Prerequisites met"

# ── step 1: start Oracle container ───────────────────────────────────────────
section "Step 1/4: Oracle AI Database container"
if docker ps --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
    ok "Container '$CONTAINER_NAME' already running — skipping"
elif docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
    info "Restarting stopped container '$CONTAINER_NAME'..."
    docker start "$CONTAINER_NAME"
    ok "Container started"
else
    info "Pulling and starting Oracle AI Database (first run takes ~2 min)..."
    docker run -d --name "$CONTAINER_NAME" \
        -p 1521:1521 \
        -e ORACLE_PWD="$ORACLE_PWD" \
        -e ORACLE_CHARACTERSET=AL32UTF8 \
        -v oracle-data:/opt/oracle/oradata \
        "$ORACLE_IMAGE"
    ok "Container launched"
fi

info "Waiting for database to be ready..."
TIMEOUT=180
ELAPSED=0
while ! docker logs "$CONTAINER_NAME" 2>&1 | grep -q "DATABASE IS READY"; do
    sleep 5
    ELAPSED=$((ELAPSED + 5))
    printf "\r  Waiting... %ds" "$ELAPSED"
    [ "$ELAPSED" -ge "$TIMEOUT" ] && fail "Timed out after ${TIMEOUT}s. Check: docker logs $CONTAINER_NAME"
done
echo
ok "Oracle AI Database is ready"

# ── step 2: create database user ─────────────────────────────────────────────
section "Step 2/4: Database user"
info "Creating user 'picooraclaw' in FREEPDB1..."
docker exec "$CONTAINER_NAME" sqlplus -S "sys/${ORACLE_PWD}@localhost:1521/FREEPDB1 as sysdba" <<SQL 2>&1 | grep -v "^$" | sed 's/^/  /' || true
WHENEVER SQLERROR CONTINUE
CREATE USER picooraclaw IDENTIFIED BY "${ORACLE_PWD}"
  DEFAULT TABLESPACE users QUOTA UNLIMITED ON users;
GRANT CONNECT, RESOURCE, DB_DEVELOPER_ROLE TO picooraclaw;
GRANT CREATE MINING MODEL TO picooraclaw;
EXIT;
SQL
ok "User ready (already existed = fine)"

# ── step 3: patch config ──────────────────────────────────────────────────────
section "Step 3/4: Config"
info "Patching $CONFIG_FILE with Oracle settings..."
python3 - "$CONFIG_FILE" "$ORACLE_PWD" <<'PYEOF'
import json, sys
path, pwd = sys.argv[1], sys.argv[2]
with open(path) as f:
    cfg = json.load(f)
cfg.setdefault("oracle", {}).update({
    "enabled": True,
    "mode": "freepdb",
    "host": "localhost",
    "port": 1521,
    "service": "FREEPDB1",
    "user": "picooraclaw",
    "password": pwd,
    "onnxModel": "ALL_MINILM_L12_V2",
    "agentId": "default"
})
with open(path, "w") as f:
    json.dump(cfg, f, indent=2)
print("  patched successfully")
PYEOF
ok "Config updated"

# ── step 4: initialize schema + ONNX model ───────────────────────────────────
section "Step 4/4: Schema + ONNX model"
info "Running picooraclaw setup-oracle..."
"$PICO_BIN" setup-oracle

echo
echo "════════════════════════════════════════════════════════"
echo "  Oracle AI Database setup complete!"
echo "  Test with:"
echo "    $PICO_BIN agent -m \"Remember that I love Go\""
echo "    $PICO_BIN agent -m \"What language do I like?\""
echo "    $PICO_BIN oracle-inspect"
echo "════════════════════════════════════════════════════════"
