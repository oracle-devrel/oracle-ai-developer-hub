# Agent-Reasoning Integration Design

**Date:** 2026-01-21
**Status:** Approved
**Scope:** Integrate agent-reasoning capabilities into agentic_rag with ensemble voting, unified chat UI, A2A support, and database logging.

---

## 1. Overview

This design integrates the [agent-reasoning](https://github.com/your-username/agent-reasoning) library into agentic_rag, replacing the existing multi-agent CoT system (Planner, Researcher, Reasoner, Synthesizer) with 10 research-backed reasoning strategies that can run in parallel with ensemble voting.

### Goals

- Integrate all 10 reasoning strategies from agent-reasoning
- Enable ensemble voting with majority selection
- Provide unified chat UI with RAG toggle and strategy selection
- Expose reasoning via A2A protocol with discoverable agent cards
- Log all reasoning events to Oracle DB

### Non-Goals

- Changing the underlying Ollama/LLM infrastructure
- Modifying the vector store implementation
- Breaking existing API endpoints

---

## 2. Architecture

### High-Level Flow

```
User Query → Gradio UI → RAGReasoningEnsemble
                              ↓
                    [RAG retrieval if enabled]
                              ↓
                    agent_reasoning.ensemble.run()
                              ↓
                    [Parallel strategy execution]
                              ↓
                    [Majority voting via semantic similarity]
                              ↓
                    [Log to REASONING_EVENTS]
                              ↓
                    Response + execution trace → UI
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  PyPI: agent-reasoning                                          │
│  ─────────────────────────────────────────────────────────────  │
│  Standalone reasoning library - works independently             │
│                                                                 │
│  from agent_reasoning import ReasoningInterceptor               │
│  from agent_reasoning.agents import CoTAgent, ToTAgent, ...     │
│  from agent_reasoning.ensemble import ReasoningEnsemble         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ pip install agent-reasoning
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  agentic_rag (oracle-ai-developer-hub)                          │
│  ─────────────────────────────────────────────────────────────  │
│  Imports and extends agent-reasoning for RAG integration        │
│                                                                 │
│  src/reasoning/rag_ensemble.py → RAGReasoningEnsemble           │
│  src/reasoning_agent_cards.py  → A2A agent cards                │
│  gradio_app.py                 → Unified chat UI                │
│  src/a2a_handler.py            → A2A reasoning methods          │
│  src/OraDBEventLogger.py       → REASONING_EVENTS table         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Reasoning Strategies

All 10 strategies from agent-reasoning will be available:

| Strategy | Agent ID | Description | Best For | Research |
|----------|----------|-------------|----------|----------|
| Standard | `reasoning_standard_v1` | Direct LLM generation (baseline) | Simple queries | N/A |
| CoT | `reasoning_cot_v1` | Step-by-step reasoning | Math, logic, explanations | Wei et al. (2022) |
| ToT | `reasoning_tot_v1` | Tree exploration with BFS | Complex riddles, strategy | Yao et al. (2023) |
| ReAct | `reasoning_react_v1` | Reason + Act with tools | Fact-checking, calculations | Yao et al. (2022) |
| Self-Reflection | `reasoning_self_reflection_v1` | Draft → Critique → Refine | Creative writing, accuracy | Shinn et al. (2023) |
| Consistency | `reasoning_consistency_v1` | Multi-sample voting | Diverse problems | Wang et al. (2022) |
| Decomposed | `reasoning_decomposed_v1` | Problem decomposition | Planning, long-form | Khot et al. (2022) |
| Least-to-Most | `reasoning_least_to_most_v1` | Simple to complex | Complex reasoning | Zhou et al. (2022) |
| Recursive | `reasoning_recursive_v1` | Recursive processing | Long context | Author et al. (2025) |

Plus one orchestrator:
- `reasoning_ensemble_v1` - Executes multiple strategies with voting

---

## 4. Ensemble Voting Mechanism

### Algorithm

1. **Single strategy selected** → Return response directly (no voting overhead)
2. **Multiple strategies selected** → Run in parallel, then vote

### Majority Voting Implementation

```python
def _majority_vote(self, responses: list[dict]) -> dict:
    # 1. Generate embeddings for each response
    embeddings = self._get_embeddings([r["response"] for r in responses])

    # 2. Cluster by cosine similarity (threshold: 0.85)
    clusters = self._cluster_by_similarity(embeddings, threshold=0.85)

    # 3. Find largest cluster
    largest_cluster = max(clusters, key=len)

    # 4. Return first response from largest cluster
    winner_idx = largest_cluster[0]

    return {
        "response": responses[winner_idx]["response"],
        "strategy": responses[winner_idx]["strategy"],
        "vote_count": len(largest_cluster),
        "total_responses": len(responses),
    }
```

### Edge Cases

- **Tie (equal cluster sizes)** → Pick cluster containing CoT response (most reliable baseline)
- **All responses unique** → Return CoT response as fallback

---

## 5. Unified Chat UI

### Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  UNIFIED CHAT                                                       │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Settings Bar                                                 │   │
│  │ [Model: ▼] [✓ RAG Enabled] [Collection: ▼]                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Reasoning Strategies (multi-select)                          │   │
│  │ [✓] CoT  [✓] ToT  [ ] ReAct  [ ] Self-Reflection            │   │
│  │ [ ] Consistency  [ ] Decomposed  [ ] Least-to-Most          │   │
│  │ [ ] Recursive  [ ] Standard                                  │   │
│  │                                                              │   │
│  │ [Advanced ▼]  ← per-strategy config (depth, samples, etc.)  │   │
│  └─────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│  USER: How does gradient descent work?                              │
├─────────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ 🔄 EXECUTION TRACE                                  [Collapse] │ │
│  ├───────────────────────────────────────────────────────────────┤ │
│  │ 09:41:02 │ 🚀 Starting ensemble with 3 strategies             │ │
│  │ 09:41:02 │ 📚 RAG: Retrieving context from PDF Collection...  │ │
│  │ 09:41:03 │ 📚 RAG: Found 4 relevant chunks (score: 0.89)      │ │
│  │ 09:41:03 │ ⚡ Launching strategies in parallel...              │ │
│  │ 09:41:05 │ ✅ CoT: Complete (1.8s)                            │ │
│  │ 09:41:06 │ ✅ Consistency: Complete (2.4s)                    │ │
│  │ 09:41:08 │ ✅ ToT: Complete (4.2s)                            │ │
│  │ 09:41:08 │ 🗳️ Voting: Clustering 3 responses...               │ │
│  │ 09:41:08 │ 🏆 Winner: CoT (similarity cluster: 2/3 votes)     │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ 📊 STRATEGY RESPONSES                               [Collapse] │ │
│  ├───────────────────────────────────────────────────────────────┤ │
│  │ ┌─────────────────────────────────────────────────────────┐   │ │
│  │ │ 🏆 CoT (Winner - 2/3 votes)                    ⏱️ 1.8s  │   │ │
│  │ │ Gradient descent is an optimization algorithm...        │   │ │
│  │ │ [Show full response ▼]                                  │   │ │
│  │ └─────────────────────────────────────────────────────────┘   │ │
│  │ ┌─────────────────────────────────────────────────────────┐   │ │
│  │ │ 🌳 ToT                                          ⏱️ 4.2s │   │ │
│  │ │ Let me explore multiple reasoning paths...              │   │ │
│  │ │ [Show full response ▼]                                  │   │ │
│  │ └─────────────────────────────────────────────────────────┘   │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ 💬 FINAL ANSWER                                               │ │
│  │ Gradient descent is an optimization algorithm...              │ │
│  │ 📚 Sources: ml_fundamentals.pdf (p.23, p.45)                 │ │
│  └───────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│  [Type your message...                                    ] [Send] │
└─────────────────────────────────────────────────────────────────────┘
```

### UI Features

- **Settings Bar**: Model selection, RAG toggle, collection picker
- **Strategy Selector**: Multi-select checkboxes with Advanced panel
- **Execution Trace**: Real-time log stream (collapsible)
- **Strategy Responses**: Individual cards for each strategy output (collapsible)
- **Final Answer**: Winning response with sources

---

## 6. A2A Protocol Integration

### New Methods

| Method | Description |
|--------|-------------|
| `reasoning.execute` | Run ensemble with multiple strategies |
| `reasoning.strategy` | Run single strategy |
| `reasoning.list` | List available strategies |

### Request Example

```json
{
  "jsonrpc": "2.0",
  "method": "reasoning.execute",
  "params": {
    "query": "How does gradient descent work?",
    "strategies": ["cot", "tot", "consistency"],
    "use_rag": true,
    "collection": "PDF",
    "config": {
      "tot_depth": 3,
      "consistency_samples": 3
    }
  },
  "id": "1"
}
```

### Response Example

```json
{
  "jsonrpc": "2.0",
  "result": {
    "winner": {
      "strategy": "cot",
      "response": "Gradient descent is...",
      "vote_count": 2
    },
    "all_responses": [
      {"strategy": "cot", "response": "...", "duration_ms": 1800},
      {"strategy": "tot", "response": "...", "duration_ms": 4200},
      {"strategy": "consistency", "response": "...", "duration_ms": 2400}
    ],
    "rag_context": {
      "chunks_used": 4,
      "sources": ["ml_fundamentals.pdf"]
    },
    "total_duration_ms": 4500
  },
  "id": "1"
}
```

### Agent Discovery

```bash
# Discover all reasoning strategy agents
curl -X POST http://localhost:8000/a2a \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "agent.discover", "params": {"capability": "reasoning.strategy"}, "id": "1"}'

# Discover ensemble orchestrator
curl -X POST http://localhost:8000/a2a \
  -d '{"jsonrpc": "2.0", "method": "agent.discover", "params": {"capability": "reasoning.execute"}, "id": "2"}'
```

---

## 7. Database Logging

### New Table: REASONING_EVENTS

```sql
CREATE TABLE IF NOT EXISTS REASONING_EVENTS (
    event_id VARCHAR2(100) PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    query_text CLOB,

    -- Ensemble info
    strategies_requested CLOB,          -- JSON array
    strategies_completed CLOB,          -- JSON array with status

    -- Voting results
    winner_strategy VARCHAR2(50),
    winner_response CLOB,
    vote_count NUMBER,
    total_strategies NUMBER,
    similarity_threshold NUMBER,

    -- All responses
    all_responses CLOB,                 -- JSON

    -- RAG integration
    rag_enabled NUMBER(1),
    collection_used VARCHAR2(200),
    chunks_retrieved NUMBER,

    -- Performance
    total_duration_ms NUMBER,
    parallel_execution NUMBER(1),

    -- Config
    config_json CLOB,

    -- Status
    status VARCHAR2(50),
    error_message CLOB
)
```

### Logging Method

```python
def log_reasoning_event(
    self,
    query_text: str,
    strategies_requested: list[str],
    winner_strategy: str,
    winner_response: str,
    vote_count: int,
    all_responses: list[dict],
    rag_enabled: bool = False,
    collection_used: str = None,
    chunks_retrieved: int = 0,
    total_duration_ms: float = None,
    config: dict = None,
    status: str = "success",
    error_message: str = None
) -> str:
    """Log a reasoning ensemble execution event"""
```

---

## 8. Package Changes

### agent-reasoning (PyPI)

**New/modified files:**

| File | Changes |
|------|---------|
| `pyproject.toml` | Configure for PyPI publishing |
| `src/agent_reasoning/__init__.py` | Public exports |
| `src/agent_reasoning/ensemble.py` | **NEW** - ReasoningEnsemble + voting |
| `src/agent_reasoning/agents/__init__.py` | Export all agents |

**Package structure:**

```
agent-reasoning/
├── pyproject.toml
├── README.md
├── src/
│   └── agent_reasoning/
│       ├── __init__.py
│       ├── client.py
│       ├── interceptor.py
│       ├── ensemble.py          # NEW
│       └── agents/
│           ├── __init__.py
│           ├── base.py
│           ├── cot.py
│           ├── tot.py
│           ├── react.py
│           ├── self_reflection.py
│           ├── consistency.py
│           ├── decomposed.py
│           ├── least_to_most.py
│           ├── recursive.py
│           └── standard.py
```

### agentic_rag

**New files:**

| File | Purpose |
|------|---------|
| `src/reasoning/__init__.py` | Package init |
| `src/reasoning/rag_ensemble.py` | RAGReasoningEnsemble wrapper |
| `src/reasoning_agent_cards.py` | Agent cards for A2A |

**Modified files:**

| File | Changes |
|------|---------|
| `gradio_app.py` | Unified chat UI with execution trace |
| `src/a2a_handler.py` | Add reasoning A2A methods |
| `src/OraDBEventLogger.py` | Add REASONING_EVENTS table |
| `src/agent_registry.py` | Register reasoning agents |
| `src/local_rag_agent.py` | Use RAGReasoningEnsemble |
| `requirements.txt` | Add `agent-reasoning>=1.0.0` |

**Removed files:**

| File | Reason |
|------|--------|
| `src/specialized_agent_cards.py` | Replaced by reasoning_agent_cards.py |

---

## 9. Implementation Phases

### Phase 1: agent-reasoning PyPI Package
1. Restructure agent-reasoning for PyPI
2. Add ensemble.py with voting logic
3. Publish to PyPI

### Phase 2: agentic_rag Core Integration
1. Add agent-reasoning dependency
2. Create RAGReasoningEnsemble wrapper
3. Update local_rag_agent.py
4. Add REASONING_EVENTS table

### Phase 3: A2A Integration
1. Add reasoning A2A methods
2. Create reasoning agent cards
3. Register agents on startup

### Phase 4: Unified Chat UI
1. Remove old chat tabs
2. Build unified chat with settings bar
3. Add execution trace component
4. Add strategy responses panel

### Phase 5: Testing & Documentation
1. Unit tests for ensemble voting
2. Integration tests for A2A
3. Update README.md

---

## 10. Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Strategies to include | All 10 | Maximum flexibility |
| Combination method | Ensemble voting | Run strategies in parallel, aggregate results |
| Voting mechanism | Majority (semantic similarity) | Groups similar answers, picks most common |
| Single strategy behavior | Direct response | No voting overhead |
| RAG integration | After retrieval | Reasoning grounded in documents |
| Existing CoT system | Replace entirely | Avoid duplication, cleaner architecture |
| UI approach | Unified single chat | Simpler UX, all controls in one place |
| Strategy selection UI | Multi-select + Advanced | Flexible but not overwhelming |
| Package distribution | PyPI for agent-reasoning | Reusable across projects |
| agentic_rag integration | Import via pip | Clean dependency management |
