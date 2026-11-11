# Architecture

The browser never receives database or model credentials. It calls a narrow API whose application services enforce user scope before reaching Mem0.

```mermaid
flowchart LR
    UI[React workspace] -->|JSON /api| API[Hono API]
    API --> CHAT[Chat service]
    API --> MEMORY[Memory service]
    CHAT -->|retrieve; ingest in OpenAI mode| MEM0[Mem0 OSS]
    MEMORY --> MEM0
    CHAT -->|optional Responses API| OPENAI[OpenAI]
    MEM0 -->|optional embeddings + inference| OPENAI
    MEM0 -->|default deterministic embeddings| DEMO[Local TypeScript embedder]
    MEM0 -->|native oracledb vector store| ORACLE[(Oracle Database)]
    API -->|read-only metadata| ORACLE
```

## Chat sequence

```mermaid
sequenceDiagram
    participant U as Browser
    participant A as API
    participant M as Mem0
    participant E as Embedder (demo or OpenAI)
    participant O as OpenAI (optional)
    participant D as Oracle
    U->>A: POST /api/chat {userId, message}
    A->>M: search(message, user_id filter)
    M->>E: embed query
    M->>D: cosine vector search
    D-->>M: scoped memories
    M-->>A: retrieved evidence
    alt no-key demo
      A-->>U: extractive answer + retrieved evidence
    else OpenAI mode
      A->>O: Responses API with relevant memory context
      O-->>A: answer
      A->>M: add full conversation turn with inference
      M->>D: persist inferred memories and vectors
    end
    A-->>U: answer + retrieval + memory events
```

## Boundaries

- `packages/shared` is the wire-contract authority.
- `packages/core` contains provider-neutral services plus the Mem0/OpenAI adapters.
- `packages/db` owns direct Oracle diagnostics and destructive-operation guards.
- `services/api` translates HTTP input into service calls and hides internal errors.
- `apps/web` consumes only the public API contract.

Mem0 history is disabled because this sample uses Oracle as its demonstrated persistence layer. The required `better-sqlite3` package remains installed because Mem0 3.3.1 imports it statically even when history is disabled.
