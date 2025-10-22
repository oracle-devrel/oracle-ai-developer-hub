# Build a Cloud‑Native RAG Assistant on Oracle Cloud: A Hands‑On Guide

Learning goals
- Explain the Data → Model → Service (DMS) architecture for building assistants.
- Run the stack locally: Spring Boot backend + Oracle JET frontend.
- Create a Retrieval‑Augmented Generation (RAG) workflow over your own PDFs.
- Provision Oracle Kubernetes (OKE) and Autonomous Database (ADB) with Terraform.
- Deploy with Kustomize, wire the ADB Wallet, and validate the app via Ingress.
- Observe telemetry (latency/tokens) and debug common issues.

What you’ll build
A cloud‑native RAG assistant that runs locally and in the cloud:
- Data: Oracle Database 26ai (via Autonomous Database) for conversations, memory, KB, telemetry
- Model: OCI Generative AI (Cohere/Meta/xAI) with vendor‑aware parameter handling
- Service: Spring Boot + Liquibase + OCI auth modes
- Interface: Oracle JET web app for chat, upload, and settings

Repo
oci-generative-ai-jet-ui

Estimated time
2.5–4 hours (local + cloud)

Prerequisites
- Oracle Cloud account with permissions to use OKE, Networking, ADB, and OCIR
- JDK 17+
- Node.js 18+
- Terraform and kubectl installed
- Unzipped Oracle ADB Wallet (download from your ADB)
- OCI credentials (e.g., ~/.oci/config with a valid profile)

Why this pattern
Assistants are moving us from click‑paths to intent. Getting to production means more than calling a model API: you need durable context, retrieval over your knowledge, vendor‑aware parameters, telemetry, and a stable UI. The DMS architecture is a simple foundation that scales.

Concept: Data → Model → Service (DMS)
- Data (Oracle Database 26ai via ADB)
  - Conversations + messages (durable chat)
  - Memory (key/value + long‑form)
  - KB tables (RAG storage)
  - Telemetry (interactions: latency, tokens, costs)
- Model (OCI Generative AI)
  - Cohere/Meta/xAI models via OCI Inference
  - Vendor‑aware parameter handling and prompt shaping
- Service (Spring Boot)
  - REST + WebSocket for chat, RAG, uploads, model listing
  - Liquibase migrations for schema evolution
  - OCI auth: local config, OKE Workload Identity, Instance Principals
- Interface (Oracle JET)
  - Chat UI, Upload panel, Settings (Use RAG)
  - Keepalive diagnostics and opt‑in debug logging

Architecture (Mermaid)
```mermaid
flowchart LR
  subgraph Web UI (Oracle JET)
    A[Chat / Upload / Settings]
  end
  subgraph Service (Spring Boot)
    B1[Controllers: GenAI, Upload/PDF, Models, Summary]
    B2[Services: OCIGenAI, RagService, GenAIModelsService]
    B3[Liquibase Migrations]
  end
  subgraph Data (Oracle Database 26ai via ADB)
    D1[(Conversations / Messages / Memory)]
    D2[(Telemetry: interactions)]
    D3[(KB Tables for RAG)]
  end
  subgraph Models (OCI Generative AI)
    C1[Cohere / Meta / xAI via Inference]
  end
  A <-- REST & WebSocket --> B1 --> B2
  B2 <---> D1 & D3
  B2 --> C1
  B2 --> D2
```

Learning Path
- Part 1: Local setup and RAG basics
- Part 2: Cloud infrastructure and deployment
- Part 3: Verification, telemetry, and practice challenges

Note on versions
This guide uses Oracle Database 26ai and OCI Generative AI. Replace region/model IDs with those available to your tenancy.

JSON reference (LLM‑friendly)
```json
{
  "compartment_id": "ocid1.compartment.oc1..exampleuniqueID",
  "model_id": "cohere.command-r-plus",
  "region": "US_CHICAGO_1"
}
```

Part 1 — Local Setup and RAG Basics

Step 1 — Clone repo and install script deps
```bash
git clone https://github.com/oracle-devrel/oci-generative-ai-jet-ui.git
cd oci-generative-ai-jet-ui
# Ensure Node 18
nvm install 18 && nvm use 18
cd scripts && npm install && cd ..
```

Step 2 — Configure backend datasource and OCI
Edit backend/src/main/resources/application.yaml. Set wallet path, ADB user/pass, region, and compartment.

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

Tip
- Use the _high service with a valid TNS_ADMIN path pointing to your unzipped wallet.
- The backend will run Liquibase migrations on startup to create tables.

Step 3 — Run the backend
```bash
cd backend
./gradlew clean build
./gradlew bootRun
# Server on http://localhost:8080
```

Step 4 — Run the web UI
```bash
cd ../app
npm ci
npm run serve
# UI on http://localhost:8000
```

Step 5 — Upload a PDF and build the KB
Use the upload endpoint to index content for RAG.

```bash
curl -F "file=@/path/to/file.pdf" http://localhost:8080/api/upload
```

What happens
- The backend extracts and chunks content.
- KB tables are populated.
- The UI RAG toggle can now ground answers on your content.

Step 6 — Ask a RAG question
```bash
curl -X POST http://localhost:8080/api/genai/rag \
  -H "Content-Type: application/json" \
  -d '{"question":"What does section 2 cover?","modelId":"ocid1.generativeaimodel.oc1...."}'
```

In the UI
- Open the app, enable “Use RAG” in Settings, and chat with your content.

Step 7 — Check diagnostics and logs
- Database keepalive: UI pings /api/kb/diag and logs “DB: database active” on first success.
- Enable verbose logs in the browser console:
```js
localStorage.setItem("debug","1")
```
To disable:
```js
localStorage.removeItem("debug")
```

Part 2 — Cloud Infrastructure and Deployment (OKE + ADB)

Step 8 — Generate environment and Terraform variables
```bash
npx zx scripts/setenv.mjs      # writes genai.json
npx zx scripts/tfvars.mjs      # writes deploy/terraform/terraform.tfvars
```
- Provide a Compartment for infra deployment.

Step 9 — Provision OKE and ADB with Terraform
```bash
cd deploy/terraform
terraform init
terraform apply --auto-approve
cd ../..
```
Outputs
- An OKE cluster and ADB
- A kubeconfig saved under deploy/terraform/generated/kubeconfig

Step 10 — Build and push images to OCIR
```bash
npx zx scripts/release.mjs
```
What it does
- Builds and tags containers (backend, web)
- Logs into OCIR
- Pushes images

Step 11 — Generate Kustomize overlays
```bash
npx zx scripts/kustom.mjs
```
This injects image references into the kustomization files.

Step 12 — Create the ADB Wallet secret (required)
Create a K8S secret from your unzipped wallet directory and mount it into the backend pod; set TNS_ADMIN.

```bash
kubectl create secret generic adb-wallet \
  --from-file=/ABSOLUTE/PATH/TO/WALLET/DIR \
  -n backend
```

Mount and set TNS_ADMIN (deploy/k8s/backend/backend.yaml excerpt):
```yaml
spec:
  template:
    spec:
      volumes:
        - name: adb-wallet
          secret:
            secretName: adb-wallet
      containers:
        - name: backend
          volumeMounts:
            - name: adb-wallet
              mountPath: /opt/adb/wallet
          env:
            - name: TNS_ADMIN
              value: /opt/adb/wallet
```

Step 13 — Deploy to the cluster
```bash
export KUBECONFIG="$(pwd)/deploy/terraform/generated/kubeconfig"
kubectl cluster-info
kubectl apply -k deploy/k8s/overlays/prod
```

Check deployments:
```bash
kubectl get deploy -n backend
kubectl get deploy -n web
kubectl get deploy -n ingress-nginx
```

Step 14 — Access the application
Get the LoadBalancer IP for the backend services:
```bash
kubectl get svc -n backend -o jsonpath='{.items[?(@.spec.type=="LoadBalancer")].status.loadBalancer.ingress[0].ip}'
```
Open the IP in your browser and test the web UI.

Step 15 — Verify schema and telemetry
Use SQL Developer Web for ADB or your SQL tool:
```sql
SELECT COUNT(*) FROM conversations;
SELECT COUNT(*) FROM kb_documents;
SELECT COUNT(*) FROM interactions;
```

Optional — Quick API checks via port‑forward
```bash
kubectl port-forward -n backend deploy/backend 8080:8080 &
curl http://localhost:8080/api/genai/models
```

Part 3 — Observe, Troubleshoot, and Improve

Telemetry (why it matters)
- Without observability, you can’t manage latency or costs.
- The interactions table stores latency, token counts, and request metadata.

Example RAG query body (LLM‑friendly JSON)
```json
{
  "question": "Summarize section 2 and list key decisions.",
  "modelId": "ocid1.generativeaimodel.oc1..exampleuniqueID",
  "useRag": true
}
```

Common issues and fixes
- Wallet/TNS_ADMIN mismatch
  - Symptom: Backend cannot connect to ADB.
  - Fix: Ensure the wallet secret path is correct, mounted at /opt/adb/wallet, set TNS_ADMIN accordingly, and use _high in JDBC URL.
- Vendor‑specific parameter errors
  - Symptom: 400s for unsupported parameters (e.g., presencePenalty).
  - Fix: Use server defaults and vendor‑aware adapters; verify MODELS.md for constraints.
- Ingress IP delay
  - Symptom: No public IP yet.
  - Fix: Re‑run the jsonpath query after a few minutes; check ingress controller status.
- Liquibase delimiter or migration issues
  - Symptom: Schema not created or errors on startup.
  - Fix: Inspect backend logs; review DATABASE.md for delimiter notes and migration details.

Try it yourself (practice challenges)
1) RAG Quality Tuning
- Upload two different PDFs (e.g., policy vs. product guide).
- Ask targeted questions and compare grounding quality.
- Outcome: Identify chunking or prompt tweaks needed.

2) Parameter Exploration
- Adjust temperature or top_p in the backend request logic (where permitted).
- Observe changes in interactions for latency/tokens/answer style.
- Outcome: Learn trade‑offs for your use case.

3) UI Debugging
- Enable UI debug logs (localStorage.debug = "1").
- Generate a failure case (e.g., simulating an offline DB).
- Outcome: Document a recovery path and user‑visible error improvements.

4) Deployment Hygiene
- Add resource requests/limits and HPA to Kustomize overlays.
- Create a Pod Disruption Budget (PDB) for the backend.
- Outcome: Increased resilience under node maintenance and load spikes.

Skill progression
- Beginner: Run local stack, upload PDFs, ask RAG questions.
- Intermediate: Deploy to OKE, wire wallet, validate telemetry, fix common issues.
- Advanced: Add autoscaling, dashboards on interactions, and stricter parameter policies; explore agentic flows and tool use.

Assessment checklist
- Can you explain each DMS layer and its responsibility?
- Did you upload PDFs and retrieve grounded answers with RAG?
- Can you find latency and token metrics in interactions?
- Can you deploy to OKE and access the app via LoadBalancer IP?
- Did you resolve a wallet or parameter mismatch during testing?

Use cases (apply what you learned)
- Support assistant: Ground responses in product and SOP PDFs with auditable history.
- Internal search: Consolidate policies and designs into a KB and enable enterprise RAG.
- Workflow co‑pilot: Parameterize prompts for tasks; monitor costs in interactions.

Appendix — LLM Optimization Tips
- Structured JSON examples for configs and payloads make content machine‑parsable.
- Q&A pairs help validate retrieval and grounding.
- Code annotations clarify intent, inputs, and outputs.
- Mermaid diagrams express flows for easy mental and machine parsing.
- Numbered procedures help models learn correct execution order.

Reference links
- Overview + Architecture: README.md
- Oracle JET frontend: JET.md
- Kubernetes (OKE) + Terraform: K8S.md
- RAG usage + flow: RAG.md
- Schema + Liquibase: DATABASE.md
- Models + parameters: MODELS.md
- Troubleshooting: TROUBLESHOOTING.md

Disclaimer
ORACLE AND ITS AFFILIATES DO NOT PROVIDE ANY WARRANTY WHATSOEVER, EXPRESS OR IMPLIED, FOR ANY SOFTWARE, MATERIAL OR CONTENT OF ANY KIND CONTAINED OR PRODUCED WITHIN THIS REPOSITORY, AND IN PARTICULAR SPECIFICALLY DISCLAIM ANY AND ALL IMPLIED WARRANTIES OF TITLE, NON-INFRINGEMENT, MERCHANTABILITY, AND FITNESS FOR A PARTICULAR PURPOSE. FURTHERMORE, ORACLE AND ITS AFFILIATES DO NOT REPRESENT THAT ANY CUSTOMARY SECURITY REVIEW HAS BEEN PERFORMED WITH RESPECT TO ANY SOFTWARE, MATERIAL OR CONTENT CONTAINED OR PRODUCED WITHIN THIS REPOSITORY. IN ADDITION, AND WITHOUT LIMITING THE FOREGOING, THIRD PARTIES MAY HAVE POSTED SOFTWARE, MATERIAL OR CONTENT TO THIS REPOSITORY WITHOUT ANY REVIEW. USE AT YOUR OWN RISK.
