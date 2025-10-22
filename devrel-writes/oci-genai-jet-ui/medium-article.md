# From GUIs to RAG: Shipping Understanding on Oracle Cloud

We don’t use computers the way we used to. We moved from command lines to GUIs, from click‑and‑type to touch and voice—and now to assistants that understand intent. The next leap isn’t a new button; it’s software that adapts to people. Assistants change the unit of work from “click these seven controls” to “state your intent.”

But shipping that leap in the enterprise takes more than calling a model API. It takes durable context, guardrails, observability, and a user experience people trust. This post is a practical story and blueprint for that shift—grounded in an open repository you can run today—built with Oracle Database 26ai, OCI Generative AI, Spring Boot, and Oracle JET.

- Project repo: oci-generative-ai-jet-ui
- Architecture: Data → Model → Service (DMS)
- Use cases: Support assistants, internal knowledge search, workflow copilots
- Demo: Chat with RAG (Retrieval‑Augmented Generation) over your own documents

## The story: From features to understanding

For years, we added features and hoped users could navigate them. It worked—until cognitive overload became the norm. Teams designed tabs, toggles, and toolbars; power‑users thrived; everyone else stalled.

Assistants flip the model. The UI becomes a conversation, the system does the tedious work, and outcomes matter more than pathways. Yet the “hello world” prototype often hides the real effort: How does the assistant remember what matters? How do you ground responses in your own knowledge? How do you audit cost, latency, and behavior?

A decade of shipping software taught a simple lesson: people don’t want more features; they want more understanding. Assistants are how we ship understanding.

## The problem: Turning intent into enterprise‑grade outcomes

Prototypes break down in production because:
- Statelessness: Chats don’t persist, so context resets constantly.
- No grounding: Answers drift without retrieval from your sources.
- Parameter hazards: Model knobs differ by vendor; invalid combinations cause brittle failures.
- Lack of observability: No record of latency, tokens, or content flow to debug or forecast cost.
- Fragile UX: Uploads, streaming, and error states need robust UI patterns.

What’s needed is a simple but reliable architecture that scales: Data → Model → Service.

## Oracle solution: The DMS architecture

We apply a straightforward pattern:

- Data (Oracle Database 26ai via Autonomous Database)
  - Durable chat history (conversations, messages)
  - Memory (key/value and long‑form)
  - Knowledge Base (KB) tables for RAG
  - Telemetry (interactions: latency, tokens, cost)
- Model (OCI Generative AI)
  - Vendor‑aware inference for Cohere, Meta, xAI
  - Prompt shaping and retrieval grounding
  - Parameter safety rails per vendor
- Service (Spring Boot)
  - REST + WebSocket endpoints for chat, RAG, uploads, and models list
  - Liquibase migrations for evolution‑safe schema
  - OCI auth: local config, OKE Workload Identity, or Instance Principals
- Interface (Oracle JET)
  - Chat, Upload, Settings (Use RAG toggle)
  - Accessible, responsive, enterprise‑grade components
  - Opt‑in debug logs; robust error states

### Visualizing the flow

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

The result is simple to reason about, easy to evolve, and ready for production practices.

## How it works (the blueprint you can run)

- Upload: Users upload PDFs. The backend extracts content and populates the KB tables.
- Retrieve: A RAG query runs a hybrid search over that KB to fetch relevant chunks.
- Generate: The model composes a grounded response using retrieved context and user intent.
- Persist: The system records the conversation and telemetry for observability and iteration.
- Iterate: You monitor costs and latency, adjust parameters, and improve chunking or prompts.

This translates directly into the repository’s features:
- Chat and summarization with multiple vendors/models
- RAG over your PDFs (upload → index → ask)
- Telemetry for model calls and cost insight
- Liquibase‑managed schema for evolvability
- Oracle JET UI for enterprise UX

## Why Oracle for assistants

- Oracle Database 26ai: Durable context, vector‑ready schemas, SQL‑driven governance
- OCI Generative AI: Enterprise‑grade access to multiple vendors, consistent auth and control
- Integration excellence: Spring Boot, Liquibase, Oracle JET—familiar tools for teams
- Production‑ready: Observability and control baked into the data layer and service tier

## The user experience: Assistants people can trust

An assistant is only as good as the experience:
- Clear uploads and progress states
- A resilient chat transcript with grounded citations or references
- A settings panel that doesn’t expose users to brittle model quirks
- Fast responses with streaming‑friendly components
- Recoverable error states; debug when you opt‑in, quiet when you don’t

Oracle JET provides the UI layer where all of this lives—enterprise‑grade components, accessibility, and performance.

## Real‑world scenarios

- Support assistant: Grounded answers from product docs and playbooks, with queries and responses persisted to audit trails.
- Internal knowledge search: Policy or design discovery across PDFs and knowledge bases with durable memory.
- Workflow co‑pilot: Parameterized prompting for recurring tasks, with cost controls and latency visibility.

## Practical: Run locally, then go cloud‑native

Local (developer loop)
1) Configure backend data source and OCI in `backend/src/main/resources/application.yaml`
2) Run backend (Gradle) and UI (Oracle JET) locally
3) Upload a PDF and ask a question with RAG enabled

Cloud‑native (production loop)
1) Provision Oracle Kubernetes (OKE) and Autonomous Database (Terraform)
2) Build/push images to OCIR, generate Kustomize overlays
3) Mount ADB Wallet via Kubernetes secret; set `TNS_ADMIN`
4) Apply manifests; access via Ingress; observe telemetry; iterate

The same DMS architecture spans both loops.

## Principles: What this blueprint optimizes for

- Modularity: Each layer has a single concern and can be evolved without breaking others
- Observability first: Understand cost and latency early
- Vendor‑aware safety: Don’t pass invalid parameters; normalize where possible
- Document ground truth: RAG should cite and reflect your knowledge base
- UX matters: Assistants are the “understanding surface”—treat them like a product

## What’s next: Assistants as default interfaces

Assistants will become the default way people interact with complex systems. As that happens:
- Governance deepens: Data lineage and policy become first‑class
- Telemetry informs cost/performance trade‑offs in real time
- Agentic flows expand: Planning, tools, and multi‑step orchestration integrate more deeply
- Teams blend UX and ML ops: The assistant UI and the learning loops become inseparable

The journey starts with RAG and intent‑first design. The DMS pattern provides the foundation for everything that follows.

## Quick references

- Overview and architecture: README.md
- Oracle JET frontend: JET.md
- Kubernetes (OKE) and Terraform: K8S.md
- RAG flow and usage: RAG.md
- Database and Liquibase: DATABASE.md
- Models and parameters: MODELS.md
- Troubleshooting: TROUBLESHOOTING.md

## Example config (LLM‑friendly JSON)

```json
{
  "compartment_id": "ocid1.compartment.oc1..exampleuniqueID",
  "model_id": "cohere.command-r-plus",
  "region": "US_CHICAGO_1"
}
```

## Q&A (for grounding and learning)

- Q: How does the assistant stay accurate over proprietary docs?
  A: It uses RAG: chunked content from your PDFs is stored in KB tables; queries retrieve relevant chunks; the model composes grounded answers.

- Q: How do I monitor performance and cost?
  A: The service records latency, tokens, and cost proxies in the `interactions` table—query it to see trends and anomalies.

- Q: What about vendor‑specific quirks?
  A: The backend is vendor‑aware and avoids sending unsupported parameters to specific models to prevent brittle failures.

## Call to action

Run the blueprint. Upload your documents. Watch grounded answers replace guesswork. Then iterate with telemetry and governance as your compass. Assistants aren’t a novelty—they’re how we ship understanding.

- Get started in the repo: README.md → JET.md → K8S.md
- Try the RAG flow: RAG.md
- Explore the schema: DATABASE.md
- See model details: MODELS.md

---

ORACLE AND ITS AFFILIATES DO NOT PROVIDE ANY WARRANTY WHATSOEVER, EXPRESS OR IMPLIED, FOR ANY SOFTWARE, MATERIAL OR CONTENT OF ANY KIND CONTAINED OR PRODUCED WITHIN THIS REPOSITORY, AND IN PARTICULAR SPECIFICALLY DISCLAIM ANY AND ALL IMPLIED WARRANTIES OF TITLE, NON-INFRINGEMENT, MERCHANTABILITY, AND FITNESS FOR A PARTICULAR PURPOSE. FURTHERMORE, ORACLE AND ITS AFFILIATES DO NOT REPRESENT THAT ANY CUSTOMARY SECURITY REVIEW HAS BEEN PERFORMED WITH RESPECT TO ANY SOFTWARE, MATERIAL OR CONTENT CONTAINED OR PRODUCED WITHIN THIS REPOSITORY. IN ADDITION, AND WITHOUT LIMITING THE FOREGOING, THIRD PARTIES MAY HAVE POSTED SOFTWARE, MATERIAL OR CONTENT TO THIS REPOSITORY WITHOUT ANY REVIEW. USE AT YOUR OWN RISK.
