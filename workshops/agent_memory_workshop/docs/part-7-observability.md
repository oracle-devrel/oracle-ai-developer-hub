# Part 7: Agent Observability

## Three TODOs in This Part

Part 7 adds OpenTelemetry tracing to the agent you built in Part 6. You will keep the original `call_agent()` function unchanged and create an observed wrapper that sends traces to Jaeger.

Before running the Part 7 notebook cells, start Jaeger:

```bash
docker compose -f .devcontainer/docker-compose.yml --profile observability up -d jaeger
```

Open the Jaeger UI from the forwarded **Jaeger UI** port, or go to:

```text
http://localhost:16686
```

---

## TODO 17: Configure OpenTelemetry

OpenTelemetry has three moving parts in this lab:

- **Tracer provider** — creates tracers for your Python process
- **Exporter** — sends spans out of the notebook
- **Backend** — receives and displays the trace; here, Jaeger

**Complete solution:**

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

def configure_agent_observability(
    service_name: str = "agent-memory-workshop",
    endpoint: str = "http://localhost:4318/v1/traces",
):
    resource = Resource.create({
        "service.name": service_name,
        "workshop.part": "7",
        "workshop.topic": "agent-observability",
    })
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)
    return trace.get_tracer("agent-memory-workshop.part7")

tracer = configure_agent_observability()
```

**Why the endpoint includes `/v1/traces`:** The notebook uses the OTLP HTTP exporter. Jaeger receives OTLP HTTP on port `4318`, and trace export uses the `/v1/traces` path.

**Privacy default:** This lab records metadata, not content. Trace attributes should include lengths, counts, model names, tool names, memory types, and error status — not full prompts, retrieved documents, API keys, or raw tool output.

---

## TODO 18: `call_agent_observed()`

The original `call_agent()` remains your working agent harness. In Part 7, you create a second function, `call_agent_observed()`, that follows the same flow but wraps each major operation in spans.

**Span shape:**

```text
agent.run
├── agent.context.build
│   ├── agent.memory.read conversational
│   ├── agent.memory.read knowledge_base
│   ├── agent.memory.read workflow
│   ├── agent.memory.read entity
│   └── agent.memory.read summary
├── agent.context.check
├── agent.toolbox.read
├── agent.memory.write user_message
├── agent.llm.call
├── agent.tool.execute
├── agent.tool.log
├── agent.memory.write workflow
├── agent.memory.write entity
└── agent.memory.write assistant_message
```

**Important attributes to record:**

| Attribute | Example | Why it is safe |
|---|---|---|
| `agent.thread_id` | `0022` | Identifier, not content |
| `query.length` | `74` | Length only |
| `context.estimated_tokens` | `1320` | Count only |
| `memory.type` | `knowledge_base` | Category only |
| `memory.result_length` | `540` | Length only |
| `tool.name` | `search_tavily` | Tool name only |
| `tool.result_length` | `1800` | Length only |
| `llm.model` | `xai.grok-3-fast` | Model name only |

**Why manual spans first:** Automatic LLM instrumentation is useful, but it can hide the architecture. Manual spans show exactly how your Part 6 harness works. Once you understand that trace, automatic instrumentation is easier to reason about.

---

## TODO 19: Run and Inspect the Trace

Run a short observed conversation using a fresh thread ID:

```python
observed_thread = "observed-0022"

for q in [
    "Find papers about memory in AI agents",
    "What did we just discuss?",
    "Search the web for recent agent observability ideas",
]:
    call_agent_observed(q, thread_id=observed_thread, max_iterations=5)
```

Then open Jaeger:

1. Select service `agent-memory-workshop`
2. Click **Find Traces**
3. Open the most recent `agent.run` trace
4. Expand the child spans

You should see where the agent spent time and which operations happened during the turn.

## What to Look For

**Context build spans:** These show which memory systems were read before the LLM call.

**Tool spans:** These show whether the model called Tavily or summary tools.

**Context check spans:** These show estimated context window size without exposing the full prompt.

**Memory write spans:** These show the durable writes that make the next turn memory-aware.

## Key Takeaways

**Observability makes agent behavior inspectable.** The Part 6 chart shows that the memory-aware agent controls context growth. Part 7 shows the operational path behind that chart.

**The trace is not the memory store.** Oracle AI Database still stores the agent's memory. Jaeger only shows what happened during execution.

**Safe traces are designed.** A useful trace does not need full prompts or raw tool results. In most labs and production systems, counts, names, durations, statuses, and sanitized IDs are enough to debug the flow.
