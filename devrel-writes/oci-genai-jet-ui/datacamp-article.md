# Deploy a Cloud‑Native AI App on Oracle: Hands‑On With UI, API, K8s, and Terraform

## Learning Goals
- Understand the end‑to‑end architecture for a production‑ready AI app on Oracle.
- Configure and run a TypeScript UI (Oracle JET + React) with a Spring Boot backend.
- Apply Kubernetes (OKE) and Terraform patterns for scalable deployment.
- Use “Oracle AI Database” features (vector, Select AI) and OCI Generative AI safely.
- Practice minimal‑diff changes, security, and observability.

## Prerequisites
- Accounts/Tools (no secrets in code)
  - Oracle Cloud Infrastructure (OCI) account and basic IAM setup
  - Node.js 18+ and npm
  - Java 17 and Gradle wrapper (repo includes `backend/gradlew`)
  - Docker (optional for local images)
  - kubectl and access to OKE (or local K8s for practice)
  - Terraform 1.5+ (for infra workflows)
- This repository cloned locally
- Branding compliance: Use “Oracle AI Database” exactly; avoid legacy names

## Concepts (Quick Explain)
- Oracle AI Database: Enterprise database with native AI features (vector search, Select AI). Use the exact branding.
- OCI Generative AI: Managed LLM endpoints for enterprise use cases.
- Minimal‑diff engineering: Prefer additive changes, keep secrets out of source, and align UI/Backend/K8s/Terraform.
- Observability: Spring Boot Actuator + Micrometer; enable readiness/liveness for stable rollouts.

## Architecture (At a Glance)
```mermaid
flowchart LR
  UI[Oracle JET + React (TypeScript)] -->|HTTPS + STOMP| API[Spring Boot REST + WebSocket]
  API -->|SQL/Vector/Select AI| DB[(Oracle AI Database)]
  API -->|API| LLM[OCI Generative AI]
  Terraform --> OKE[Kubernetes (OKE)]
  Terraform --> DB
  UI & API --> OKE
```

## Hands‑On Steps

1) Explore the repository layout
- Top‑level docs: README.md, MODELS.md, RAG.md, SERVICES_GUIDE.md, TROUBLESHOOTING.md
- UI (Oracle JET + React): `app/`
- Backend (Spring Boot): `backend/`
- Kubernetes manifests: `deploy/k8s/**`
- Terraform for OCI: `deploy/terraform/**`
- Scripts/helpers: `scripts/**`

2) Run the UI locally
```bash
cd app
npm ci
# Oracle JET dev server
npx ojet serve --server-port=8000
# or package.json scripts if defined
```
- Open http://localhost:8000
- Review config in `app/oraclejafconfig.json` (no secrets, placeholders only).

3) Run the backend locally
```bash
cd backend
./gradlew clean build
./gradlew bootRun
```
- Verify health: `curl -s http://localhost:8080/actuator/health | jq`
- Check logs for startup messages; ensure no secrets are required for basic flows.

4) Wire UI to backend (local)
- If the UI calls the backend directly, confirm CORS and/or a local proxy works.
- Ensure WebSocket endpoint path matches (commonly `/ws`).
- Inspect UI source:
  - `app/src/components/content/*.tsx` (chat, answer, settings, summary)
  - `app/src/components/content/stomp-interface.tsx` and `websocket-interface.tsx`
- Inspect backend WebSocket config and REST controllers (Spring Boot).

5) Try WebSocket/STOMP in the UI
- In the UI code, observe STOMP client lifecycle:
  - Activate on mount
  - Subscribe to `/topic/...`
  - Deactivate on unmount to avoid leaks
- Check browser DevTools → Network → WS frames for CONNECT/SUBSCRIBE/MESSAGE.

6) Introduce a minimal‑diff change (UI)
- Example: add an optional prop to a small component and render conditionally.
- Keep TypeScript types strict; avoid `any`.
- Rebuild and verify the change does not break existing calls.

7) Observability sanity checks (Backend)
```bash
# Health
curl -s http://localhost:8080/actuator/health | jq
# Liveness/Readiness (if configured)
# curl -s http://localhost:8080/actuator/health/liveness | jq
# curl -s http://localhost:8080/actuator/health/readiness | jq
```
- Review logs for errors; ensure timeouts/retries are configured where needed.

8) Kubernetes manifests walkthrough
- Base manifests: `deploy/k8s/app/`, `deploy/k8s/backend/`, `deploy/k8s/web/`, `deploy/k8s/ingress/`
- Overlays (example): `deploy/k8s/overlays/prod/`
- Validate:
```bash
# Option A: use kustomize directly (if installed)
kustomize build deploy/k8s/overlays/prod | head -n 50

# Option B: repo helper
node scripts/kustom.mjs --overlay prod --dry-run
```
- Confirm containerPort/targetPort alignment and Ingress routing.

9) Terraform for OCI (no secrets in repo)
```bash
cd scripts
node tfvars.mjs --env dev
# This renders terraform.tfvars from mustache template (excluded from git)

cd ../deploy/terraform
terraform fmt -check
terraform validate
terraform plan
```
- Do not commit `terraform.tfvars`. Pass sensitive values via environment or secret stores.
- Review `versions.tf` for pinned providers.

10) Structured configuration example (placeholders only)
```json
{
  "compartment_id": "ocid1.compartment.oc1..exampleuniqueID",
  "oke_cluster_name": "genai-jet-oke-dev",
  "model_id": "cohere.command-r-plus",
  "region": "example-region-1"
}
```
- Use this pattern for documentation only — never store real secrets.

11) Branding validation
- Search for legacy brand variants (optional editorial step).
- Ensure all user‑facing text uses “Oracle AI Database” exactly.

12) Prepare a minimal PR
- Add only your focused changes (docs or code).
- Include screenshots/diagram previews for UI changes.
- Reference the authoring workflow and branding rule.
- Consider a brief `CHANGES.md` entry for user‑visible docs.

## Try It Yourself (Exercises)
- Exercise 1: Add a new model option to the UI settings (docs‑only config).
  - Update `app/oraclejafconfig.json` with a new model entry (no secrets).
  - Expose it in the settings UI (optional toggle). Keep changes additive.
- Exercise 2: Add a readiness probe to the backend Deployment via a kustomize patch.
  - Create a `patches/resources-patch.yaml` with readiness/liveness.
  - Validate with `kustomize build`.
- Exercise 3: Add a small DTO validation rule in a REST endpoint and surface user‑friendly errors in the UI.

## Wrap‑Up
You stood up a UI and backend locally, inspected WebSocket behavior, validated K8s manifests, and rehearsed Terraform planning — all while staying minimal‑diff, secure, and branding‑compliant. This pattern scales from dev to prod without rewriting core pieces.

---

## References
- Project: [README.md](../../README.md)
- Models: [MODELS.md](../../MODELS.md)
- RAG: [RAG.md](../../RAG.md)
- Services: [SERVICES_GUIDE.md](../../SERVICES_GUIDE.md)
- Troubleshooting & Local: [TROUBLESHOOTING.md](../../TROUBLESHOOTING.md), [LOCAL.md](../../LOCAL.md)
- Authoring & Branding Guardrails:
  - [.clinerules/workflows/devrel-content.md](../../.clinerules/workflows/devrel-content.md)
  - [.clinerules/branding-oracle-ai-database.md](../../.clinerules/branding-oracle-ai-database.md)
  - [.clinerules/secrets-and-credentials-handling.md](../../.clinerules/secrets-and-credentials-handling.md)

---

Branding: Use “Oracle AI Database”. Version details are secondary and should be phrased as “Oracle AI Database (version details for compatibility only)”.
