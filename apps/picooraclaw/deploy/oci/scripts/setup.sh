#!/bin/bash
# PicoOraClaw OCI Instance Setup Script
# Runs via cloud-init on first boot - fully unattended
set -euo pipefail
exec > >(tee -a /var/log/picooraclaw-setup.log) 2>&1

echo "=== PicoOraClaw setup started at $(date) ==="

ORACLE_MODE="${ORACLE_MODE:-freepdb}"
ORACLE_PWD="${ORACLE_PWD:-PicoOraclaw123}"
ADB_DSN="${ADB_DSN:-}"
ADB_WALLET_BASE64="${ADB_WALLET_BASE64:-}"

# -- 1. System packages --
echo "--- Installing system packages ---"
dnf install -y oracle-epel-release-el9
dnf install -y docker-engine git make gcc wget curl unzip python3
systemctl enable --now docker
usermod -aG docker opc

# -- 2. Install Go 1.24 --
echo "--- Installing Go 1.24 ---"
ARCH=$(uname -m)
case "$ARCH" in
  x86_64)  GOARCH="amd64" ;;
  aarch64) GOARCH="arm64" ;;
  *)       GOARCH="$ARCH" ;;
esac
wget -q "https://go.dev/dl/go1.24.0.linux-${GOARCH}.tar.gz" -O /tmp/go.tar.gz
rm -rf /usr/local/go
tar -C /usr/local -xzf /tmp/go.tar.gz
rm /tmp/go.tar.gz
export PATH="/usr/local/go/bin:$PATH"
echo 'export PATH="/usr/local/go/bin:$PATH"' >> /etc/profile.d/golang.sh
go version

# -- 3. Install Ollama --
echo "--- Installing Ollama ---"
curl -fsSL https://ollama.com/install.sh | sh
systemctl enable --now ollama
sleep 5
ollama pull gemma3:270m
echo "Ollama ready with gemma3:270m"

# -- 4. Build PicoOraClaw --
echo "--- Building PicoOraClaw ---"
git clone https://github.com/jasperan/picooraclaw.git /opt/picooraclaw
cd /opt/picooraclaw
make build
cp "build/picooraclaw-linux-${GOARCH}" /usr/local/bin/picooraclaw
chmod +x /usr/local/bin/picooraclaw
picooraclaw --version || true

# -- 5. Initialize config --
echo "--- Initializing config ---"
export HOME=/home/opc
sudo -u opc picooraclaw onboard <<< "n"

CONFIG_FILE="/home/opc/.picooraclaw/config.json"

# Patch config: set ollama provider and gemma3:270m model
python3 - "$CONFIG_FILE" <<'PYEOF'
import json, sys
path = sys.argv[1]
with open(path) as f:
    cfg = json.load(f)
cfg["agents"]["defaults"]["provider"] = "ollama"
cfg["agents"]["defaults"]["model"] = "gemma3:270m"
with open(path, "w") as f:
    json.dump(cfg, f, indent=2)
PYEOF

# -- 6. Oracle Database Setup --
echo "--- Setting up Oracle Database (mode: $ORACLE_MODE) ---"

if [ "$ORACLE_MODE" = "freepdb" ]; then
  # Pull and start Oracle DB Free container
  docker pull container-registry.oracle.com/database/free:latest
  docker run -d --name oracle-free \
    -p 1521:1521 \
    -e ORACLE_PWD="$ORACLE_PWD" \
    -e ORACLE_CHARACTERSET=AL32UTF8 \
    -v oracle-data:/opt/oracle/oradata \
    --restart unless-stopped \
    container-registry.oracle.com/database/free:latest

  echo "Waiting for Oracle DB to be ready..."
  TIMEOUT=300
  ELAPSED=0
  while ! docker logs oracle-free 2>&1 | grep -q "DATABASE IS READY"; do
    sleep 10
    ELAPSED=$((ELAPSED + 10))
    echo "  Waiting... ${ELAPSED}s"
    if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
      echo "ERROR: Oracle DB timed out after ${TIMEOUT}s"
      docker logs oracle-free --tail 50
      exit 1
    fi
  done
  echo "Oracle DB is ready"

  # Create picooraclaw user
  docker exec oracle-free sqlplus -S "sys/${ORACLE_PWD}@localhost:1521/FREEPDB1 as sysdba" <<SQL || true
WHENEVER SQLERROR CONTINUE
CREATE USER picooraclaw IDENTIFIED BY "${ORACLE_PWD}"
  DEFAULT TABLESPACE users QUOTA UNLIMITED ON users;
GRANT CONNECT, RESOURCE, DB_DEVELOPER_ROLE TO picooraclaw;
GRANT CREATE MINING MODEL TO picooraclaw;
EXIT;
SQL

  # Patch config for freepdb mode
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
PYEOF

elif [ "$ORACLE_MODE" = "adb" ]; then
  # ADB mode - wallet and DSN provided by Terraform
  if [ -n "$ADB_WALLET_BASE64" ]; then
    WALLET_DIR="/home/opc/.picooraclaw/wallet"
    mkdir -p "$WALLET_DIR"
    echo "$ADB_WALLET_BASE64" | base64 -d > "$WALLET_DIR/wallet.zip"
    cd "$WALLET_DIR" && unzip -o wallet.zip && cd -
    chown -R opc:opc "$WALLET_DIR"
  fi

  python3 - "$CONFIG_FILE" "$ORACLE_PWD" "$ADB_DSN" "${WALLET_DIR:-}" <<'PYEOF'
import json, sys
path, pwd, dsn = sys.argv[1], sys.argv[2], sys.argv[3]
wallet_path = sys.argv[4] if len(sys.argv) > 4 else ""
with open(path) as f:
    cfg = json.load(f)
cfg.setdefault("oracle", {}).update({
    "enabled": True,
    "mode": "adb",
    "dsn": dsn,
    "user": "picooraclaw",
    "password": pwd,
    "walletPath": wallet_path,
    "onnxModel": "ALL_MINILM_L12_V2",
    "agentId": "default"
})
with open(path, "w") as f:
    json.dump(cfg, f, indent=2)
PYEOF
fi

# -- 7. Initialize Oracle schema --
echo "--- Running setup-oracle ---"
sudo -u opc picooraclaw setup-oracle

# -- 8. Install and start gateway systemd service --
echo "--- Installing gateway service ---"
cat > /etc/systemd/system/picooraclaw-gateway.service <<'UNIT'
[Unit]
Description=PicoOraClaw Gateway
After=network-online.target docker.service ollama.service
Wants=network-online.target

[Service]
Type=simple
User=opc
ExecStart=/usr/local/bin/picooraclaw gateway
Restart=on-failure
RestartSec=10
Environment=HOME=/home/opc

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now picooraclaw-gateway

# -- 9. Done --
echo "=== PicoOraClaw setup completed at $(date) ==="
touch /var/log/picooraclaw-setup-complete
