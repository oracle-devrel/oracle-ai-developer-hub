# Run Local

## 🚀 One-Shot Deployment (Recommended)

The easiest way to get started is using the automated deployment script:

```bash
# Make script executable (one time only)
chmod +x serverStart.sh

# Run full application (backend + frontend)
./serverStart.sh
```

The script will:
- ✅ Check system requirements (Python 3.8+, Node.js 16+)
- ✅ Set up Python virtual environment
- ✅ Install all dependencies
- ✅ Verify OCI configuration
- ✅ Start both backend and frontend servers
- ✅ Provide access URLs

### Script Options

```bash
# Show help
./serverStart.sh --help

# Skip OCI configuration checks
./serverStart.sh --skip-checks

# Start only backend (for API testing)
./serverStart.sh --backend-only

# Start only frontend (if backend is already running)
./serverStart.sh --frontend-only
```

## 🔧 Manual Setup (Alternative)

If you prefer manual setup, follow these steps:

### Prerequisites

- **Python 3.8+**: [Download Python](https://python.org)
- **Node.js 16+**: [Download Node.js](https://nodejs.org)
- **OCI Account & CLI**: [Setup Guide](https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/cliinstall.htm)

### 1. OCI Configuration

1. Install OCI CLI and configure:
   ```bash
   pip install oci-cli
   oci setup config
   ```

2. Upload your public key to OCI console: [API Keys](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/apisigningkey.htm)

3. Update `service/python/server.py`:
   ```python
   compartment_id = "ocid1.compartment.oc1..YOUR_COMPARTMENT_OCID"
   endpoint = "https://inference.generativeai.YOUR_REGION.oci.oraclecloud.com"
   ```

### 2. Backend Setup

```bash
# Create Python virtual environment
cd service/python
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run backend server
python server.py
```

### 3. Frontend Setup

```bash
# Install dependencies
cd app
npm install

# Run development server
npm run dev
```

### 4. Access Application

- **Frontend**: http://localhost:8000 (check npm output for exact port)
- **Backend APIs**:
  - WebSocket: ws://localhost:1986
  - HTTP: http://localhost:1987

## 🔧 Environment Configuration

### Model Selection

The application automatically detects and supports all available models in your region:

- **Cohere**: `cohere.command-a-03-2025`, `cohere.command-r-08-2024`, etc.
- **Meta**: `meta.llama-4-maverick-17b-128e-instruct-fp8`, `meta.llama-3.3-70b-instruct`, etc.
- **xAI**: `xai.grok-4`, `xai.grok-3`, etc.

### Environment Variables (Optional)

```bash
# Force specific model (defaults to cohere.command-a-03-2025)
export GENAI_ONDEMAND_MODEL_ID="cohere.command-a-03-2025"

# Use dedicated endpoint (if available)
export GENAI_ENDPOINT_ID="ocid1.generativeaiendpoint.oc1.us-chicago-1.YOUR_ENDPOINT_OCID"

# Skip virtual environment checks (for CI/CD)
export SKIP_VENV=true
```

## 🐛 Troubleshooting

### Backend Issues

**"model OCID ... does not support TextSummarization"**
- This is expected - the app now uses chat models for summarization
- All models support chat, so summarization works with any model

**404 Errors with Dedicated Mode**
- Unset `GENAI_ENDPOINT_ID` to use On-Demand mode
- Or ensure your endpoint OCID matches the region

**WebSocket Connection Failed**
- Ensure backend is running on port 1986
- Check firewall settings

### Frontend Issues

**Port Already in Use**
- Kill existing processes: `pkill -f "python server.py"`
- Or use different ports in configuration

**Model Dropdown Empty**
- Check OCI configuration and permissions
- Verify compartment_id in server.py
- Check browser console for API errors

### Common Fixes

```bash
# Reset everything
rm -rf service/python/venv app/node_modules
./serverStart.sh

# Check OCI config
oci iam compartment list --compartment-id ocid1.tenancy.oc1..YOUR_TENANCY

# Test backend directly
curl http://localhost:1987/models
```

## 📦 Build for Production

### Backend Build

```bash
cd service/python
# The Python app is ready for production as-is
# Consider using gunicorn for production deployment
pip install gunicorn
gunicorn --bind 0.0.0.0:1987 server:app
```

### Frontend Build

```bash
cd app
npm run build
# Deploy the 'web' folder to your web server
```
