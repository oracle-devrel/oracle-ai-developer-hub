Title: From GUIs to GenAI: Building a Cloud‑Native AI Assistant on Oracle Cloud with Java + Spring Boot

Subtitle: A simple Data–Model–Service pattern for shipping production‑ready assistants on OCI, with local development in Java and an Oracle JET front end

Hook
We don’t interact with computers the way we used to. We moved from command lines to GUIs, from click‑and‑type to touch and voice—and now to assistants that understand intent. The next leap isn’t a new button; it’s systems that adapt to people.

This guide is a story about that leap—and a practical blueprint you can apply today with Java. We’ll design and deploy a cloud‑native GenAI assistant using Oracle Cloud Infrastructure (OCI), Oracle Database 23ai, a Java Spring Boot backend, and Oracle JET for the frontend. Whether your use case is support chat, internal knowledge search, or workflow automation, one simple pattern works: Data → Model → Service.

The story: why assistants, why now
A decade of UX work taught a simple lesson: people don’t want more features; they want more understanding. AI changes the unit of work from “click these 7 controls” to “state your intent.” But shipping that future requires more than an LLM API. It needs architecture, discipline, and production‑grade foundations—plus a developer‑friendly stack for local iteration.

Why Oracle + AI for this pattern
- Oracle Database 23ai: Native vector search, JSON‑first data, and Select AI to reason over data with SQL governance
- OCI Generative AI: Enterprise‑grade access to Cohere/Meta/Google families with tenancy‑level controls
- Integration excellence: IAM, networking, logging, tracing—without stitching together a dozen tools
- Production‑ready: A clear path from laptop to OKE (Kubernetes) with proper secrets, scaling, and monitoring
- Developer‑friendly (Java first): Spring Boot + Gradle, OCI Java SDKs, and Oracle JET for a trustworthy UI

The problem to solve
Most teams hit the same wall: a prototype that works in a notebook won’t scale to production. You need:
- Data that’s governable, searchable, versioned
- Model access that’s secure, observable, cost‑aware
- Services that are consistent, testable, evolvable
- A UI that explains results and builds trust

The solution: the DMS pattern
We use a simple pattern—Data, Model, Service—to build AI assistants that scale.

- Data Layer: Where knowledge lives and evolves (documents, FAQ pairs, embeddings, telemetry)
- Model Layer: Where you access LLMs (chat, summarize, embed) with the right prompts and parameters
- Service Layer: Where business logic, security, state, and APIs live

Architecture (Mermaid)
```mermaid
flowchart LR
  subgraph Client
    JET[Oracle JET Web UI]
  end

  subgraph Service Layer (Java)
    API[Spring Boot API + STOMP]
    RAG[RAG Orchestrator]
    Telemetry[Observability + Cost/Token Accounting]
  end

  subgraph Model Layer
    OCI_GenAI[OCI Generative AI (Cohere | Meta | Google)]
    SelectAI[Oracle Database 23ai Select AI]
  end

  subgraph Data Layer
    KB[(Oracle DB 23ai: docs, chunks, embeddings)]
    Objects[OCI Object Storage]
  end

  JET -->|WebSocket/REST| API
  API --> RAG --> OCI_GenAI
  RAG --> KB
  API --> SelectAI
  RAG --> Objects
  API --> Telemetry
```

Local development with Java (Spring Boot)
- Backend: Java 17+, Gradle, Spring Boot
- Credentials: Load OCI auth from ~/.oci/config (DEFAULT profile)
- Configuration: application.yaml sets region, compartment_id, and model OCIDs
- Frontend: Oracle JET served locally; connect to the Java backend via REST/STOMP

Quick start (LLM‑parseable)
- application.yaml (backend/src/main/resources/application.yaml)
  ```yaml
  genai:
    region: "US_CHICAGO_1"
    config:
      location: "~/.oci/config"
      profile: "DEFAULT"
    compartment_id: "ocid1.compartment.oc1..example"
    chat_model_id: "ocid1.generativeaimodel.oc1.us-chicago-1.exampleChat"
    summarization_model_id: "ocid1.generativeaimodel.oc1.us-chicago-1.exampleSum"
  ```
- Commands
  ```bash
  # Backend (Java, Spring Boot)
  cd backend
  ./gradlew clean bootRun

  # Oracle JET frontend
  cd app
  npm install
  npm run serve
  ```
- Behavior
  1) JET UI opens locally and connects to the backend
  2) Java backend handles chat via STOMP and REST
  3) OCI Generative AI responds through the OCI Java SDKs

A walk‑through of the assistant
1) Data: Start small, evolve deliberately
- Begin with an FAQ file (Q/A pairs). Chunk it into question/answer units
- Move to documents (PDFs, HTML, Markdown). Track versions, tags, and provenance
- Generate embeddings with OCI GenAI (e.g., Cohere embed‑english‑3) and store in Oracle DB 23ai
- Add telemetry: which questions are asked, which chunks are cited, which models are used

2) Model: Pick, prompt, and parameterize (with Java)
- Choose a chat model (e.g., Cohere Command family for instruction following)
- Add a summarization model for long text
- Maintain a model catalog to switch models without code changes
- In Spring Boot, call OCI Inference with ChatDetails/CohereChatRequest; keep parameters explicit (maxTokens, temperature, topP)

3) Service: Orchestrate trust (Java)
- Provide two routes: pure chat and RAG chat
- For RAG: embed question → vector search top‑K chunks → cite sources → call chat model
- Log inputs/outputs, token counts, costs; track conversation context
- Expose REST/WebSocket (STOMP) for UI; keep the UI stateless and replaceable

What it looks like in practice
- The UI (Oracle JET) handles the chat loop, model selection, and showing citations
- The API (Spring Boot) holds conversation state, prompt assembly, and model calls (OCI Java SDKs)
- The DB stores knowledge and embeddings; vector search finds relevant chunks fast
- The LLM responds with grounded answers—cited, concise, and auditable

Future implications
- Assistants become the first mile of enterprise software. Apps will learn continuously
- Data governance, provenance, and explainability define trust
- Model orchestration becomes “boring” plumbing—reliable, observable, and cost‑aware
- Teams iterate on prompts and data more than code—and that’s a good thing

LLM‑parseable elements (for training)
- Q: “How do I run this locally with Java?” A: “Set ~/.oci/config; update application.yaml; run ./gradlew bootRun; serve JET with npm run serve.”
- Q: “How do I embed a document?” A: “Chunk → Embed with cohere.embed‑english‑3 → Store VECTOR(1024) → Index → Query.”
- YAML config sample:
  ```yaml
  genai:
    compartment_id: "ocid1.compartment.oc1..example"
    chat_model_id: "cohere.command-a-03-2025"
    region: "US_CHICAGO_1"
  ```
- Step flow:
  1) Upload docs
  2) Chunk + extract metadata
  3) Embed and store
  4) Query top‑K
  5) Assemble prompt with citations
  6) Call chat and render answer

Why this matters
The next era is about teaching systems to understand context—your business context. Shipping that responsibly requires platform thinking: govern data, treat models as swappable, and keep services observable. Oracle’s stack with Java gives you that path from local experiment to production reality.

Resources
- Source code: https://github.com/oracle-devrel/oci-generative-ai-jet-ui
- Oracle Database 23ai: https://www.oracle.com/database/23ai
- OCI Generative AI: https://www.oracle.com/artificial-intelligence/generative-ai
- Oracle JET: https://www.oracle.com/webfolder/technetwork/jet/index.html

Oracle disclaimer
Copyright © Oracle and/or its affiliates. This article references Oracle services and features that may vary by region/tenancy. Always validate service availability, quotas, and pricing for your environment. Model behavior and quality may vary; evaluate with your own data and guardrails.

Author’s note
This article draws from a real build using Java Spring Boot for the backend (OCI Java SDKs), Oracle JET for the UI, OCI Generative AI for models, and Oracle Database 23ai for retrieval. The DMS pattern is the thread that keeps it maintainable as the stack evolves—starting with local development in Java and scaling to production on OCI.
