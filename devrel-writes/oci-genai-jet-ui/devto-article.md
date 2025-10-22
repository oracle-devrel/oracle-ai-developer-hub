# Cloud‑Native RAG on Oracle Cloud: Spring Boot + Oracle JET + OCI GenAI + ADB 26ai

Problem → Architecture → Key code → Best practices → Resources. A production‑ready pattern for assistants that goes beyond “call an LLM API.” This deep dive shows how to build a Retrieval‑Augmented Generation (RAG) app that persists context, enforces vendor‑aware parameters, ships telemetry, and deploys on Kubernetes (OKE) with Terraform and Kustomize.

- Stack: Spring Boot (service) + Oracle JET (UI) + OCI Generative AI (models) + Oracle Database 26ai (data)
- Pattern: Data → Model → Service (DMS)
- Repo: oci-generative-ai-jet-ui

## 1) Problem

LLM demos often skip the hard parts:
- No durable context (chat resets)
- No grounding (answers drift)
- Model parameter pitfalls (vendor differences cause 400s)
- Zero observability (no latency/tokens/cost telemetry)
- Fragile UX (uploads, streaming, error paths)

Goal: a repeatable architecture that ships understanding—production‑ready assistants grounded in your data.

## 2) Architecture (DMS)

- Data (Oracle Database 26ai via Autonomous Database)
  - Conversations, messages, memory (KV + long)
  - Knowledge Base (KB) tables for RAG
  - Telemetry (interactions: latency, tokens, cost)
- Model (OCI Generative AI)
  - Cohere / Meta / xAI via Inference
  - Vendor‑aware parameter handling
- Service (Spring Boot)
  - REST + WebSocket (chat, RAG, upload, models)
  - Liquibase migrations
  - OCI auth (local config, Workload Identity, Instance Principals)
- UI (Oracle JET)
  - Chat, Upload, Settings (Use RAG)
  - Keepalive diagnostics + opt‑in debug

```mermaid
flowchart LR
  subgraph UI (Oracle JET)
    A[Chat / Upload / Settings]
  end
  subgraph Service (Spring Boot)
    B1[Controllers: GenAI, Upload/PDF, Models, Summary]
    B2[Services: OCIGenAI, RagService, GenAIModelsService]
    B3[Liquibase]
  end
  subgraph Data (ADB 26ai)
    D1[(Conversations/Messages/Memory)]
    D2[(KB for RAG)]
    D3[(Telemetry: interactions)]
  end
  subgraph Models (OCI GenAI)
    C1[Cohere / Meta / xAI]
  end
  A <-- REST/WS --> B1 --> B2
  B2 <---> D1 & D2
  B2 --> C1
  B2 --> D3
```

## 3) Local quickstart (key code + commands)

application.yaml (datasource + OCI GenAI). Use an unzipped ADB wallet and your compartment.

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

Run backend:

```bash
cd backend
./gradlew clean build
./gradlew bootRun
# http://localhost:8080
```

Run web UI:

```bash
cd ../app
npm ci
npm run serve
# http://localhost:8000
```

Upload a PDF (indexes to KB):

```bash
curl -F "file=@/path/to/file.pdf" http://localhost:8080/api/upload
```

RAG query:

```bash
curl -X POST http://localhost:8080/api/genai/rag \
  -H "Content-Type: application/json" \
  -d '{"question":"What does section 2 cover?","modelId":"ocid1.generativeaimodel.oc1...."}'
```

List models:

```bash
curl http://localhost:8080/api/genai/models
```

## 4) Kubernetes on OCI (OKE) — Infra + Deploy

Provision (Terraform):

```bash
cd deploy/terraform
terraform init
terraform apply --auto-approve
cd ../..
```

Release images to OCIR (buildx + push):

```bash
npx zx scripts/release.mjs
```

Generate Kustomize overlays (injects image refs):

```bash
npx zx scripts/kustom.mjs
```

ADB Wallet secret (required for JDBC wallet connectivity):

```bash
kubectl create secret generic adb-wallet \
  --from-file=/ABSOLUTE/PATH/TO/WALLET/DIR \
  -n backend
```

Mount wallet + set TNS_ADMIN (deploy/k8s/backend/backend.yaml):

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

Deploy overlays:

```bash
export KUBECONFIG="$(pwd)/deploy/terraform/generated/kubeconfig"
kubectl cluster-info
kubectl apply -k deploy/k8s/overlays/prod
```

Find LoadBalancer IP:

```bash
kubectl get svc -n backend -o jsonpath='{.items[?(@.spec.type=="LoadBalancer")].status.loadBalancer.ingress[0].ip}'
```

## 5) Technical gotchas → solutions

- Vendor‑aware params
  - Not all providers accept the same knobs (e.g., some don’t support presencePenalty).
  - Fix: centralize model adapters; only send supported parameters per vendor.

- Wallet/TNS_ADMIN issues
  - JDBC fails if wallet path is wrong or not mounted.
  - Fix: create K8S secret from unzipped wallet dir; mount; set `TNS_ADMIN=/opt/adb/wallet`; use `_high` service.

- Ingress delay
  - LB IP can take minutes.
  - Fix: loop jsonpath query; verify ingress controller readiness.

- Liquibase delimiter / schema
  - PL/SQL and DDL delimiter config can break migrations if wrong.
  - Fix: see DATABASE.md notes; check backend logs at startup.

- Telemetry is not optional
  - You’ll fly blind on latency/costs without `interactions`.
  - Fix: regularly query telemetry; set alerts/budgets.

## 6) Best practices

- DMS separation: keep data, model, and service concerns isolated.
- Ground before generate: always retrieve KB chunks for enterprise answers.
- Parameter safety: gate knobs per vendor; validate server‑side.
- Observability: persist interactions; tie into dashboards.
- Resource hygiene: set requests/limits; consider HPA + PDBs; handle disruptions.
- Secrets/ConfigMaps: isolate envs; never bake creds in images.
- Same‑origin deployment: ingress routes UI→backend cleanly; avoid ad‑hoc CORS.

## 7) Reference JSON (LLM‑friendly)

```json
{
  "compartment_id": "ocid1.compartment.oc1..exampleuniqueID",
  "model_id": "cohere.command-r-plus",
  "region": "US_CHICAGO_1"
}
```

## 8) Resources

- Overview + Architecture: README.md
- Frontend (Oracle JET): JET.md
- Kubernetes (OKE) + Terraform: K8S.md
- RAG usage + flow: RAG.md
- Schema + Liquibase: DATABASE.md
- Models + parameters: MODELS.md
- Troubleshooting: TROUBLESHOOTING.md

---

ORACLE AND ITS AFFILIATES DO NOT PROVIDE ANY WARRANTY WHATSOEVER, EXPRESS OR IMPLIED, FOR ANY SOFTWARE, MATERIAL OR CONTENT OF ANY KIND CONTAINED OR PRODUCED WITHIN THIS REPOSITORY, AND IN PARTICULAR SPECIFICALLY DISCLAIM ANY AND ALL IMPLIED WARRANTIES OF TITLE, NON-INFRINGEMENT, MERCHANTABILITY, AND FITNESS FOR A PARTICULAR PURPOSE. FURTHERMORE, ORACLE AND ITS AFFILIATES DO NOT REPRESENT THAT ANY CUSTOMARY SECURITY REVIEW HAS BEEN PERFORMED WITH RESPECT TO ANY SOFTWARE, MATERIAL OR CONTENT CONTAINED OR PRODUCED WITHIN THIS REPOSITORY. IN ADDITION, AND WITHOUT LIMITING THE FOREGOING, THIRD PARTIES MAY HAVE POSTED SOFTWARE, MATERIAL OR CONTENT TO THIS REPOSITORY WITHOUT ANY REVIEW. USE AT YOUR OWN RISK.
