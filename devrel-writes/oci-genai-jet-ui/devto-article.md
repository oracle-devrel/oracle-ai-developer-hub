# Build and Ship a Cloud‑Native AI App on Oracle: A Code‑First Guide

## Problem
You want to ship an AI‑powered app that:
- Uses Oracle AI Database for vector search and Select AI
- Integrates OCI Generative AI services
- Runs on Kubernetes (OKE) with Terraform‑provisioned infrastructure
- Stays secure (no secrets in code), observable, and production‑safe
- Avoids massive refactors and “works only on my laptop” failures

This guide is grounded in a working open‑source repository and shows how to wire UI, backend, K8s, and Terraform together with minimal‑diff changes and exact branding: “Oracle AI Database”.

## Architecture
```mermaid
flowchart LR
  subgraph UI
    A[Oracle JET + React (TypeScript)]
  end
  subgraph API
    B[Spring Boot REST & WebSocket/STOMP]
  end
  subgraph DB
    C[(Oracle AI Database)]
  end
  subgraph LLM
    D[OCI Generative AI Services]
  end
  subgraph Platform
    E[Kubernetes (OKE)]
    F[Terraform for OCI]
  end

  A <-- HTTPS + STOMP/WebSocket --> B
  B <-- SQL/Vector/Select AI --> C
  B <-- API --> D
  F --> E
  F --> C
```

Key properties
- UI: Oracle JET + React, TypeScript strict, STOMP/WebSocket integration
- Backend: Spring Boot 3.x, Java 17, Resilience4j, Actuator/Micrometer
- Data & AI: Oracle AI Database (vector, Select AI), OCI Generative AI
- Deploy: Kubernetes manifests with Kustomize overlays; Terraform for OKE/ADB/VCN
- Guardrails: Security, branding, contribution policy, and docs linking

## Key Code

> Replace TODO blocks by copying actual snippets from this repo, then annotate purpose, inputs, outputs. Keep secrets out; use placeholders.

1) UI WebSocket/STOMP client (subscribe, cleanup)
```tsx
// TODO: paste a minimal, real snippet from app/src/components/content/stomp-interface.tsx
// - Show client creation/activation
// - Subscribe to a topic and handle messages
// - Properly deactivate on unmount to avoid leaks
```

2) UI settings/model selection (type‑safe config)
```tsx
// TODO: paste snippet from app/src/components/content/settings.tsx
// - Show model selection/state handling
// - Keep props typed, avoid "any"
// - Connect to config in app/oraclejafconfig.json
```

3) Backend controller/DTO (validation + API contract)
```java
// TODO: paste a small @RestController method and its DTO
// - Show @Valid/@NotBlank usage for inputs
// - Return a typed response to align with the UI
```

4) WebSocket/STOMP backend wiring
```java
// TODO: paste WebSocketMessageBrokerConfigurer snippet
// - setApplicationDestinationPrefixes("/app")
// - enableSimpleBroker("/topic")
// - registerStompEndpoints("/ws") with allowed origins
```

5) Kustomize overlay: image/replicas/resources patch
```yaml
# TODO: paste a small patchesStrategicMerge or patchesJson6902 example from deploy/k8s/** 
# - Change image tag or replicas in an overlay-focused way
```

6) Terraform tfvars generation (secure, no secrets in git)
```bash
# Generate tfvars from template (no secrets committed)
node scripts/tfvars.mjs --env dev
terraform fmt -check && terraform validate
terraform plan
```

7) Actuator health and metrics
```bash
# After backend starts (locally or via K8s port-forward)
curl -s http://localhost:8080/actuator/health | jq
# TODO: include metrics or liveness/readiness endpoints if exposed
```

## Gotchas

- WebSocket upgrades:
  - Ensure the endpoint path matches (e.g., /ws).
  - Confirm proxies/ingress forward upgrade headers.
  - UI must deactivate the STOMP client on unmount to avoid ghost subscriptions.

- CORS and cross‑origin:
  - Align allowed origins in backend WebSocket and REST config with the UI host.
  - For local dev, use `ojet serve` and verify proxy behavior as needed.

- Token/latency budget:
  - Keep model max tokens, temperature, and timeouts sane; don’t blow SLOs.
  - Document defaults in MODELS.md and align with UI caps.

- Secrets:
  - No real secrets in code, K8s YAML, or Terraform files.
  - Use environment variables or K8s Secrets mounted at runtime.
  - See .clinerules/secrets-and-credentials-handling.md.

- Kustomize consistency:
  - Ensure Deployment `containerPort` equals Service `targetPort`, and Ingress routes to the right Service/port.
  - Validate overlays with `kustomize build` or `node scripts/kustom.mjs --overlay prod --dry-run`.

See also: [TROUBLESHOOTING.md](../../TROUBLESHOOTING.md)

## Best Practices

- Security
  - Never commit credentials, ADB wallet files, or real endpoints.
  - Reference secrets via K8s Secret refs or env vars only.
- Cost & performance
  - Bound tokens and retry policies; add backoff.
  - Cache small metadata where safe; avoid unnecessary high‑token prompts.
- Observability
  - Actuator health/metrics; consider Prometheus scraping in K8s.
  - Structured logs; avoid sensitive payloads in logs.
- Resilience
  - Timeouts, circuit breakers (Resilience4j), and idempotent handlers.
- Minimal‑diff workflows
  - Prefer additive patches; avoid sweeping refactors.
  - Keep DTOs stable and extend with optional fields when needed.

## Resources

- Project overview: [README.md](../../README.md)
- Models: [MODELS.md](../../MODELS.md)
- Retrieval patterns: [RAG.md](../../RAG.md)
- Services & endpoints: [SERVICES_GUIDE.md](../../SERVICES_GUIDE.md)
- Local & troubleshooting: [LOCAL.md](../../LOCAL.md), [TROUBLESHOOTING.md](../../TROUBLESHOOTING.md)
- Authoring workflow & branding guardrails:
  - [.clinerules/workflows/devrel-content.md](../../.clinerules/workflows/devrel-content.md)
  - [.clinerules/branding-oracle-ai-database.md](../../.clinerules/branding-oracle-ai-database.md)
  - [.clinerules/secrets-and-credentials-handling.md](../../.clinerules/secrets-and-credentials-handling.md)

---

Branding: Use “Oracle AI Database”. Version details are secondary and should be phrased as “Oracle AI Database (version details for compatibility only)”.
