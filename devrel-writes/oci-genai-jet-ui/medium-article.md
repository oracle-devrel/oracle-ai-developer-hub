# <Compelling Title: How We Ship Cloud‑Native AI on Oracle Without the Drama>

<Hook>Enterprises want AI that’s secure, observable, and production‑ready — not just a weekend demo. Here’s a pragmatic blueprint, grounded in a real open‑source app, for taking an idea from laptop to Kubernetes using Oracle AI Database and OCI Generative AI.</Hook>

## The Story
Every team I meet wants the same thing: use LLMs to unlock their data — safely, at scale, and without re‑architecting the universe. The gap between a demo and a dependable product is where projects stall. This repository exists to collapse that gap: a reference implementation that shows how to blend UI, services, Kubernetes, and infrastructure into one cohesive path to production.

## The Problem
- Demos don’t translate to durable systems (secrets, observability, upgrades).
- AI features often drift from app and infra realities (token limits, cost, latency).
- Docs are scattered, and branding clarity matters for stakeholders.
- Teams need a repeatable workflow and concrete code, not just slides.

## Oracle Solution
- Oracle AI Database capabilities (vector search, Select AI) — branding compliant and designed for enterprise workloads.
- OCI Generative AI — managed access to LLMs with governance and scale.
- A production‑minded architecture in this repo that’s minimal‑diff and secret‑safe:
  - Oracle JET + React UI (TypeScript)
  - Spring Boot backend with resilience policies
  - Kubernetes with Kustomize overlays
  - Terraform for OCI (OKE, Networking, Autonomous Database)
  - Guardrails for branding, security, and contributions

### Architecture (High‑Level)
```mermaid
flowchart LR
  subgraph Client
    A[Oracle JET + React UI]
  end
  subgraph Backend
    B[Spring Boot API & WebSocket]
  end
  subgraph Data
    C[(Oracle AI Database)]
  end
  subgraph AI
    D[OCI Generative AI Services]
  end
  subgraph Platform
    E[Kubernetes (OKE)]
    F[Terraform (OCI)]
  end

  A <-- STOMP/WebSocket + HTTPS --> B
  B <-- SQL/Vector/Select AI --> C
  B <-- API Calls --> D
  E --- A
  E --- B
  F --> E
  F --> C
```

## What This Enables
- Search and reasoning on enterprise data with vector retrieval.
- Secure, observable, and scalable deployment on OCI.
- A single repository that shows how UI, backend, K8s, and Terraform work together.
- Faster path from prototype to production using minimal‑diff workflows.

## Looking Ahead
- Responsible AI controls: rate limits, safety filters, and audit trails.
- Cost‑aware defaults and token budgeting.
- Modular RAG patterns to fit your domain.
- Extensible scripts and overlays for multi‑env rollouts.

---

## Links and References
- Project: [README.md](../../README.md)
- Models & limits: [MODELS.md](../../MODELS.md)
- Retrieval patterns: [RAG.md](../../RAG.md)
- Services & endpoints: [SERVICES_GUIDE.md](../../SERVICES_GUIDE.md)
- Troubleshooting: [TROUBLESHOOTING.md](../../TROUBLESHOOTING.md)
- Local setup: [LOCAL.md](../../LOCAL.md)
- Workflow & branding guardrails:
  - [.clinerules/workflows/devrel-content.md](../../.clinerules/workflows/devrel-content.md)
  - [.clinerules/branding-oracle-ai-database.md](../../.clinerules/branding-oracle-ai-database.md)
  - [.clinerules/secrets-and-credentials-handling.md](../../.clinerules/secrets-and-credentials-handling.md)

---

## Author Notes (Replace with your story)
- Replace the title and hook with your narrative (why this matters to your audience).
- Pull 2–3 short code snippets from this repo (UI, backend, deploy) and annotate what they achieve.
- Keep secrets out — use placeholders only.
- Keep “Oracle AI Database” branding exact.

---
Disclaimer: This article references “Oracle AI Database”. Version details, where noted, are for compatibility only.
