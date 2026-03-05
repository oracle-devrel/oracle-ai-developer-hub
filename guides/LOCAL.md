# Run Local

This guide provides step-by-step instructions to run the app locally using the Java/Spring backend and Oracle JET frontend. It builds on README.md for overview and aligns with build.gradle (Spring Boot 3.2.x/Java 21) and package.json (Oracle JET 19.x). For deployment, see K8S.md next.

## Prerequisites

- JDK 21+ (for backend)
- Node.js 18+ (for frontend and scripts)
- OCI credentials configured locally (~/.oci/config) with access to Generative AI
- Oracle ADB Wallet unzipped to an absolute path (contains sqlnet.ora, tnsnames.ora, etc.)

## Step-by-Step Setup

1. Clone and prepare:
   ```bash
   git clone https://github.com/oracle-devrel/oci-generative-ai-jet-ui.git
   cd oci-generative-ai-jet-ui
   node -v   # ensure Node.js 18+
   npm -v
   cd scripts && npm ci && cd ..
   ```

   If Node.js is missing or older than 18, install Node.js 18+ using nvm or Homebrew, then rerun the commands.

2. Configure backend (DB and OCI) in backend/src/main/resources/application.yaml:
   ```yaml
   spring:
     datasource:
       driver-class-name: oracle.jdbc.OracleDriver
       url: jdbc:oracle:thin:@DB_SERVICE_high?TNS_ADMIN=/ABSOLUTE/PATH/TO/WALLET
       username: ADMIN
       password: "YOUR_PASSWORD"
       type: oracle.ucp.jdbc.PoolDataSource
       oracleucp:
         sql-for-validate-connection: SELECT 1 FROM dual
         connection-pool-name: pool1
         initial-pool-size: 5
         min-pool-size: 5
         max-pool-size: 10

   genai:
     region: "US_CHICAGO_1"
     config:
       location: "~/.oci/config"
       profile: "DEFAULT"
     compartment_id: "ocid1.compartment.oc1..xxxx"
   ```

3. Build and run backend:
   ```bash
   cd backend
   ./gradlew clean build  # Aligns with Spring Boot 3.2.x/Java 21 in build.gradle
   ./gradlew bootRun
   # Backend runs on http://localhost:8080
   ```

4. Build and run frontend:
   ```bash
   cd ../app
   npm ci  # Installs Oracle JET 19.x and deps from package.json
   npm run serve
   # UI on http://localhost:8000
   ```

5. Test endpoints:
   ```bash
   # List models
   curl http://localhost:8080/api/genai/models

   # Upload a PDF for RAG
   curl -F "file=@/absolute/path/to/document.pdf" http://localhost:8080/api/upload

   # Ask a RAG question
   curl -X POST http://localhost:8080/api/genai/rag \
     -H "Content-Type: application/json" \
     -d '{
       "question": "What does section 2 cover?",
       "modelId": "ocid1.generativeaimodel.oc1...."
     }'
   ```

Notes:
- Liquibase applies schema migrations on backend startup (conversations, messages, memory, telemetry, KB). See DATABASE.md.
- The backend adapts parameters per vendor (e.g., omits presencePenalty for xAI Grok). See MODELS.md.

## One-Shot Script (Alternative)

For quick start:
```bash
chmod +x serverStart.sh
./serverStart.sh  # Starts backend + frontend
```

Options:
- --help: Show usage
- --skip-checks: Skip OCI checks
- --backend-only: Only backend
- --frontend-only: Only frontend

## Environment Variables (Optional)

```bash
export GENAI_ONDEMAND_MODEL_ID="cohere.command-a-03-2025"  # Default chat model
```

## Troubleshooting

See TROUBLESHOOTING.md for errors. Common: Verify wallet path, OCI config.

## Q&A

Q: Why no Python backend? A: App uses Java-only for consistency; removed in recent changes (see CHANGES.md).

Q: How do I verify builds? A: After ./gradlew clean build, check build/ for JAR; npm ci should succeed without errors.
