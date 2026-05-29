# Part 7 Observability Tool Comparison

## Recommendation

Use **Jaeger all-in-one as the Part 7 v1 trace backend**, with direct OTLP export from the notebook to Jaeger on ports `4317` or `4318`.

That is the most reliable fit for this workshop because Part 7 is primarily about teaching what an agent trace is. The student needs to see one turn of the existing memory-aware agent as a span tree: context build, Oracle memory reads, tool lookup, Tavily execution, LLM calls, context checks, summarisation, and memory writes. Jaeger gives us that with one extra container, one UI port, no account, no API key, and a clear OpenTelemetry path.

The best runner-up is **Arize Phoenix**. Phoenix is the strongest AI-native choice: it is built for LLM tracing, has Phoenix/OpenInference concepts that map well to agent work, and has a useful path toward evaluation. But for this workshop, Phoenix adds more product-specific vocabulary before the learner has seen the OpenTelemetry basics. It is better as an optional follow-on or as the selected backend if human review prioritizes LLM-specific UI over the smallest reliable lab.

Do **not** select SigNoz, Langfuse, or OpenLIT for the first implementation unless the scope changes. They are good tools, but they are more platform-shaped than this lab needs.

## Research Method

This comparison uses:

- The local requirement in `MARK.md`
- The existing Part 1-6 workshop docs and notebooks
- The local Oracle Database Skills guidance for container/tooling decisions
- A required run of the `/home/mark/evangelist-crew` tutorial pipeline using the OCA provider, with output kept in this workshop under `output/tutorial_runs/observability_part_7_research`
- Current official documentation checks for SigNoz, Phoenix, OpenLIT, Langfuse, OpenTelemetry, and Jaeger

Pipeline note: the tutorial flow produced useful research artifacts under `output/tutorial_runs/observability_part_7_research/research/`, but the flow failed before planning because one saved research artifact did not pass its guardrail after a tool-call retry. I used the successful generated context, audience, and landscape briefs as research input, then hand-curated this report.

## Selection Criteria

The backend should optimize for this workshop, not for general production observability.

Scoring scale:

- `5`: excellent fit
- `3`: workable with tradeoffs
- `1`: poor fit for this lab

| Option | OpenTelemetry fit | Compose/Codespaces fit | Agent trace teaching value | LLM-specific value | Privacy control | Overall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Jaeger all-in-one | 5 | 5 | 4 | 2 | 5 | 21 |
| Arize Phoenix | 4 | 4 | 5 | 5 | 4 | 22 |
| SigNoz | 5 | 2 | 4 | 4 | 4 | 19 |
| OpenLIT | 5 | 3 | 3 | 5 | 3 | 19 |
| Langfuse | 4 | 2 | 4 | 5 | 4 | 19 |

Phoenix edges out Jaeger on raw score because it has stronger LLM-native affordances. Jaeger is still the recommendation because Codespaces reliability and low cognitive overhead matter more for Part 7 v1 than richer product features.

## Candidate Notes

### Jaeger All-In-One

Jaeger is the best **teaching backend** for this lab.

Why it fits:

- One container can provide the trace collector and UI.
- Current Jaeger docs show the all-in-one container exposing `16686` for the UI and `4317`/`4318` for OTLP.
- It uses transient in-memory trace storage, which is fine for a workshop.
- It avoids accounts, ingestion keys, product-specific SDKs, and extra databases.
- It makes manual spans easy to explain: one agent turn becomes one trace.

Tradeoffs:

- No LLM-specific views.
- No prompt/version/evaluation workflow.
- Trace interpretation depends on good span names and attributes.

Best Part 7 use:

- Add a Docker Compose `observability` profile with a `jaeger` service.
- Add notebook cells that configure OpenTelemetry and send a first test span.
- Wrap the existing agent flow with manual spans, keeping `call_agent()` unchanged.
- Teach privacy by recording lengths, counts, model names, tool names, memory types, and status, not full prompts or retrieved documents.

### Arize Phoenix

Phoenix is the best **AI-native runner-up**.

Why it fits:

- Phoenix docs separate Phoenix from Arize AX and describe Phoenix tracing setup with `phoenix.otel`.
- Phoenix has tracing, sessions, projects, evaluation, datasets, and prompts in the product surface.
- It is well aligned with OpenInference and LangChain-style instrumentation.
- It gives a future path to evaluation without choosing an evaluation-first lab today.

Tradeoffs:

- The lab would need to explain Phoenix/OpenInference concepts in addition to OpenTelemetry.
- It is easier for the tutorial to drift from observability into evaluation.
- We should verify the exact Docker Compose or local service path before choosing it.

Best Part 7 use if selected:

- Use Phoenix only for tracing in v1.
- Mention evaluation as a future extension, not a required task.
- Keep manual spans for Oracle memory operations even if OpenInference instruments LangChain calls.

### SigNoz

SigNoz is a strong observability platform, but it is likely too heavy for this workshop.

Why it fits:

- SigNoz has explicit LLM observability docs.
- Its docs list many LLM integrations, including LangChain/LangGraph, CrewAI, OpenLIT, OpenAI, and OpenLLMetry.
- The LangChain/LangGraph guide uses OpenTelemetry and OpenInference, and supports self-hosted SigNoz with endpoint changes.
- It would be useful if the lab wanted traces, metrics, logs, dashboards, and alerting.

Tradeoffs:

- Self-hosted SigNoz is a platform stack, not a tiny trace viewer.
- Running it beside Oracle Database in Codespaces may be brittle.
- It introduces dashboard/APM concepts that are not needed for the Part 7 teaching goal.

Best use:

- Mention as a production-grade OpenTelemetry platform option.
- Do not make it the default backend unless human review prioritizes full-stack observability over workshop simplicity.

### OpenLIT

OpenLIT is attractive as an AI observability platform and instrumentation layer.

Why it fits:

- OpenLIT positions itself as an open-source AI engineering platform.
- Its docs describe OpenTelemetry-native SDKs for automatic instrumentation of LLMs, agents, frameworks, vector databases, MCP, and GPUs.
- It includes tracing, evaluations, prompts, experiments, dashboards, and cost/model features.
- It can view telemetry from OpenTelemetry-instrumented tools and LLM instrumentation frameworks.

Tradeoffs:

- It may hide the learning path if introduced before students understand spans.
- It has more product surface than Part 7 needs.
- We need a live validation pass to decide whether its self-hosted path is lighter than Jaeger or Phoenix.

Best use:

- Consider it an optional advanced extension after manual OpenTelemetry spans.
- Do not select it as the v1 backend unless human review wants automatic LLM instrumentation as the central lesson.

### Langfuse

Langfuse is a strong LLM observability product, but its shape is broader than this lab.

Why it fits:

- Langfuse can receive OpenTelemetry traces on its `/api/public/otel` OTLP endpoint.
- Its docs explicitly discuss GenAI semantic conventions evolving and mapping OTel traces into the Langfuse data model.
- It supports traces, prompt management, evaluations, datasets, sessions, metadata, and LLM workflow concepts.

Tradeoffs:

- Its docs recommend Langfuse SDKs for Python/JS when possible, which pulls the lab toward product-specific instrumentation.
- Its self-hosting footprint is likely more than a beginner Part 7 needs.
- Langfuse concepts such as sessions, metadata propagation, prompt management, and evaluations may compete with the simpler OpenTelemetry lesson.

Best use:

- Mention as a good LLM observability platform for teams that want prompt/evaluation workflows.
- Do not select it for the first workshop implementation.

## OpenTelemetry Notes

Use **manual instrumentation first**.

The existing notebook already has a clear agent loop. Manual spans make that architecture visible:

- `agent.run`
- `agent.context.build`
- `agent.memory.read`
- `agent.toolbox.read`
- `agent.llm.call`
- `agent.tool.execute`
- `agent.context.check`
- `agent.context.summarise`
- `agent.memory.write`

Use stable, conservative attributes:

- `service.name`
- `workshop.part`
- `agent.thread_id`
- `agent.mode`
- `llm.model`
- `query.length`
- `response.length`
- `context.estimated_tokens`
- `memory.type`
- `memory.result_count`
- `tool.name`
- `tool.result_length`
- `error.type`

Do not depend on OpenTelemetry GenAI semantic convention names as hard lab invariants. The conventions are useful context, but they are still changing. Keep the lab correct even if GenAI attribute names evolve.

## Privacy Defaults

Part 7 should default to safe telemetry:

- Do not capture full prompts.
- Do not capture full responses.
- Do not capture retrieved documents.
- Do not capture raw Tavily output.
- Do not capture API keys, database passwords, DSNs with credentials, or environment values.
- Do capture lengths, counts, status, model names, memory types, selected tool names, and errors.

If the notebook includes a prompt/response capture toggle, make it clearly opt-in and label it as unsafe for shared environments.

## Proposed Human Decision

Approve one of these:

- **Recommended:** Jaeger all-in-one for Part 7 v1.
- **Alternative:** Phoenix if the lab should emphasize LLM-native trace views and future evaluation.
- **Heavier alternative:** SigNoz if the lab should feel like production OpenTelemetry/APM.

After review, the implementation should add only the selected backend to Docker Compose and then append Part 7 to the docs and notebooks.

## Sources

- SigNoz LLM observability overview: https://signoz.io/docs/llm-observability/
- SigNoz LangChain/LangGraph observability: https://signoz.io/docs/langchain-observability/
- Arize Phoenix tracing setup: https://arize.com/docs/phoenix/tracing/how-to-tracing/setup-tracing
- OpenLIT overview: https://docs.openlit.io/
- Langfuse OpenTelemetry integration: https://langfuse.com/docs/opentelemetry
- OpenTelemetry Python exporters: https://opentelemetry.io/docs/languages/python/exporters/
- OpenTelemetry Collector: https://opentelemetry.io/docs/collector/
- OpenTelemetry GenAI semantic conventions: https://opentelemetry.io/docs/specs/semconv/gen-ai/
- Jaeger getting started: https://www.jaegertracing.io/docs/latest/getting-started/
