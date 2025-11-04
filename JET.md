# Oracle JET Frontend: From GUIs to Assistants

This UI turns the Data → Model → Service (DMS) architecture into a usable assistant: a fast, accessible Oracle JET web app for chat, RAG, upload, and settings.

We moved from command lines to GUIs, from click-and-type to touch and voice—and now to assistants that understand intent. This frontend is the “understanding surface” for the blueprint: Oracle JET on the web, Spring Boot in the middle, OCI Generative AI for models, and Oracle AI Database for durable context and retrieval.

## Why JET for assistants

- Enterprise-ready components, theming, and accessibility
- Preact-based performance and small footprint
- Clear separation of concerns: UI here; model/data logic in the Spring Boot backend
- Fast iteration with npx ojet serve and direct integration with REST/WebSocket APIs

## App structure (selected)

- app/src/components/app.tsx — root layout and routing
- app/src/components/content/chat.tsx — chat transcript and input; integrates with backend chat/RAG
- app/src/components/content/upload.tsx — PDF upload to /api/upload
- app/src/components/content/settings.tsx — model selection, Use-RAG toggle, parameters
- app/src/components/content/summary.tsx — summary panel (example of model-adjacent UX)
- app/src/components/content/stomp-interface.tsx — WebSocket/STOMP integration
- app/src/components/content/websocket-interface.tsx — alternative WebSocket interface
- app/src/libs/debug.ts — opt-in debug logging via localStorage.debug === "1"
- app/src/styles/app.css — layout, fixed input bar, list padding
- app/src/index.ts — application bootstrap
- app/src/index.html — base HTML

## Behavior and logging

- Database keepalive: the UI pings /api/kb/diag on startup and periodically
  - On first success logs “DB: database active”
  - Subsequent successes are silent; failures log warn; recovery logs info
- Fixed chat input bar: input anchored at the bottom; list view includes extra bottom padding
- Opt-in debug logs controlled by localStorage.debug
  - Enable: localStorage.setItem("debug", "1")
  - Disable: localStorage.removeItem("debug")
- RAG in Settings: toggle “Use RAG” to ground chat on your uploaded documents
- Upload header: modelId header is optional for POST /api/upload; server no longer requires it

## Backend interface (representative)

- POST /api/genai/chat — freeform chat (vendor-aware parameters)
- POST /api/genai/rag — RAG-grounded responses using KB tables
- GET /api/genai/models — enumerate available models
- POST /api/upload — upload PDFs; server extracts/indexes for RAG
- GET /api/kb/diag — diagnostics/keepalive for database connection

See also:
- RAG pipeline and usage: RAG.md
- Models and parameters: MODELS.md
- Database schema and Liquibase: DATABASE.md

## Run locally

Backend
```bash
cd backend
./gradlew bootRun
# http://localhost:8080
```

Web UI
```bash
cd ../app
npm ci
npm run serve
# http://localhost:8000
```

Default dev ports
- Backend: 8080
- Web UI: 8000

## Configuration

- Local dev: UI calls http://localhost:8080 by default (see fetch/WS endpoints in components)
- In cluster: UI is served same-origin behind Ingress; no port dance required
- Models: selected in Settings; backend enforces vendor-compatible parameters per provider
- Use RAG: toggle determines if chat requests are grounded on uploaded KB content

## Accessibility, UX, and performance

- Keyboard-friendly navigation and screen-reader-friendly components
- Minimal re-renders on chat updates; transcript updated incrementally
- Error paths are visible and recoverable; optimistic UI used where safe
- Streaming-friendly transcript components (when enabled)

## Extending the UI

- Add a new panel: create a component under app/src/components/content and route it from app.tsx
- Add model parameters: extend settings.tsx and propagate fields to request payloads
- Theming/icons: adjust app/src/styles and Oracle JET theme variables
- Markdown rendering: see custom md-wrapper and oj-ref-marked components under app/src/components

## LLM-friendly documentation patterns

- Numbered flows for tasks and reproducible steps
- JSON request/response samples inline for quick testing
- Comments and code annotations explaining intent, inputs, outputs
- Mermaid diagrams in the main README for architecture visualization
- Q&A pairs for RAG verification scenarios

Example request payload (chat with RAG enabled)
```json
{
  "question": "Summarize section 2 and list key decisions.",
  "modelId": "ocid1.generativeaimodel.oc1..exampleuniqueID",
  "useRag": true
}
```

## Troubleshooting

- Unknown host or CORS in local dev: ensure backend is running on http://localhost:8080 and UI on http://localhost:8000
- Parameter validation errors: check MODELS.md for vendor-specific constraints (e.g., presencePenalty not supported on some vendors)
- RAG returns empty: verify documents uploaded successfully and KB tables populated (see DATABASE.md and RAG.md)
- No “DB: database active” message: ensure backend datasource configuration is correct and ADB is reachable

## Related guides

- From GUIs to RAG: Building a Cloud‑Native RAG on Oracle Cloud (overview): README.md
- Cloud-native deployment (OKE, Terraform, Kustomize): K8S.md
- RAG pipeline and usage: RAG.md
- Models and parameters: MODELS.md
- Database schema and Liquibase: DATABASE.md
- Troubleshooting: TROUBLESHOOTING.md

## License

Licensed under the Universal Permissive License (UPL), Version 1.0. See LICENSE.

ORACLE AND ITS AFFILIATES DO NOT PROVIDE ANY WARRANTY WHATSOEVER, EXPRESS OR IMPLIED, FOR ANY SOFTWARE, MATERIAL OR CONTENT OF ANY KIND CONTAINED OR PRODUCED WITHIN THIS REPOSITORY, AND IN PARTICULAR SPECIFICALLY DISCLAIM ANY AND ALL IMPLIED WARRANTIES OF TITLE, NON-INFRINGEMENT, MERCHANTABILITY, AND FITNESS FOR A PARTICULAR PURPOSE.  FURTHERMORE, ORACLE AND ITS AFFILIATES DO NOT REPRESENT THAT ANY CUSTOMARY SECURITY REVIEW HAS BEEN PERFORMED WITH RESPECT TO ANY SOFTWARE, MATERIAL OR CONTENT CONTAINED OR PRODUCED WITHIN THIS REPOSITORY. IN ADDITION, AND WITHOUT LIMITING THE FOREGOING, THIRD PARTIES MAY HAVE POSTED SOFTWARE, MATERIAL OR CONTENT TO THIS REPOSITORY WITHOUT ANY REVIEW. USE AT YOUR OWN RISK.
