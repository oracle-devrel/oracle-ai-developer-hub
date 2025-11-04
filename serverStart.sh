#!/bin/bash

# OCI Generative AI JET UI - One-Shot Local Deployment Script
# This script sets up and runs the complete application locally

set -euo pipefail  # Exit on error, unset var, and pipeline fails

echo "🚀 OCI Generative AI JET UI - Local Deployment"
echo "=============================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to start Oracle DB container
start_oracle_db() {
    echo "🗄️ Setting up local Oracle Autonomous Database Free container..."
    
    if ! command_exists docker; then
        echo "❌ Docker is required but not found. Please install Docker."
        exit 1
    fi
    
    local container_name="adb-free"
    local wallet_dir="$HOME/adb_wallet"
    local admin_password="Welcome123456#"
    local wallet_password="WalletPass123#"
    
    # Cleanup old oracle-free if exists
    if docker ps -a | grep -q oracle-free; then
        echo "🧹 Removing old oracle-free container to free ports..."
        docker rm -f oracle-free
    fi
    
    # Remove any existing adb-free container for clean start
    if docker ps -a --filter "name=^${container_name}$" | grep -q ${container_name}; then
        echo "🧹 Removing existing ${container_name} container for clean start..."
        docker rm -f ${container_name}
    fi
    
    echo "📥 Pulling Oracle ADB Free image..."
    docker pull container-registry.oracle.com/database/adb-free:latest-23ai
    
    echo "🚀 Creating and starting ADB container..."
    docker run -d --name ${container_name} \
        -p 1522:1522 -p 8443:8443 -p 27017:27017 \
        -e WORKLOAD_TYPE=ATP \
        -e WALLET_PASSWORD="${wallet_password}" \
        -e ADMIN_PASSWORD="${admin_password}" \
        --cap-add SYS_ADMIN \
        --device /dev/fuse \
        container-registry.oracle.com/database/adb-free:latest-23ai
    
    # Wait for DB to be ready
    echo "⏳ Waiting for ADB to be ready (this may take up to 10 minutes on first run)..."
    local tries=600
    while [ $tries -gt 0 ]; do
        if docker logs ${container_name} 2>&1 | grep -q "DATABASE IS READY TO USE!"; then
            echo "✅ ADB is ready"
            break
        fi
        sleep 1
        tries=$((tries - 1))
    done
    if [ $tries -eq 0 ]; then
        echo "❌ ADB did not start in time"
        return 1
    fi
    
    # Copy wallet to host if not exists
    if [ ! -d "${wallet_dir}" ]; then
        echo "📂 Copying wallet to ${wallet_dir}..."
        mkdir -p "${wallet_dir}"
        docker cp ${container_name}:/u01/app/oracle/wallets/tls_wallet/. "${wallet_dir}/"
    else
        echo "✅ Wallet already exists at ${wallet_dir}"
    fi
    
    return 0
}



# Function to check Node.js and setup frontend
setup_frontend() {
    echo "🌐 Setting up frontend..."

    # Check if Node.js is available
    if ! command_exists node; then
        echo "❌ Node.js is required but not found."
        echo "   Please install Node.js 18+: https://nodejs.org/"
        exit 1
    fi

    # Check Node version
    NODE_VERSION=$(node -v | sed 's/v//')
    if node -e "const v=process.version.match(/^v(\d+)/)[1]; process.exit(v>=18?0:1)"; then
        echo "✅ Node.js $NODE_VERSION detected"
    else
        echo "❌ Node.js 18+ is required. Current version: $NODE_VERSION"
        exit 1
    fi

    # Install frontend dependencies if needed
    if [ ! -d "app/node_modules" ]; then
        echo "📦 Installing frontend dependencies..."
        cd app
        npm install
        cd ..
    else
        echo "✅ Frontend dependencies already installed"
    fi

    echo "✅ Frontend setup complete"

}

# Function to check Java (>=17)
check_java() {
    echo "☕ Checking Java runtime..."
    if ! command_exists java; then
        echo "❌ Java (JDK) is required but not found. Please install Java 17+."
        exit 1
    fi
    JAVA_VERSION_RAW=$(java -version 2>&1 | awk -F\" '/version/ {print $2}')
    JAVA_MAJOR=${JAVA_VERSION_RAW%%.*}
    if [[ "$JAVA_MAJOR" =~ ^[0-9]+$ ]] && [ "$JAVA_MAJOR" -ge 17 ]; then
        echo "✅ Java $JAVA_VERSION_RAW detected"
    else
        echo "❌ Java 17+ is required. Current version: $JAVA_VERSION_RAW"
        exit 1
    fi
}

# Wait for Java backend health to be UP
wait_for_java() {
    echo "⏳ Waiting for Java backend health at http://localhost:8080/actuator/health ..."
    local tries=60
    while [ $tries -gt 0 ]; do
        if curl -sf http://localhost:8080/actuator/health | grep -q "\"status\":\"UP\""; then
            echo "✅ Java backend is UP"
            return 0
        fi
        sleep 1
        tries=$((tries - 1))
    done
    echo "❌ Java backend did not become ready in time"
    return 1
}
# Function to start the application
start_application() {
    echo "🎯 Starting OCI Generative AI JET UI (Java backend + JET frontend)..."
    echo ""

    # Start Oracle DB first
    start_oracle_db || {
        echo "❌ Failed to start ADB"
        exit 1
    }
    
    # Start Java backend with local profile and TNS_ADMIN
    echo "🔧 Starting Java backend server (local profile)..."
    cd backend
    export TNS_ADMIN="$HOME/adb_wallet"
    SPRING_PROFILES_ACTIVE=local ./gradlew bootRun &
    JAVA_PID=$!
    cd ..

    # Wait for backend readiness
    wait_for_java || {
        echo "❌ Backend failed to start. Stopping..."
        kill $JAVA_PID 2>/dev/null || true
        exit 1
    }

    # Start frontend
    echo "🌟 Starting frontend development server..."
    cd app
    npm run dev &
    FRONTEND_PID=$!
    cd ..

    echo ""
    echo "🎉 Application started successfully!"
    echo ""
    echo "📱 Frontend: http://localhost:8000 (or check npm output for exact port)"
    echo "🔌 Backend (Java): http://localhost:8080 (health: /actuator/health)"
    echo ""
    echo "🛑 To stop the application, press Ctrl+C"
    echo ""

    # Wait for user interrupt
    trap "echo '🛑 Stopping application...'; kill $JAVA_PID $FRONTEND_PID 2>/dev/null || true; exit" INT TERM

    # Wait for processes
    wait
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -s, --skip-checks  Reserved (no-op)"
    echo "  --backend-only     Start only the Java backend"
    echo "  --frontend-only    Start only the frontend"
    echo ""
    echo "Examples:"
    echo "  $0              # Full setup and start"
    echo "  $0 --backend-only   # Start only backend"
    echo "  $0 -s           # Skip OCI checks"
}

# Parse command line arguments
SKIP_CHECKS=false
BACKEND_ONLY=false
FRONTEND_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -s|--skip-checks)
            SKIP_CHECKS=true
            shift
            ;;
        --backend-only)
            BACKEND_ONLY=true
            shift
            ;;
        --frontend-only)
            FRONTEND_ONLY=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    # Run setup steps
    if [ "$FRONTEND_ONLY" = false ]; then
        check_java
    fi

    if [ "$BACKEND_ONLY" = false ]; then
        setup_frontend
    fi

    # Start application based on flags
    if [ "$BACKEND_ONLY" = true ]; then
        echo "🔧 Starting backend only (Java)..."
        cd backend
        ./gradlew bootRun
    elif [ "$FRONTEND_ONLY" = true ]; then
        echo "� Starting frontend only..."
        cd app
        npm run dev
    else
        start_application
    fi
}

# Run main function
main "$@"
