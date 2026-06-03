# Part 7 Observability Tool Comparison

## Recommendation

Use **LangSmith as the Part 7 trace backend**.

This workshop now traces the existing memory-aware agent with LangSmith manual runs. That is the best fit for the requested revision because Part 7 is focused on AI agent observability, and LangSmith provides a purpose-built trace view for agent steps, LLM calls, tool calls, and metadata without adding a local trace container or collector to the workshop.

The tradeoff is that LangSmith requires a hosted account and API key. For this lab, that is acceptable because it removes the local observability service and gives learners an AI-native trace UI. Oracle AI Database remains the durable memory and vector search system of record; LangSmith only shows what happened during execution.

## Selection Criteria

The backend should optimize for this workshop, not for general production observability.

Scoring scale:

- `5`: excellent fit
- `3`: workable with tradeoffs
- `1`: poor fit for this lab

| Option | AI agent fit | Setup burden | Trace teaching value | Local service burden | Privacy control | Overall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| LangSmith | 5 | 4 | 5 | 5 | 4 | 24 |
| Arize Phoenix | 5 | 3 | 5 | 3 | 4 | 20 |
| Langfuse | 5 | 2 | 4 | 2 | 4 | 18 |
| SigNoz | 4 | 2 | 4 | 2 | 4 | 18 |
| OpenLIT | 5 | 3 | 3 | 3 | 3 | 19 |

## Candidate Notes

### LangSmith

LangSmith is the selected backend.

Why it fits:

- It is designed for LLM and agent traces.
- It integrates naturally with LangChain-oriented workflows.
- It supports manual tracing, so the lab can show the exact Part 6 agent architecture instead of hiding it behind automatic instrumentation.
- It avoids running a local trace container beside Oracle Database in Codespaces.
- It gives learners a clear project-based UI for inspecting `agent.run` and child runs.

Tradeoffs:

- It requires a LangSmith API key.
- It sends trace metadata to the LangSmith service.
- The lab must be explicit about privacy and avoid recording full prompts, retrieved documents, API keys, raw Tavily output, or database connection strings.

Best Part 7 use:

- Set `LANGSMITH_TRACING=true`, `LANGSMITH_PROJECT=agent-memory-workshop`, and `LANGSMITH_API_KEY`.
- Use manual LangSmith trace runs for `agent.run`, memory reads, tool selection, LLM calls, tool execution, context checks, and memory writes.
- Record lengths, counts, model names, tool names, memory types, and status only.

### Arize Phoenix

Phoenix remains a strong AI-native alternative if the workshop needs local-first tracing plus evaluation.

Why it fits:

- Phoenix has LLM tracing, sessions, projects, evaluation, datasets, and prompts in the product surface.
- It aligns well with OpenInference and LangChain-style instrumentation.
- It gives a future path to evaluation workflows.

Tradeoffs:

- It would require explaining Phoenix/OpenInference concepts in addition to agent memory concepts.
- The local service path adds more setup than LangSmith for this requested revision.

### Langfuse

Langfuse is a strong LLM observability product, but its self-hosted path is broader than this lab needs.

Why it fits:

- It supports LLM traces, prompt management, evaluations, datasets, sessions, and metadata.
- It can support OpenTelemetry-oriented workflows.

Tradeoffs:

- Its self-hosted footprint is likely heavier than this workshop needs.
- Its product surface may distract from the narrower Part 7 goal: inspect one memory-aware agent run.

### SigNoz

SigNoz is a strong observability platform, but it is platform-shaped rather than agent-workshop-shaped.

Why it fits:

- It is credible for traces, metrics, logs, dashboards, and production observability.
- It has LLM observability documentation and integrations.

Tradeoffs:

- The local stack is more than the workshop needs.
- It introduces APM concepts that are not required for this lab.

### OpenLIT

OpenLIT is attractive as an AI observability and automatic instrumentation layer.

Why it fits:

- It focuses on OpenTelemetry-native AI instrumentation.
- It can instrument LLMs, agents, frameworks, vector databases, MCP, and GPUs.

Tradeoffs:

- Automatic instrumentation can obscure the manual span/run structure learners need to understand first.
- It has more product surface than Part 7 needs.

## Privacy Defaults

Part 7 should default to safe telemetry:

- Do not capture full prompts.
- Do not capture full responses.
- Do not capture retrieved documents.
- Do not capture raw Tavily output.
- Do not capture API keys, database passwords, DSNs with credentials, or environment values.
- Do capture lengths, counts, status, model names, memory types, selected tool names, and errors.

If the notebook includes a prompt/response capture toggle, make it clearly opt-in and label it as unsafe for shared environments.

## Sources

- LangSmith tracing with LangChain: https://docs.smith.langchain.com/observability/how_to_guides/trace_with_langchain
- LangSmith manual instrumentation: https://docs.langchain.com/langsmith/annotate-code
- Arize Phoenix tracing setup: https://arize.com/docs/phoenix/tracing/how-to-tracing/setup-tracing
- OpenLIT overview: https://docs.openlit.io/
- Langfuse OpenTelemetry integration: https://langfuse.com/docs/opentelemetry
- SigNoz LLM observability overview: https://signoz.io/docs/llm-observability/
