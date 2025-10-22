# Cloud‑Native Deployment on OKE: Enterprise RAG Blueprint

This guide operationalizes the Data → Model → Service (DMS) architecture on Oracle Cloud:
- Oracle Database 26ai (via Autonomous Database) for durable context, memory, telemetry, and KB for RAG
- OCI Generative AI for model inference (Cohere, Meta, xAI via Inference)
- Spring Boot backend and Oracle JET web app on OKE (Oracle Container Engine for Kubernetes)
- Terraform + Kustomize for reproducible environments

![Architecture](./images/architecture.png)

## Prerequisites

- OCI tenancy with permissions to manage OKE, Networking, ADB, and OCIR
- Terraform and kubectl installed
- Node.js 18+ for repository scripts
- Unzipped ADB wallet (for JDBC wallet connectivity)
- OCI credentials available for image push and Generative AI access

Helpful docs:
- OKE: https://docs.oracle.com/en-us/iaas/Content/ContEng/Concepts/contengoverview.htm
- Autonomous Database: https://docs.oracle.com/en/database/autonomous-database-cloud-services.html

## Environment setup

```bash
git clone https://github.com/oracle-devrel/oci-generative-ai-jet-ui.git
cd oci-generative-ai-jet-ui
nvm install 18 && nvm use 18
cd scripts && npm install && cd ..
```

### Generate environment and tfvars

These scripts create `genai.json` and `deploy/terraform/terraform.tfvars` from prompts:

```bash
npx zx scripts/setenv.mjs      # writes genai.json
npx zx scripts/tfvars.mjs      # writes deploy/terraform/terraform.tfvars
```

> Tip: When asked, provide the Compartment where you want to deploy. Root compartment is the default.

## Provision OKE + ADB with Terraform

```bash
cd deploy/terraform
terraform init
terraform apply --auto-approve
cd ../..
```

After apply, a kubeconfig is generated at `deploy/terraform/generated/kubeconfig`.

## Build and publish images to OCIR

Use the release script to version, build, login, and push images to OCIR:

```bash
npx zx scripts/release.mjs
```

## Generate Kustomize overlays

Create kustomization files that reference the newly published images:

```bash
npx zx scripts/kustom.mjs
```

Overlays are under:

- `deploy/k8s/backend/*`
- `deploy/k8s/web/*`
- `deploy/k8s/ingress/*`
- `deploy/k8s/overlays/prod/*`

## ADB Wallet for Backend (Required)

You selected ADB with Wallet for production. Before deploying the backend, create a Kubernetes Secret from your unzipped ADB Wallet and mount it into the backend pod. Then set `TNS_ADMIN` so the JDBC driver can find `sqlnet.ora` and `tnsnames.ora`.

1) Create the wallet secret (use the path to your unzipped wallet directory):

```bash
# Namespace 'backend' is used by provided manifests
kubectl create secret generic adb-wallet \
  --from-file=/ABSOLUTE/PATH/TO/WALLET/DIR \
  -n backend
```

2) Mount the secret and set `TNS_ADMIN` in the backend Deployment (`deploy/k8s/backend/backend.yaml`):

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

3) Ensure your Spring datasource uses the `_high` service and the same `TNS_ADMIN`:

```yaml
spring:
  datasource:
    url: jdbc:oracle:thin:@DB_SERVICE_high?TNS_ADMIN=/opt/adb/wallet
    driver-class-name: oracle.jdbc.OracleDriver
    username: ADMIN
    password: "YOUR_PASSWORD"
    type: oracle.ucp.jdbc.PoolDataSource
```

You can inject these via env vars/ConfigMap if preferred. See `DATABASE.md` for schema details.

## Deploy to the cluster

Export kubeconfig created by Terraform and apply the Kustomize overlay:

```bash
export KUBECONFIG="$(pwd)/deploy/terraform/generated/kubeconfig"
kubectl cluster-info
kubectl apply -k deploy/k8s/overlays/prod
```

Check deployments and wait until `READY` equals desired replicas:

```bash
kubectl get deploy -n backend
kubectl get deploy -n web
kubectl get deploy -n ingress-nginx
```

## Access the application

Fetch the public IP of the LoadBalancer service:

```bash
echo $(kubectl get service \
  -n backend \
  -o jsonpath='{.items[?(@.spec.type=="LoadBalancer")].status.loadBalancer.ingress[0].ip}')
```

If empty, wait a few minutes and retry; provisioning may take time. Open the IP in your browser to access the web UI.

## OCI authentication options on OKE

- Workload Identity (recommended) or Instance Principals for the backend
- Avoid local file dependencies in cluster
- Configure `genai.region` and `compartment_id` via environment or application config

## Operational guardrails

- Vendor‑aware parameter handling (avoid sending unsupported params to specific models)
- Telemetry via `interactions` table (latency, tokens, costs) for observability and budgeting
- Resource requests/limits and optional HPA (add to kustomize if desired)
- Pod Disruption Budgets for high availability
- Secrets and ConfigMaps for environment separation and secure configuration

## Verification

Backend logs and pod status:

```bash
kubectl get pods -n backend
kubectl logs deploy/backend -n backend
```

Schema checks (via SQL Developer Web on ADB, or your SQL tool):

```sql
SELECT COUNT(*) FROM conversations;
SELECT COUNT(*) FROM kb_documents;
SELECT COUNT(*) FROM interactions;
```

Quick API checks:

```bash
# Models list
kubectl port-forward -n backend deploy/backend 8080:8080 &
curl http://localhost:8080/api/genai/models

# RAG (ensure you uploaded PDFs first)
curl -X POST http://localhost:8080/api/genai/rag \
  -H "Content-Type: application/json" \
  -d '{"question":"What does section 2 cover?","modelId":"ocid1.generativeaimodel.oc1...."}'
```

## Troubleshooting

- Wallet path or `TNS_ADMIN` mismatch → backend fails to connect; verify secret mount and JDBC URL path.
- Invalid model parameters → see `MODELS.md` for vendor-specific constraints; the backend adapts where possible.
- Ingress provisioning delay → LoadBalancer IP may take several minutes; re-check `kubectl get svc`.
- Database objects missing → confirm Liquibase ran; see logs and `DATABASE.md` (delimiter notes, schemas).
- More scenarios: `TROUBLESHOOTING.md`.

## Cleanup

Delete Kubernetes components:

```bash
kubectl delete -k deploy/k8s/overlays/prod
```

Destroy infrastructure with Terraform:

```bash
cd deploy/terraform
terraform destroy -auto-approve
cd ../..
```

Clean up build artifacts in Object Storage:

```bash
npx zx scripts/clean.mjs
```

## LLM‑friendly documentation patterns

- JSON‑first configuration and payload examples
- Q&A pairs to validate RAG behavior
- Mermaid diagrams (see README) for architecture and flows
- Numbered procedures with clear prerequisites and outputs

## Notes

- This blueprint targets Oracle Database 26ai features through ADB for vector‑ready, assistant‑grade persistence.
- See `DATABASE.md` for Liquibase migrations and table layouts, `RAG.md` for RAG pipeline usage, and `README.md` for the broader “From GUIs to RAG” story.
