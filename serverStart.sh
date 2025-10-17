#!/bin/bash

# OCI Generative AI JET UI - One-Shot Local Deployment Script
# This script sets up and runs the complete application locally

set -e  # Exit on any error

echo "🚀 OCI Generative AI JET UI - Local Deployment"
echo "=============================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to setup Python virtual environment
setup_python_env() {
    echo "🐍 Setting up Python virtual environment..."

    # Check if Python 3 is available
    if ! command_exists python3; then
        echo "❌ Python 3 is required but not found. Please install Python 3."
        exit 1
    fi

    # Check Python version (should be 3.8+)
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)'; then
        echo "✅ Python $PYTHON_VERSION detected"
    else
        echo "❌ Python 3.8+ is required. Current version: $PYTHON_VERSION"
        exit 1
    fi

    # Create virtual environment if it doesn't exist
    if [ ! -d "service/python/venv" ]; then
        echo "📦 Creating Python virtual environment..."
        cd service/python
        python3 -m venv venv
        cd ../..
    else
        echo "✅ Python virtual environment already exists"
    fi

    # Activate virtual environment and install dependencies
    echo "📥 Installing Python dependencies..."
    cd service/python
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    cd ../..

    echo "✅ Python environment setup complete"
}

# Function to check OCI configuration
check_oci_config() {
    echo "🔐 Checking OCI configuration..."

    # Check if OCI config directory exists
    if [ ! -d "$HOME/.oci" ]; then
        echo "⚠️  OCI configuration directory not found: $HOME/.oci"
        echo "   This may be okay if you're using instance principals or other auth methods"
        echo "   Proceeding without OCI validation..."
        return 0
    fi

    # Check if config file exists
    if [ ! -f "$HOME/.oci/config" ]; then
        echo "⚠️  OCI config file not found: $HOME/.oci/config"
        echo "   This may be okay if you're using instance principals or other auth methods"
        echo "   Proceeding without OCI validation..."
        return 0
    fi

    # Try to read key_file from config (may not exist)
    CONFIG_PROFILE="DEFAULT"
    KEY_FILE=$(grep "^key_file" "$HOME/.oci/config" 2>/dev/null | head -1 | cut -d'=' -f2 | tr -d ' ' | sed 's/~/$HOME/')

    if [ -n "$KEY_FILE" ]; then
        # Expand ~ to $HOME if present
        KEY_FILE="${KEY_FILE/#\~/$HOME}"

        if [ ! -f "$KEY_FILE" ]; then
            echo "⚠️  Private key file not found: $KEY_FILE"
            echo "   This may be okay if you're using different authentication methods"
            echo "   Proceeding without strict key validation..."
        else
            echo "✅ OCI private key found: $KEY_FILE"
        fi
    else
        echo "ℹ️  No key_file specified in OCI config (may be using instance principals)"
    fi

    echo "✅ OCI configuration check completed"

    # Check if server.py has been configured (just a warning)
    if grep -q "ocid1.compartment.oc1" service/python/server.py 2>/dev/null; then
        echo "⚠️  WARNING: server.py still contains placeholder compartment_id"
        echo "   Please update service/python/server.py with your actual compartment_id"
    fi
}

# Function to check Node.js and setup frontend
setup_frontend() {
    echo "🌐 Setting up frontend..."

    # Check if Node.js is available
    if ! command_exists node; then
        echo "❌ Node.js is required but not found."
        echo "   Please install Node.js 16+: https://nodejs.org/"
        exit 1
    fi

    # Check Node version
    NODE_VERSION=$(node -v | sed 's/v//')
    if node -e "const v=process.version.match(/^v(\d+)/)[1]; process.exit(v>=16?0:1)"; then
        echo "✅ Node.js $NODE_VERSION detected"
    else
        echo "❌ Node.js 16+ is required. Current version: $NODE_VERSION"
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

# Function to start the application
start_application() {
    echo "🎯 Starting OCI Generative AI JET UI..."
    echo ""

    # Start Python backend in background
    echo "🔧 Starting Python backend server..."
    cd service/python
    source venv/bin/activate
    python server.py &
    BACKEND_PID=$!
    cd ../..

    # Wait a moment for backend to start
    sleep 3

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
    echo "🔌 Backend: WebSocket on ws://localhost:1986, HTTP on http://localhost:1987"
    echo ""
    echo "🛑 To stop the application, press Ctrl+C"
    echo ""

    # Wait for user interrupt
    trap "echo '🛑 Stopping application...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT

    # Wait for processes
    wait
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -s, --skip-checks  Skip OCI configuration checks"
    echo "  --backend-only     Start only the Python backend"
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
        setup_python_env
        if [ "$SKIP_CHECKS" = false ]; then
            check_oci_config
        fi
    fi

    if [ "$BACKEND_ONLY" = false ]; then
        setup_frontend
    fi

    # Start application based on flags
    if [ "$BACKEND_ONLY" = true ]; then
        echo "🔧 Starting backend only..."
        cd service/python
        source venv/bin/activate
        python server.py
    elif [ "$FRONTEND_ONLY" = true ]; then
        echo "🌐 Starting frontend only..."
        cd app
        npm run dev
    else
        start_application
    fi
}

# Run main function
main "$@"
