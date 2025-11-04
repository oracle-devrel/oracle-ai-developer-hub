# Deploying RAG Assistant on Kubernetes with Oracle AI Database and Oracle Cloud Infrastructure  

Deploy Retrieval‑Augmented Generation (RAG) assistant on Kubernetes using Oracle Kubernetes Engine (OKE) and Oracle Cloud Infrastructure (OCI). This guide covers Terraform provisioning, Kustomize overlays, OCI Container Registry (OCIR) image publishing, and secure connectivity to Oracle AI Database for vector‑enabled RAG with OCI Generative AI.

This guide operationalizes the Data → Model → Service (DMS) architecture on Oracle Cloud:

- Oracle AI Database for durable context, memory, telemetry, and Knowledge Base (KB) for RAG
- OCI Generative AI for model inference (Cohere, Meta, xAI via Inference)
- Spring Boot backend and Oracle JET web app on OKE (Oracle Container Engine for Kubernetes)
- Terraform + Kustomize for reproducible environments

![RAG on Kubernetes architecture: OKE, Spring Boot, Oracle JET, OCI Generative AI, Oracle AI Database](images/architecture.png)

## Table of Contents

- [Deploying RAG Assistant on Kubernetes with Oracle AI Database and Oracle Cloud Infrastructure](#deploying-rag-assistant-on-kubernetes-with-oracle-ai-database-and-oracle-cloud-infrastructure)
  - [Table of Contents](#table-of-contents)
  - [Prerequisites](#prerequisites)
  - [Environment setup](#environment-setup)
    - [Generate environment and tfvars](#generate-environment-and-tfvars)
  - [Provision OKE (Oracle Kubernetes Engine) and Autonomous Database with Terraform](#provision-oke-oracle-kubernetes-engine-and-autonomous-database-with-terraform)
  - [Build and publish container images to OCI Container Registry (OCIR)](#build-and-publish-container-images-to-oci-container-registry-ocir)
  - [Generate and apply Kustomize overlays](#generate-and-apply-kustomize-overlays)
  - [Deploy to the OKE Kubernetes cluster](#deploy-to-the-oke-kubernetes-cluster)
  - [Expose and access the application (Kubernetes Ingress on OKE)](#expose-and-access-the-application-kubernetes-ingress-on-oke)
  - [OCI authentication options on OKE (Workload Identity, Instance Principals)](#oci-authentication-options-on-oke-workload-identity-instance-principals)
  - [Kubernetes operational guardrails](#kubernetes-operational-guardrails)
  - [Verification and health checks](#verification-and-health-checks)
  - [Troubleshooting and FAQ](#troubleshooting-and-faq)
  - [Cleanup](#cleanup)
  - [Notes](#notes)
  - [Keywords](#keywords)

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

## Provision OKE (Oracle Kubernetes Engine) and Autonomous Database with Terraform

```bash
cd deploy/terraform
terraform init
terraform apply --auto-approve
cd ../..
```

```bash
cd deploy/terraform && terraform init && terraform apply --auto-approve && cd ../..
```

After apply, a kubeconfig is generated at `deploy/terraform/generated/kubeconfig`.

## Build and publish container images to OCI Container Registry (OCIR)

Use the release script to version, build, login, and push images to OCIR:

```bash
npx zx scripts/release.mjs 
```

## Generate and apply Kustomize overlays

Create kustomization files that reference the newly published images:

```bash
npx zx scripts/kustom.mjs
```

Overlays are under:

- [deploy/k8s/backend/](deploy/k8s/backend/)
- [deploy/k8s/web/](deploy/k8s/web/)
- [deploy/k8s/ingress/](deploy/k8s/ingress/)
- [deploy/k8s/overlays/prod/](deploy/k8s/overlays/prod/)

You can inject these via env vars/ConfigMap if preferred. See [DATABASE.md](DATABASE.md) for schema details and [RAG.md](RAG.md) for pipeline endpoints.

## Deploy to the OKE Kubernetes cluster

Export kubeconfig created by Terraform and apply the Kustomize overlay:

```bash
export KUBECONFIG="$(pwd)/deploy/terraform/generated/kubeconfig"
kubectl cluster-info
kubectl apply -k deploy/k8s/overlays/prod
```

Check deployments and wait until `READY` equals desired replicas:

```bash
kubectl get deploy -n backend
```

## Expose and access the application (Kubernetes Ingress on OKE)

Fetch the public IP of the LoadBalancer service:

```bash
echo $(kubectl get service \
  -n backend \
  -o jsonpath='{.items[?(@.spec.type=="LoadBalancer")].status.loadBalancer.ingress[0].ip}')
```

If empty, wait a few minutes and retry; provisioning may take time. Open the IP in your browser to access the web UI.

Ingress manifests live under [deploy/k8s/ingress/](deploy/k8s/ingress/). For a custom domain, create a DNS A record pointing to the LoadBalancer IP and, if needed, configure TLS in your Ingress (see ingress manifests for examples).

## OCI authentication options on OKE (Workload Identity, Instance Principals)

- Workload Identity (recommended) or Instance Principals for the backend. See service account and RBAC in [deploy/k8s/backend/service-account.yaml](deploy/k8s/backend/service-account.yaml).
- Avoid local file dependencies in cluster (use Kubernetes Secrets and ConfigMaps).
- Configure `genai.region` and `compartment_id` via environment or application config.
- Push/pull images via OCIR with proper auth; see [scripts/release.mjs](scripts/release.mjs).

## Kubernetes operational guardrails

- Vendor‑aware parameter handling (avoid sending unsupported params to specific models)
- Telemetry via `interactions` table (latency, tokens, costs) for observability and budgeting
- Resource requests/limits and optional HPA (add to kustomize if desired)
- Pod Disruption Budgets for high availability
- Secrets and ConfigMaps for environment separation and secure configuration

## Verification and health checks

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

Quick API checks (see [RAG.md](RAG.md) for details):

```bash
# Models list
kubectl port-forward -n backend deploy/backend 8080:8080 &
curl http://localhost:8080/api/genai/models

# RAG (ensure you uploaded PDFs first)
curl -X POST http://localhost:8080/api/genai/rag \
  -H "Content-Type: application/json" \
  -d '{"question":"What does section 2 cover?","modelId":"ocid1.generativeaimodel.oc1...."}'
```

## Troubleshooting and FAQ

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

## Notes

- This blueprint targets Oracle AI Database features through ADB for vector‑ready, assistant‑grade persistence.
- See [DATABASE.md](DATABASE.md) for Liquibase migrations and table layouts, [RAG.md](RAG.md) for RAG pipeline usage, and [README.md](README.md) for the broader “From GUIs to RAG” story.

## Keywords

Kubernetes, Oracle Kubernetes Engine, OKE, Oracle Cloud Infrastructure, OCI, OCI Generative AI, Autonomous Database, Oracle AI Database, RAG, Retrieval‑Augmented Generation, Terraform on OCI, Kustomize, Kubernetes Ingress, OCIR, Oracle JET, Spring Boot on Kubernetes, vector search, embeddings, ANN index, Workload Identity, Instance Principals
