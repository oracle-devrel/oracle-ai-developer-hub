#!/bin/bash

# localStart.sh - Fully Local Setup Script for OCI Generative AI JET UI
# This script sets up a local Oracle ADB via Docker, patches wallet for connections,
# creates DB user, and starts backend/frontend. Everything managed in ./adb_wallet/.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Fully Local OCI Generative AI JET UI Setup${NC}"
echo "=============================================="

# Default values (can be overridden via env vars)
CONTAINER_NAME="adb-free"
WALLET_DIR="./adb_wallet"
ADMIN_PASSWORD="Welcome123456#"
WALLET_PASSWORD="WalletPass123#"
USER_PASSWORD="GenAiPass123#"
TNS_ALIAS="myatp_low"
IMAGE="container-registry.oracle.com/database/adb-free:latest-23ai"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Java 21+
check_java() {
    echo -e "${YELLOW}☕ Checking Java runtime...${NC}"
    if ! command_exists java; then
        echo -e "${RED}❌ Java (JDK) 21+ is required but not found. Install from https://adoptium.net/ or brew install --cask temurin@21.${NC}"
        exit 1
    fi
    JAVA_VERSION_RAW=$(java -version 2>&1 | awk -F\" '/version/ {print $2}')
    JAVA_MAJOR=${JAVA_VERSION_RAW%%.*}
    if [[ "$JAVA_MAJOR" =~ ^[0-9]+$ ]] && [ "$JAVA_MAJOR" -ge 21 ]; then
        echo -e "${GREEN}✅ Java $JAVA_VERSION_RAW detected${NC}"
    else
        echo -e "${RED}❌ Java 21+ is required. Current: $JAVA_VERSION_RAW${NC}"
        exit 1
    fi
}

# Check Node.js 18+
check_node() {
    echo -e "${YELLOW}🌐 Checking Node.js...${NC}"
    if ! command_exists node; then
        echo -e "${RED}❌ Node.js 18+ is required but not found. Install via nvm or https://nodejs.org/.${NC}"
        exit 1
    fi
    NODE_VERSION=$(node -v | sed 's/v//')
    if node -e "const v=process.version.match(/^v(\d+)/)[1]; process.exit(v>=18?0:1)"; then
        echo -e "${GREEN}✅ Node.js $NODE_VERSION detected${NC}"
    else
        echo -e "${RED}❌ Node.js 18+ is required. Current: $NODE_VERSION${NC}"
        exit 1
    fi
}

# Check Docker
check_docker() {
    echo -e "${YELLOW}🐳 Checking Docker...${NC}"
    if ! command_exists docker; then
        echo -e "${RED}❌ Docker is required but not found. Install from https://www.docker.com/ or brew install --cask docker.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Docker detected${NC}"
}

# Cleanup old container and wallet
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up old resources...${NC}"
    docker rm -f $CONTAINER_NAME 2>/dev/null || true
    rm -rf $WALLET_DIR
    mkdir -p $WALLET_DIR
}

# Pull Docker image with retries
pull_image() {
    echo -e "${YELLOW}📥 Pulling Oracle ADB Free image...${NC}"
    local retries=3
    while [ $retries -gt 0 ]; do
        if docker pull $IMAGE; then
            echo -e "${GREEN}✅ Image pulled${NC}"
            return 0
        fi
        retries=$((retries - 1))
        echo -e "${YELLOW}⚠️ Pull failed, retrying ($retries left)...${NC}"
        sleep 5
    done
    echo -e "${RED}❌ Failed to pull image after retries${NC}"
    exit 1
}

# Start container
start_container() {
    echo -e "${YELLOW}🚀 Starting ADB container...${NC}"
    docker run -d --name $CONTAINER_NAME \
        -p 1521:1521 -p 1522:1522 -p 8443:8443 -p 27017:27017 \
        -e WORKLOAD_TYPE=ATP \
        -e WALLET_PASSWORD="$WALLET_PASSWORD" \
        -e ADMIN_PASSWORD="$ADMIN_PASSWORD" \
        --cap-add SYS_ADMIN \
        --device /dev/fuse \
        $IMAGE
}

# Wait for container healthy
wait_healthy() {
    echo -e "${YELLOW}⏳ Waiting for ADB to be ready (up to 10min)...${NC}"
    local tries=120  # 10min with 5s intervals
    while [ $tries -gt 0 ]; do
        HEALTH=$(docker inspect --format '{{.State.Health.Status}}' $CONTAINER_NAME 2>/dev/null || echo "unknown")
        if [ "$HEALTH" = "healthy" ]; then
            echo -e "${GREEN}✅ ADB is ready${NC}"
            return 0
        fi
        sleep 5
        tries=$((tries - 1))
    done
    echo -e "${RED}❌ ADB did not start in time. Check docker logs $CONTAINER_NAME${NC}"
    docker logs $CONTAINER_NAME
    exit 1
}

# Copy and patch wallet
patch_wallet() {
    echo -e "${YELLOW}📂 Copying and patching wallet...${NC}"
    docker cp $CONTAINER_NAME:/u01/app/oracle/wallets/tls_wallet/. $WALLET_DIR/
    
    # Extract SERVICE_NAME from original tnsnames.ora for myatp_low (portable for macOS)
    ORIGINAL_TNS="$WALLET_DIR/tnsnames.ora"
    SERVICE_NAME=$(sed -n '/myatp_low =/,/))/ { /service_name /s/.*service_name = \([^)]*\).*/\1/p }' $ORIGINAL_TNS || echo "myatp_low.adb.oraclecloud.com")

    # Append or update myatp_low with TCPS and no DN match (to avoid SSL issues)
    cat >> $ORIGINAL_TNS <<EOF

$TNS_ALIAS =
  (DESCRIPTION =
    (ADDRESS = (PROTOCOL = tcps)(PORT = 1522)(HOST = localhost))
    (CONNECT_DATA =
      (SERVICE_NAME = $SERVICE_NAME)
    )
    (SECURITY = (SSL_SERVER_DN_MATCH = FALSE))
  )
EOF
    echo -e "${GREEN}✅ Wallet patched with $TNS_ALIAS using SERVICE_NAME=$SERVICE_NAME${NC}"
}


# Start backend
start_backend() {
    echo -e "${YELLOW}🔧 Starting backend...${NC}"
    # Ensure wallet dir exists for override file
    mkdir -p "$WALLET_DIR"
    # Generate local Spring override to avoid changing project files
    cat > "$WALLET_DIR/local-override.yaml" <<EOF
spring:
  datasource:
    username: admin
    password: "$ADMIN_PASSWORD"
    type: com.zaxxer.hikari.HikariDataSource
EOF
    cd backend
    ./gradlew clean build
    export TNS_ADMIN=../$WALLET_DIR
    SPRING_PROFILES_ACTIVE=local SPRING_CONFIG_ADDITIONAL_LOCATION=file:../$WALLET_DIR/local-override.yaml ./gradlew bootRun > ../backend.log 2>&1 &
    BACKEND_PID=$!
    cd ..
}

# Wait for backend health
wait_backend_health() {
    echo -e "${YELLOW}⏳ Waiting for backend health (up to 5min)...${NC}"
    local tries=60  # 5min with 5s intervals
    while [ $tries -gt 0 ]; do
        if curl -sf http://localhost:8080/actuator/health | grep -q '"status":"UP"'; then
            echo -e "${GREEN}✅ Backend is UP${NC}"
            return 0
        fi
        echo -e "${YELLOW}Checking health (tries left: $tries)...${NC}"
        sleep 5
        tries=$((tries - 1))
    done
    echo -e "${RED}❌ Backend did not start. Check backend.log:${NC}"
    tail -n 50 backend.log
    exit 1
}

# Start frontend
start_frontend() {
    echo -e "${YELLOW}🌟 Starting frontend...${NC}"
    cd app
    if [ ! -d "node_modules" ]; then
        npm ci
    fi
    npm run serve &
    FRONTEND_PID=$!
    cd ..
}

# Cleanup on exit
cleanup_on_exit() {
    echo -e "${YELLOW}🛑 Stopping application...${NC}"
    [ ! -z "${BACKEND_PID:-}" ] && kill $BACKEND_PID 2>/dev/null || true
    [ ! -z "${FRONTEND_PID:-}" ] && kill $FRONTEND_PID 2>/dev/null || true
    docker stop $CONTAINER_NAME 2>/dev/null || true
    docker rm $CONTAINER_NAME 2>/dev/null || true
    rm -f backend.log "$WALLET_DIR/local-override.yaml"
    exit
}

# Show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  --backend-only      Start only backend (with DB)"
    echo "  --frontend-only     Start only frontend (no DB/backend)"
    echo "  --skip-db           Skip DB setup (assume running)"
    echo "  --clean             Force clean wallet/container"
    exit 0
}

# Parse options
BACKEND_ONLY=false
FRONTEND_ONLY=false
SKIP_DB=false
CLEAN=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help) show_usage ;;
        --backend-only) BACKEND_ONLY=true ;;
        --frontend-only) FRONTEND_ONLY=true ;;
        --skip-db) SKIP_DB=true ;;
        --clean) CLEAN=true ;;
        *) echo -e "${RED}Unknown option: $1${NC}"; show_usage ;;
    esac
    shift
done

# Main execution
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
elif [ "$BACKEND_ONLY" = true ] || [ "$SKIP_DB" = false ]; then
    if [ "$SKIP_DB" = false ]; then
        cleanup
        pull_image
        start_container
        wait_healthy
        patch_wallet
    fi
    start_backend
    wait_backend_health
    if [ "$BACKEND_ONLY" != true ]; then
        start_frontend
    fi
else
    start_backend
    wait_backend_health
    start_frontend
fi

echo -e "${GREEN}🎉 Application started!${NC}"
echo "Backend: http://localhost:8080 (health: /actuator/health)"
echo "Frontend: http://localhost:8000"
echo "DB Container: $CONTAINER_NAME (logs: docker logs $CONTAINER_NAME)"
echo "Press Ctrl+C to stop"

wait
