#!/bin/bash
# serverStart.sh - Local-only setup runner for OCI Generative AI JET UI
# Goals:
# - Do NOT modify tracked project files (no edits to build.gradle or application-local.yaml)
# - Start a local Oracle ADB Free via Docker
# - Copy wallet to ./adb_wallet and (if needed) append a local alias in tnsnames.ora using portable sed (no grep -P)
# - Run backend with a temporary Spring override (Hikari pool + local admin credentials) via SPRING_CONFIG_ADDITIONAL_LOCATION
# - Optionally start the frontend
# - Robust health checks and clean shutdown
#
# Requirements: macOS, bash, Docker, Java 21+, Node 18+

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🚀 Starting Fully Local OCI Generative AI JET UI Setup${NC}"
echo "=============================================="

# Defaults (overridable via env)
CONTAINER_NAME="${CONTAINER_NAME:-adb-free}"
WALLET_DIR="${WALLET_DIR:-./adb_wallet}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-Welcome123456#}"
WALLET_PASSWORD="${WALLET_PASSWORD:-WalletPass123#}"
TNS_ALIAS="${TNS_ALIAS:-myatp_low}"
IMAGE="${IMAGE:-container-registry.oracle.com/database/adb-free:latest-23ai}"

# Flags (defaults)
BACKEND_ONLY=false
FRONTEND_ONLY=false
SKIP_DB=false
CLEAN=false

# Utilities
command_exists() { command -v "$1" >/dev/null 2>&1; }

port_in_use() {
  local port="$1"
  if command_exists lsof; then
    lsof -i TCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  elif command_exists netstat; then
    netstat -an | grep -E "LISTEN|LISTENING" | grep -qE "[\.:]$port[ \)]"
    return $?
  else
    return 1
  fi
}

ensure_ports_free() {
  local ports=("$@")
  local conflict=false
  for p in "${ports[@]}"; do
    if port_in_use "$p"; then
      echo -e "${RED}❌ Port $p is already in use. Close the process using it and retry.${NC}"
      conflict=true
    fi
  done
  if [ "$conflict" = true ]; then
    exit 1
  fi
}

# Checks
check_java() {
  echo -e "${YELLOW}☕ Checking Java runtime...${NC}"
  if ! command_exists java; then
    echo -e "${RED}❌ Java (JDK) 21+ required. Install from https://adoptium.net/ or brew install --cask temurin@21${NC}"
    exit 1
  fi
  local ver_raw
  ver_raw=$(java -version 2>&1 | awk -F\" '/version/ {print $2}')
  local major="${ver_raw%%.*}"
  if [[ "$major" =~ ^[0-9]+$ ]] && [ "$major" -ge 21 ]; then
    echo -e "${GREEN}✅ Java $ver_raw detected${NC}"
  else
    echo -e "${RED}❌ Java 21+ required. Current: $ver_raw${NC}"
    exit 1
  fi
}

check_node() {
  echo -e "${YELLOW}🌐 Checking Node.js...${NC}"
  if ! command_exists node; then
    echo -e "${RED}❌ Node.js 18+ required. Install via nvm or https://nodejs.org/${NC}"
    exit 1
  fi
  if node -e "const v=parseInt(process.version.slice(1)); process.exit(v>=18?0:1)"; then
    echo -e "${GREEN}✅ Node.js $(node -v) detected${NC}"
  else
    echo -e "${RED}❌ Node.js 18+ required. Current: $(node -v)${NC}"
    exit 1
  fi
}

check_docker() {
  echo -e "${YELLOW}🐳 Checking Docker...${NC}"
  if ! command_exists docker; then
    echo -e "${RED}❌ Docker is required. Install Docker Desktop for Mac.${NC}"
    exit 1
  fi
  echo -e "${GREEN}✅ Docker detected${NC}"
}

# Cleanup
cleanup() {
  echo -e "${YELLOW}🧹 Cleaning up old resources...${NC}"
  docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
  rm -rf "$WALLET_DIR"
  mkdir -p "$WALLET_DIR"
}

# Docker image
pull_image() {
  echo -e "${YELLOW}📥 Pulling Oracle ADB Free image...${NC}"
  local retries=3
  while [ $retries -gt 0 ]; do
    if docker pull "$IMAGE"; then
      echo -e "${GREEN}✅ Image pulled${NC}"
      return 0
    fi
    retries=$((retries-1))
    echo -e "${YELLOW}⚠️ Pull failed, retrying ($retries left)...${NC}"
    sleep 5
  done
  echo -e "${RED}❌ Failed to pull image after retries${NC}"
  exit 1
}

# Start container
start_container() {
  echo -e "${YELLOW}🚀 Starting ADB container...${NC}"
  ensure_ports_free 1521 1522 8443 27017
  docker run -d --name "$CONTAINER_NAME" \
    -p 1521:1521 -p 1522:1522 -p 8443:8443 -p 27017:27017 \
    -e WORKLOAD_TYPE=ATP \
    -e WALLET_PASSWORD="$WALLET_PASSWORD" \
    -e ADMIN_PASSWORD="$ADMIN_PASSWORD" \
    --cap-add SYS_ADMIN \
    --device /dev/fuse \
    "$IMAGE"
}

wait_healthy() {
  echo -e "${YELLOW}⏳ Waiting for ADB to be ready (up to 10min)...${NC}"
  local tries=120
  while [ $tries -gt 0 ]; do
    local state
    state=$(docker inspect --format '{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "unknown")
    if [ "$state" = "healthy" ]; then
      echo -e "${GREEN}✅ ADB is ready${NC}"
      return 0
    fi
    sleep 5
    tries=$((tries-1))
  done
  echo -e "${RED}❌ ADB did not become healthy in time. Check logs with: docker logs $CONTAINER_NAME${NC}"
  docker logs "$CONTAINER_NAME" || true
  exit 1
}

# Wallet copy and optional tns patch (portable sed)
copy_and_patch_wallet() {
  echo -e "${YELLOW}📂 Copying wallet...${NC}"
  docker cp "$CONTAINER_NAME:/u01/app/oracle/wallets/tls_wallet/." "$WALLET_DIR/"
  local tns="$WALLET_DIR/tnsnames.ora"

  # Prefer existing myatp_low_tls alias (ssl_server_dn_match=no) if present.
  if grep -q "myatp_low_tls" "$tns"; then
    echo -e "${GREEN}✅ Wallet has myatp_low_tls (DN match disabled). Using it as-is.${NC}"
    return 0
  fi

  # Else, append a local alias with DN match disabled, using service name extracted with portable sed.
  echo -e "${YELLOW}🛠️  Appending local TNS alias ($TNS_ALIAS) with DN match disabled...${NC}"
  local service_name
  service_name=$(sed -n '/myatp_low[[:space:]]*=/,/[)]/ { /service_name[[:space:]]*=/s/.*service_name[[:space:]]*=[[:space:]]*\([^)]*\).*/\1/p }' "$tns" || true)
  if [ -z "$service_name" ]; then
    service_name="myatp_low.adb.oraclecloud.com"
  fi
  cat >> "$tns" <<EOF

$TNS_ALIAS =
  (DESCRIPTION =
    (ADDRESS = (PROTOCOL = tcps)(PORT = 1522)(HOST = localhost))
    (CONNECT_DATA =
      (SERVICE_NAME = $service_name)
    )
    (SECURITY = (SSL_SERVER_DN_MATCH = FALSE))
  )
EOF
  echo -e "${GREEN}✅ TNS alias $TNS_ALIAS added (SERVICE_NAME=$service_name)${NC}"
}

# Backend
start_backend() {
  echo -e "${YELLOW}🔧 Starting backend...${NC}"
  # Create local override (do not change tracked files)
  mkdir -p "$WALLET_DIR"
  cat > "$WALLET_DIR/local-override.yaml" <<EOF
spring:
  datasource:
    # Use local admin user inside the ADB Free container for simple local dev
    username: admin
    password: "$ADMIN_PASSWORD"
    # Force Hikari (avoid UCP ClassCast issues seen in logs for local)
    type: com.zaxxer.hikari.HikariDataSource
    hikari:
      connection-test-query: SELECT 1 FROM DUAL
      idle-timeout: 30000
      max-lifetime: 60000
      connection-timeout: 30000
      keepalive-time: 10000
      leak-detection-threshold: 30000
logging:
  level:
    com.zaxxer.hikari: DEBUG
    org.hibernate.SQL: DEBUG
    com.oracle.jdbc: DEBUG
liquibase:
  enabled: false  # Temporarily disable for testing; re-enable for migrations
EOF

  pushd backend >/dev/null
  # Build without upgrading project dependencies; user controls repo deps
  ./gradlew clean build
  export TNS_ADMIN="../$WALLET_DIR"
  # Use local profile and override config file, do not touch application-local.yaml
  SPRING_PROFILES_ACTIVE=local \
  SPRING_CONFIG_ADDITIONAL_LOCATION="file:../$WALLET_DIR/local-override.yaml" \
  ./gradlew bootRun > ../backend.log 2>&1 &

  BACKEND_PID=$!
  popd >/dev/null
}

wait_backend_health() {
  echo -e "${YELLOW}⏳ Waiting for backend health (up to 15min)...${NC}"
  local tries=180
  while [ $tries -gt 0 ]; do
    if curl -sf http://localhost:8080/actuator/health | grep -q '"status":"UP"'; then
      echo -e "${GREEN}✅ Backend is UP${NC}"
      return 0
    fi
    echo -e "${YELLOW}Checking health (tries left: $tries)...${NC}"
    tail -n 5 backend.log || true
    sleep 5
    tries=$((tries-1))
  done
  echo -e "${RED}❌ Backend did not start. Tail of backend.log:${NC}"
  tail -n 80 backend.log || true
  exit 1
}

# Frontend
start_frontend() {
  echo -e "${YELLOW}🌟 Starting frontend...${NC}"
  pushd app >/dev/null
  if [ ! -d node_modules ]; then
    npm ci
  fi
  npm run serve &
  FRONTEND_PID=$!
  popd >/dev/null
}

# Cleanup
cleanup_on_exit() {
  echo -e "${YELLOW}🛑 Stopping application...${NC}"
  [ ! -z "${BACKEND_PID:-}" ] && kill "$BACKEND_PID" 2>/dev/null || true
  [ ! -z "${FRONTEND_PID:-}" ] && kill "$FRONTEND_PID" 2>/dev/null || true
  docker stop "$CONTAINER_NAME" 2>/dev/null || true
  docker rm "$CONTAINER_NAME" 2>/dev/null || true
  rm -f backend.log "$WALLET_DIR/local-override.yaml"
  exit
}

show_usage() {
  cat <<USAGE
Usage: $0 [OPTIONS]

Options:
  -h, --help          Show help
  --backend-only      Start only DB + backend
  --frontend-only     Start only frontend (no DB/backend)
  --skip-db           Skip DB setup (assume ADB container already running)
  --clean             Force clean wallet/container before start

Notes:
- This script does NOT modify tracked project files.
- Backend runs with a temporary Spring override file and Hikari CP.
- Wallet is copied to ./adb_wallet.
USAGE
  exit 0
}

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) show_usage ;;
    --backend-only) BACKEND_ONLY=true ;;
    --frontend-only) FRONTEND_ONLY=true ;;
    --skip-db) SKIP_DB=true ;;
    --clean) CLEAN=true ;;
    *) echo -e "${RED}Unknown option: $1${NC}"; show_usage ;;
  esac
  shift
done

# Main
check_java
check_node

if [ "$FRONTEND_ONLY" != true ] && [ "$SKIP_DB" != true ]; then
  check_docker
fi

trap cleanup_on_exit INT TERM

if [ "$CLEAN" = true ]; then
  cleanup
fi

if [ "$FRONTEND_ONLY" = true ]; then
  start_frontend
else
  if [ "$SKIP_DB" = false ]; then
    cleanup
    pull_image
    start_container
    wait_healthy
    copy_and_patch_wallet
  else
    # Ensure wallet dir exists if skipping DB (user keeps their container)
    mkdir -p "$WALLET_DIR"
    if [ ! -f "$WALLET_DIR/tnsnames.ora" ]; then
      echo -e "${YELLOW}⚠️ Skipping DB but wallet not found in $WALLET_DIR. Backend may fail to connect.${NC}"
    fi
  fi

  start_backend
  wait_backend_health

  if [ "$BACKEND_ONLY" != true ]; then
    start_frontend
  fi
fi

echo -e "${GREEN}🎉 Application started!${NC}"
echo "Backend:  http://localhost:8080  (health: /actuator/health)"
echo "Frontend: http://localhost:8000"
echo "DB:       Container '$CONTAINER_NAME' (logs: docker logs $CONTAINER_NAME)"
echo "Press Ctrl+C to stop"

wait
