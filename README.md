# Oracle AI Developer Hub

Reference applications, notebooks, and hands-on workshops for building RAG applications, AI agents, and agent memory systems on Oracle AI Database and OCI Generative AI.

## What is this repository?

The Oracle AI Developer Hub is a catalogue of runnable examples, not an SDK or a framework. Every entry is self-contained code you can read, run, and adapt: reference applications, Jupyter notebooks, guided workshops, and conference decks.

The examples show how to build retrieval-augmented generation (RAG), AI agents, and agent memory with [Oracle AI Database](https://www.oracle.com/database/) (vector search, hybrid search, JSON Relational Duality, Select AI) and OCI Generative AI, together with frameworks such as LangChain, LangGraph, the OpenAI Agents SDK, and the Claude Agent SDK.

It is for developers and AI engineers who want working code to start from. If you are looking for a library rather than examples, see [python-oracledb](https://github.com/oracle/python-oracledb), [langchain-oracledb](https://github.com/oracle/langchain-oracle), or [Oracle AI Agent Memory](https://www.oracle.com/database/ai-agent-memory/).

## Quick start

Run vector search, hybrid search, RAG, and agent memory on a local Oracle AI Database. There is no sign-up and no API key: an ONNX model inside the database creates the embeddings.

The shortest way needs only Docker. One command builds a small Python image, starts the database, prepares it, and runs the first example. The first run downloads the database image (about 0.9 GB) and takes a few minutes.

```bash
git clone https://github.com/oracle-devrel/oracle-ai-developer-hub.git
cd oracle-ai-developer-hub/quickstart
docker compose up --attach quickstart
```

Or open the quick start in GitHub Codespaces, where the database runs next to the editor:

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/oracle-devrel/oracle-ai-developer-hub?devcontainer_path=.devcontainer%2Fquickstart%2Fdevcontainer.json)

To run the same steps in your own Python environment, you need Docker and Python 3.11 or newer:

1. Start the database. The first start downloads about 0.9 GB.

   ```bash
   export ORACLE_PWD=Quickstart2026
   docker run -d --name oracle-free -p 127.0.0.1:1521:1521 -e ORACLE_PWD=$ORACLE_PWD \
     container-registry.oracle.com/database/free:latest-lite
   ```

2. Install the packages, prepare the database, and run the first example.

   ```bash
   git clone https://github.com/oracle-devrel/oracle-ai-developer-hub.git
   cd oracle-ai-developer-hub/quickstart
   python3 -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   python setup_database.py
   python vector_and_hybrid_search.py
   ```

The example loads six sentences and searches them for "money back". The sentence about refunds comes first, although it shares no word with the query. A hybrid search then puts the sentence with an exact error code first.

A vector search with LangChain takes a few lines. Save this as `snippet.py` in the same folder and run `python snippet.py`, or `docker compose run --rm quickstart python snippet.py` if you started with Docker Compose. It prints the refund sentence.

```python
import os

import oracledb
from langchain_core.embeddings import Embeddings
from langchain_oracledb.vectorstores import DistanceStrategy, OracleVS

conn = oracledb.connect(
    user="quickstart",
    password=os.environ["ORACLE_PWD"],
    dsn=os.environ.get("ORACLE_DSN", "localhost:1521/FREEPDB1"),
)


class InDatabaseEmbeddings(Embeddings):
    """Embeds text with the ONNX model that setup_database.py loaded into the database."""

    def embed_documents(self, texts):
        sql = "select vector_embedding(ALL_MINILM_L12_V2 using :text as data) from dual"
        with conn.cursor() as cur:
            return [list(cur.execute(sql, text=text).fetchone()[0]) for text in texts]

    def embed_query(self, text):
        return self.embed_documents([text])[0]


store = OracleVS.from_texts(
    ["Premium customers can request a full refund within 30 days.", "Support is available 24/7."],
    InDatabaseEmbeddings(),
    client=conn,
    table_name="QS_SNIPPET",
    distance_strategy=DistanceStrategy.COSINE,
)
print(store.similarity_search("money back", k=1)[0].page_content)
```

The [quick start walkthrough](./quickstart/README.md) shows the expected output of every step and continues with RAG, a LangGraph agent that keeps its state in the database, and Oracle AI Agent Memory.

## Start here

| I want to                              | Start with                                                                                                                        | Then                                                                       |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Build my first RAG app                 | [Minimal RAG notebook with LangChain and Oracle AI Vector Search](./notebooks/langchain_ecosystem/oracle_langchain_example.ipynb) | [RAG reference app with in-database embeddings](./apps/oracle-rag)         |
| Build an AI agent                      | [RAG agents from zero to hero notebook](./notebooks/oracle_rag_agents_zero_to_hero.ipynb)                                         | [From RAG to Agents workshop](./workshops/from_rag_to_agents_workshop)     |
| Add persistent memory to an agent      | [Oracle AI Agent Memory developer guide notebook](./notebooks/agent_memory/oracle_agent_memory_developer_guide.ipynb)             | [Agent Memory workshop](./workshops/agent_memory_workshop)                 |
| Learn step by step                     | [Information Retrieval to RAG workshop](./workshops/information_retrieval_to_RAG)                                                 | [All workshops](./workshops/README.md)                                     |
| Have a coding agent scaffold a project | [Build Paths: beginner, intermediate, and advanced](./build-paths/README.md)                                                      | [Three worked Build Paths walk-throughs](./build-paths/GETTING_STARTED.md) |

## Contents

- [Agent Memory](#agent-memory): concepts, implementation, and complete examples
- [Apps](#apps): reference applications you can run, fork, or deploy
- [Notebooks](#notebooks): Jupyter notebooks for RAG, agents, and vector search
- [LangChain Ecosystem](#langchain-ecosystem): notebooks built on LangChain, LangGraph, and Deep Agents
- [Workshops](#workshops): guided, multi-part learning paths
- [Guides](#guides): conference decks on agent architecture and memory engineering
- [Partners](#partners): examples contributed by ecosystem partners
- [Build Paths](#build-paths): skills that let a coding agent scaffold an Oracle AI project
- [Contributing](#contributing)

## Agent Memory

Agent memory is what lets an agent recall earlier conversations, keep durable facts, and resume work across sessions. The resources below use Oracle AI Database as the single memory store, most of them through the [Oracle AI Agent Memory](https://www.oracle.com/database/ai-agent-memory/) package (`oracleagentmemory`, also called OAMP).

Follow the map from concept to implementation to a complete example:

| Step                | Resource                                                                                                                  | What it covers                                                                                          |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| 1. Concept          | [What is agent memory?](./notebooks/agent_memory/README.md)                                                               | The memory types (conversation, episodic, semantic, procedural, working, entity) and how they are used. |
| 1. Concept          | [Filesystem vs database agent memory notebook](./notebooks/fs_vs_dbs.ipynb)                                               | Why agent memory belongs in a database, shown side by side.                                             |
| 1. Concept          | [Teach Agents What To Remember deck](./guides/teach_agents_what_to_remember_ai_world_2026.pptx)                           | Memory engineering from first principles (Oracle AI World 2026).                                        |
| 2. Implementation   | [Oracle AI Agent Memory developer guide notebook](./notebooks/agent_memory/oracle_agent_memory_developer_guide.ipynb)     | The `oracleagentmemory` API: users and agents, memories, threads, extraction, and retrieval.            |
| 2. Implementation   | [Short-term vs long-term agent memory notebook](./notebooks/agent_memory/short_term_vs_long_term_agent_memory_26_6.ipynb) | Thread state, summaries, durable memory, updates, TTL, and deletion.                                    |
| 2. Implementation   | [Memory and context engineering notebook](./notebooks/memory_context_engineering_agents.ipynb)                            | Six memory types built by hand with LangChain and Oracle AI Database.                                   |
| 2. Implementation   | [Agent Memory workshop](./workshops/agent_memory_workshop)                                                                | Guided build of a `MemoryManager`, with agent runs compared with and without memory.                    |
| 3. Complete example | [Oracle AI Agent Memory example apps](./apps/oracle-agent-memory)                                                         | A social-media voice agent, a Codex plugin, and an OCI IAM + Deep Data Security web app.                |
| 3. Complete example | [Finance AI agent demo](./apps/finance-ai-agent-demo)                                                                     | A financial services agent with Oracle AI Database as its memory core.                                  |
| 3. Complete example | [Enterprise Data Agent Harness workshop](./workshops/enterprise-data-agent-harness-workshop)                              | A memory-aware data agent running in a Flask + React chat UI.                                           |
| 3. Complete example | [Java agent memory with Spring AI](./apps/oracle-database-java-agent-memory)                                              | Episodic, semantic, and procedural memory for Java developers.                                          |
| 3. Complete example | [TypeScript memory assistant with Mem0](./apps/oracle-mem0-ts-memory)                                                     | User-scoped memory for JavaScript and TypeScript developers.                                            |

### Which memory option do I need?

Oracle AI Database backs several kinds of agent memory, each through its own package. They combine: one agent often uses two or three of them.

| You need                                                                                                                   | Use                                | Package              | Example in this hub                                                                                                            |
| -------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| To resume a LangGraph run where it stopped: per-thread state and checkpoints                                               | `OracleSaver` / `AsyncOracleSaver` | `langgraph-oracledb` | [AI on-call triage notebook](./notebooks/langchain_ecosystem/ai_oncall_triage_langchain.ipynb)                                 |
| Long-term facts that outlive a thread in LangGraph: a namespaced store with optional vector search                         | `OracleStore` / `AsyncOracleStore` | `langgraph-oracledb` | [Research agent with Deep Agents notebook](./notebooks/langchain_ecosystem/research_agent_with_deepagents_oracle.ipynb)        |
| A durable chat transcript for each session                                                                                 | `OracleChatMessageHistory`         | `langchain-oracledb` | [Semantic cache and chat history notebook](./notebooks/langchain_ecosystem/langchain_oracle_semantic_cache_chat_history.ipynb) |
| Managed agent memory: threads, memories extracted from conversations, context cards, and vector, keyword, or hybrid search | Oracle AI Agent Memory             | `oracleagentmemory`  | [Oracle AI Agent Memory developer guide notebook](./notebooks/agent_memory/oracle_agent_memory_developer_guide.ipynb)          |
| The Mem0 API with Oracle AI Database as the store                                                                          | Mem0                               | `mem0ai`             | [TypeScript memory assistant with Mem0](./apps/oracle-mem0-ts-memory)                                                          |

Oracle AI Agent Memory is not a LangGraph checkpointer or store. In a LangGraph workflow, call it from nodes or tools, as the [Mortgage Approval Workflow notebook](./notebooks/agent_memory/03_mortgage_workflow_langgraph.ipynb) does.

For a minimal script that runs without an API key, see [`agent_memory_langgraph.py`](./quickstart/agent_memory_langgraph.py) (`OracleSaver` and `OracleStore`) and [`agent_memory_sdk.py`](./quickstart/agent_memory_sdk.py) (Oracle AI Agent Memory) in the quick start.

Notebooks for the `oracleagentmemory` package (`/notebooks/agent_memory`):

| Name                                                                                        | Description                                                                                                                                                             | Stack                           | Colab                                                                                                                                                                      |
| ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [OAMP Developer Guide](./notebooks/agent_memory/oracle_agent_memory_developer_guide.ipynb)  | Step-by-step guide to the `oracleagentmemory` API: connection, the three core primitives (users/agents, memories, threads), automatic extraction, and vector retrieval. | OAMP, LiteLLM                   | [Open in Colab](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/agent_memory/oracle_agent_memory_developer_guide.ipynb) |
| [OAMP Benchmarks](./notebooks/agent_memory/oracle_agent_memory_benchmarks.ipynb)            | Quantify token cost, latency, and response quality of OAMP vs. naive flat-history memory across 80 scripted turns with three agent variants.                            | OAMP, LiteLLM, OpenAI           | [Open in Colab](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/agent_memory/oracle_agent_memory_benchmarks.ipynb)      |
| [Deep Research Agent](./notebooks/agent_memory/01_deep_research_openai_agents.ipynb)        | Build a deep research agent for human genome exploration that uses Tavily for live web search and Oracle AI Agent Memory for durable findings across sessions.          | OpenAI Agents SDK, Tavily, OAMP | [Open in Colab](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/agent_memory/01_deep_research_openai_agents.ipynb)      |
| [Supply Chain Assistant](./notebooks/agent_memory/02_supply_chain_claude_agent_sdk.ipynb)   | A supply chain assistant that tracks shipment cargo via in-process tools and an MCP server, with shipment records and operational notes persisted in OAMP.              | Claude Agent SDK, MCP, OAMP     | [Open in Colab](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/agent_memory/02_supply_chain_claude_agent_sdk.ipynb)    |
| [Mortgage Approval Workflow](./notebooks/agent_memory/03_mortgage_workflow_langgraph.ipynb) | A deterministic mortgage approval workflow modeled as a LangGraph `StateGraph` where OAMP persists applicant data and audit trails so failed runs can resume.           | LangGraph, OAMP                 | [Open in Colab](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/agent_memory/03_mortgage_workflow_langgraph.ipynb)      |

> See the [Agent Memory README](./notebooks/agent_memory/README.md) for every agent memory notebook, a recommended reading order, prerequisites, and Open-in-Colab links.

## Apps

Complete, working reference applications with source code, deployment configuration, and setup instructions (`/apps`).

| Name                                                                          | Description                                                                                                                                                                                                                                                 |
| ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [FitTracker](./apps/FitTracker)                                               | Gamified fitness platform built with Oracle 26ai JSON Duality Views (FastAPI + Redis), created live during a webinar.                                                                                                                                       |
| [agentic_rag](./apps/agentic_rag)                                             | Intelligent RAG system with multi-agent Chain of Thought (CoT), PDF/Web/Repo processing, and Oracle AI Database 26ai integration.                                                                                                                           |
| [finance-ai-agent-demo](./apps/finance-ai-agent-demo)                         | Financial services AI agent with Oracle AI Database as a unified memory core for vector, graph, spatial, and relational queries.                                                                                                                            |
| [generative-ui-data-chat](./apps/generative-ui-data-chat)                     | Next.js and [OpenUI](https://github.com/thesysdev/openui) data chatbot that pairs Oracle AI Database 26ai SQL, vector, and hybrid search with typed generative UI components such as charts, KPI cards, tables, and source cards.                           |
| [oci-generative-ai-jet-ui](./apps/oci-generative-ai-jet-ui)                   | Full-stack AI application with Oracle JET UI, OCI Generative AI integration, Kubernetes deployment, and Terraform infrastructure.                                                                                                                           |
| [tanstack-shoe-store](./apps/tanstack-shoe-store)                             | AI chat app using TanStack Start and Oracle 26ai Select AI to query a shoe store database with natural language.                                                                                                                                            |
| [team-brain](./apps/team-brain)                                               | Team knowledge base with Slack, GitHub, and docs connectors, hybrid Oracle Text + vector retrieval, and row-level access control (`DBMS_RLS`), exposed to Claude Code over MCP and to a LangChain agent CLI.                                                |
| [oracle-data-migration-harness](./apps/oracle-data-migration-harness)         | AI agent harness that migrates a RAG corpus from MongoDB into Oracle AI Database 26ai while preserving vector search and unlocking SQL/JSON Duality queries.                                                                                                |
| [supplychain-demand-planning-agent](./apps/supplychain-demand-planning-agent) | Multi-agent demand-planning assistant with a LangGraph supervisor over two specialists; vector knowledge, long-term memory, per-thread checkpoints, semantic LLM cache, and chat history all share one Oracle AI Database.                                  |
| [idp-oracle-ai-database](./apps/idp-oracle-ai-database)                       | Intelligent Document Processor that keeps each document's BLOB, extracted text, structured JSON, and vector in one Oracle AI Database 26ai, with extraction, summarization, embeddings, and classification running in the database via `DBMS_VECTOR_CHAIN`. |
| [vector-development](./apps/vecdb)                                            | AI Database vector development sample apps for semantic search, RAG, product discovery, code search, and geospatial search. For Python development, see the [Oracle VecDB Python SDK](https://github.com/oracle/vecdb-python-sdk).                          |
| [oraviz-mcp](./apps/oraviz-mcp)                                               | Visualization-first MCP server for Oracle AI Database 26ai: seven read-only tools that return compact, size-capped results and render PNG charts, including PCA projections of `VECTOR` columns.                                                            |

> This table is a selection. See the [full list of apps](./apps/README.md) for every app in the repository, including the interactive appbooks.

## Notebooks

Jupyter notebooks and interactive tutorials on RAG, agents, agent memory, vector search, and Oracle AI Database features (`/notebooks`).

| Name                                                                                                               | Description                                                                                                                                                                 | Stack                                                                   | Colab                                                                                                                                                       |
| ------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [agentic_rag_langchain_oracledb_demo](./notebooks/agentic_rag_langchain_oracledb_demo.ipynb)                       | Multi-agent RAG with langchain-oracledb: OracleVS, OracleEmbeddings, OracleTextSplitter, and CoT agents.                                                                    | Oracle AI Database, langchain-oracledb, Ollama                          |                                                                                                                                                             |
| [fs_vs_dbs](./notebooks/fs_vs_dbs.ipynb)                                                                           | Compare filesystem vs database agent memory architectures.                                                                                                                  | LangChain, Oracle AI Database, OpenAI                                   | [Open in Colab](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/fs_vs_dbs.ipynb)                         |
| [memory_context_engineering_agents](./notebooks/memory_context_engineering_agents.ipynb)                           | Build AI agents with 6 types of persistent memory.                                                                                                                          | LangChain, Oracle AI Database, OpenAI, Tavily                           | [Open in Colab](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/memory_context_engineering_agents.ipynb) |
| [oracle_rag_agents_zero_to_hero](./notebooks/oracle_rag_agents_zero_to_hero.ipynb)                                 | Learn to build RAG agents from scratch using Oracle AI Database.                                                                                                            | Oracle AI Database, OpenAI, OpenAI Agents SDK                           | [Open in Colab](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/oracle_rag_agents_zero_to_hero.ipynb)    |
| [oracle_rag_with_evals](./notebooks/oracle_rag_with_evals.ipynb)                                                   | Build RAG systems with comprehensive evaluation metrics.                                                                                                                    | Oracle AI Database, OpenAI, BEIR, Galileo                               | [Open in Colab](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/oracle_rag_with_evals.ipynb)             |
| [oracle_data_migration_harness_walkthrough](./notebooks/oracle_data_migration_harness_walkthrough.ipynb)           | Walk through a MongoDB-to-Oracle AI Database migration harness with vector parity, verification, and JSON Relational Duality.                                               | Oracle AI Database 26ai, MongoDB, FastAPI, React, sentence-transformers |                                                                                                                                                             |
| [agent_reasoning_demo](./notebooks/agent_reasoning_demo.ipynb)                                                     | Interactive demo of 11 cognitive architectures (CoT, ToT, ReAct, Self-Reflection, and more) for agent reasoning.                                                            | Ollama, agent-reasoning                                                 |                                                                                                                                                             |
| [oracle_agentic_rag_hybrid_search](./notebooks/oracle_agentic_rag_hybrid_search.ipynb)                             | Agentic RAG with vector, keyword, and hybrid search in a single SQL query using LangGraph ReAct agent.                                                                      | Oracle AI Database, langchain-oracledb, LangGraph, OpenAI               | [Open in Colab](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/oracle_agentic_rag_hybrid_search.ipynb)  |
| [f1_miami_strategy_oracle_26ai](./notebooks/f1_miami_strategy_oracle_26ai.ipynb)                                   | F1 Miami GP strategy intelligence for 2026 — SQL, hybrid vector+keyword search, JSON documents, and property graph in one Oracle 26ai database using real FastF1 data.      | Oracle AI Database, FastF1, sentence-transformers, Plotly               | [Open in Colab](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/f1_miami_strategy_oracle_26ai.ipynb)     |
| [cursor_mcp_oracle_ai_database](./notebooks/cursor_mcp_oracle_ai_database.ipynb)                                   | Set up Cursor to work with Oracle AI Database through the SQLcl MCP server: MCP configuration, a tool policy, database-backed memory tables, and hybrid retrieval.          | SQLcl MCP server, Oracle AI Database, Oracle AI Agent Memory            |                                                                                                                                                             |
| [codex_mcp_oracle_ai_database_memory_langchain](./notebooks/codex_mcp_oracle_ai_database_memory_langchain.ipynb)   | Set up Codex CLI to work with Oracle AI Database through the SQLcl MCP server, with Oracle AI Agent Memory and a LangChain wrapper.                                         | SQLcl MCP server, Oracle AI Database, Oracle AI Agent Memory, LangChain |                                                                                                                                                             |
| [claude_mcp_oracle_ai_database_memory_langchain](./notebooks/claude_mcp_oracle_ai_database_memory_langchain.ipynb) | Set up Claude Desktop to work with Oracle AI Database through the SQLcl MCP server, and compare Claude memory, Oracle AI Agent Memory, and LangChain.                       | SQLcl MCP server, Oracle AI Database, LangChain                         |                                                                                                                                                             |
| [antigravity_mcp_oracle_ai_database](./notebooks/antigravity_mcp_oracle_ai_database.ipynb)                         | Set up Antigravity to work with Oracle AI Database through the SQLcl MCP server, with memory tables, hybrid retrieval, and an MCP audit-log check.                          | SQLcl MCP server, Oracle AI Database, Oracle AI Agent Memory, LangChain |                                                                                                                                                             |
| [multicloud/](./notebooks/multicloud)                                                                              | AWS, Azure, Google Cloud, and MongoDB API samples running Oracle AI Database outside OCI.                                                                                   | Oracle AI Database + AWS / Azure / Google / MongoDB                     |                                                                                                                                                             |
| [vector-development](./notebooks/vecdb)                                                                            | AI Database vector development notebook collection covering auto-embedding, BYOV, search diagnostics, indexing, OCI embeddings, Gemini RAG, parks search, and bulk loading. | AI Database vector APIs, Python, Pandas                                 |                                                                                                                                                             |

> This table is a selection. See the [Notebooks README](./notebooks/README.md) for more notebooks and the subfolder collections.

## LangChain Ecosystem

Notebooks that build on the **LangChain ecosystem** — LangChain, LangGraph, Deep Agents, and Oracle's first-party integrations (`langchain-oracledb`, `langgraph-oracledb`, `langchain-oci`) — using **Oracle AI Database** as the single backend for vectors, agent memory, checkpoints, the LLM cache, and chat history (`/notebooks/langchain_ecosystem`). They build up from a starter RAG app to a multi-agent supervisor.

| Name                                                                                                                               | Description                                                                                                                                                                        | Stack                                                                                                                   | Colab                                                                                                                                                                                      |
| ---------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [oracle_langchain_example](./notebooks/langchain_ecosystem/oracle_langchain_example.ipynb)                                         | The starter: build a minimal RAG application on Oracle AI Vector Search with `OracleVS` and LangChain.                                                                             | Oracle AI Database, langchain-oracledb, HuggingFace                                                                     | [Open in Colab](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/langchain_ecosystem/oracle_langchain_example.ipynb)                     |
| [langchain_oracle_semantic_cache_chat_history](./notebooks/langchain_ecosystem/langchain_oracle_semantic_cache_chat_history.ipynb) | Two `langchain-oracledb` primitives: `OracleSemanticCache` (reuse answers for meaning-equivalent prompts) and `OracleChatMessageHistory` (durable chat transcripts).               | langchain-oracledb, OpenAI (embeddings), Anthropic                                                                      | [Open in Colab](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/langchain_ecosystem/langchain_oracle_semantic_cache_chat_history.ipynb) |
| [research_agent_with_deepagents_oracle](./notebooks/langchain_ecosystem/research_agent_with_deepagents_oracle.ipynb)               | A durable Deep Agents research agent via `langchain_oci.create_deepagents_agent`; Oracle backs the hybrid-search corpus, checkpoints, long-term notes, and the virtual filesystem. | langchain-oci (deepagents), Anthropic, HuggingFace, langgraph-oracledb, Oracle AI Database                              | [Open in Colab](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/langchain_ecosystem/research_agent_with_deepagents_oracle.ipynb)        |
| [ai_oncall_triage_langchain](./notebooks/langchain_ecosystem/ai_oncall_triage_langchain.ipynb)                                     | A LangGraph supervisor over two specialists that triages incoming issues; vector KB, long-term memory, checkpoints, semantic cache, and chat history share one Oracle AI Database. | langchain, langgraph, langgraph-supervisor, langchain-oracledb, langgraph-oracledb, Anthropic (Claude Opus 4.8), OpenAI | [Open in Colab](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/langchain_ecosystem/ai_oncall_triage_langchain.ipynb)                   |

> See the [LangChain Ecosystem README](./notebooks/langchain_ecosystem/README.md) for a recommended reading order, prerequisites, and Open-in-Colab links.

## Workshops

Hands-on, guided workshops that go from information retrieval and RAG, through agents and orchestration, to memory-augmented agents (`/workshops`). Each workshop is self-contained, with a student notebook, a complete reference notebook, step-by-step part guides, and a ready-to-run Codespaces / devcontainer environment with Oracle AI Database pre-configured.

> **Pull a single workshop without cloning the whole hub** — each workshop README includes `git sparse-checkout` instructions so you can fetch only the folder you need.

| Name                                                                                | Description                                                                                                                                                                                                                              | Stack                                                                                                                                     |
| ----------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| [Information Retrieval to RAG](./workshops/information_retrieval_to_RAG)            | Build a Research Paper Assistant over 200 ArXiv papers by implementing five retrieval strategies (keyword, vector, hybrid, graph) and a full RAG pipeline wired to OCI GenAI.                                                            | Oracle AI Database, sentence-transformers, oracledb, OCI GenAI (xAI Grok 3 Fast)                                                          |
| [From RAG to Agents](./workshops/from_rag_to_agents_workshop)                       | Extend the RAG pipeline into a multi-agent system — wrap retrieval as agent tools, compose orchestration, and add persistent session memory backed by Oracle.                                                                            | Oracle AI Database, sentence-transformers, oracledb, OpenAI API (GPT-5), openai-agents                                                    |
| [Agent Memory](./workshops/agent_memory_workshop)                                   | Build memory-aware agents: implement a `MemoryManager` with six memory types in Oracle, apply context-engineering techniques, and compare agent runs with and without memory.                                                            | Oracle AI Database, langchain-oracledb, sentence-transformers, OCI GenAI, Tavily                                                          |
| [Enterprise Data Agent Harness](./workshops/enterprise-data-agent-harness-workshop) | Build a memory-aware enterprise data agent on Oracle AI Database 26ai with OAMP, hybrid retrieval, JSON Relational Duality Views, and Deep Data Security, then run it in a Flask + React chat UI.                                        | Oracle AI Database 26ai, OAMP, langchain-oracledb, OCI GenAI, Flask, React                                                                |
| [Financial Fraud Agent Harness](./workshops/financial-fraud-agent-harness-workshop) | Build a memory-aware anti-money-laundering agent for a synthetic bank with OAMP memory, hybrid retrieval, and identity-aware policies, then run the same harness as a Flask + React app.                                                 | Oracle AI Database 26ai, OAMP, langchain-oracledb, OCI GenAI, Flask, React                                                                |
| [Soccer Analytics Agent](./workshops/soccer-analytics-agent)                        | Build a FIFA World Cup analytics agent with Oracle-backed memory, hybrid retrieval, and an XGBoost prediction pipeline served through FastAPI + React.                                                                                   | Oracle AI Database, langchain-oracledb, langgraph-oracledb, XGBoost, FastAPI, React, OCI GenAI (Grok 4)                                   |
| [Supply-Chain Demand Planning Agent](./workshops/supplychain_demand_agent_workshop) | Build a multi-agent demand-planning assistant (a LangGraph supervisor over two specialists) where vectors, memory, checkpoints, semantic cache, and chat history share one Oracle AI Database. Includes a live FastAPI + React chat app. | Oracle AI Database, langchain-oracledb, langgraph-oracledb, langgraph-supervisor, FastAPI, React, OCI GenAI (xAI Grok 4.1 Fast Reasoning) |

> See the [Workshops README](./workshops/README.md) for how a workshop is organised and how to get started.

## Guides

Conference presentations on AI agent architecture, reasoning strategies, and memory systems (`/guides`). These are slide decks; the links open or download the file.

| Name                                                                                                                     | Description                                                                                                                                                                                                                                                  | Format  |
| ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------- |
| [Building the Brain and Backbone of Enterprise AI Agents](./guides/brain_backbone_enterprise_agents_devweek_sf_2026.pdf) | The 2026 agent stack, reasoning patterns (Chain of Thought, Tree of Thoughts, Self-Reflection), and context/belief updates for enterprise AI agents. Presented at DevWeek SF 2026 by Nacho Martinez.                                                         | PDF     |
| [Memory Engineering: The Discipline Behind Memory Augmented Agents](./guides/memory_engineering_devweek_sf_2026.pdf)     | Memory engineering as a discipline: the memory ecosystem, form factors, and the practices behind memory-augmented agents. DevWeek SF 2026 keynote by Richmond Alake.                                                                                         | PDF     |
| [Agent Memory with Oracle AI Database](./guides/dlai_aidev_agent_memory.pptx)                                            | Agent memory architectures and Oracle AI Database as the memory core for AI agents. Presented at the AI Developer Conference hosted by DeepLearning.AI in April 2026 by Eli Schilling.                                                                       | PPTX    |
| [Memory Engineering with Deep Agents](./guides/memory_engineering_deep_agents_langchain.key)                             | The four memory layers, the Deep Agents middleware architecture (AGENTS.md, skills, checkpointing), and the four ways memory breaks. Presented by Colin Francis (LangChain).                                                                                 | Keynote |
| [Oracle AI Database + Agent Memory with LangChain](./guides/oracle_ai_database_agent_memory_langchain.pptx)              | Building a multi-agent stack on a single database with LangChain and LangGraph: `AsyncOracleSaver` checkpoints, long-term memory, `OracleSemanticCache`, and vector + lexical retrieval. Presented by Richmond Alake (Oracle) and Colin Francis (LangChain). | PPTX    |
| [How Oracle AI Database Meets the AI Agent Era](./guides/oracle_ai_database_agent_era_overview.pptx)                     | Overview deck mapping Oracle AI Database to the agent landscape: four application form factors, four build modes from no-code to custom code, and the matching Oracle products. Presented by Richmond Alake (Oracle) and Colin Francis (LangChain).          | PPTX    |
| [Teach Agents What To Remember](./guides/teach_agents_what_to_remember_ai_world_2026.pptx)                               | Agent memory from first principles: the components of a memory system, memory and context engineering techniques, and Oracle AI Agent Memory, ending with the CityOps Copilot build. Presented at Oracle AI World 2026 by Richmond Alake.                    | PPTX    |

## Partners

Notebooks and apps contributed by partners in the AI ecosystem, showing how to use Oracle AI Database and OCI alongside other AI frameworks and platforms (`/partners`).

| Name                                                                                           | Description                                                                                                                                                                                                                   | Stack                                                          |
| ---------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| [CopilotKit](./partners/copilotkit)                                                            | An agentic travel app on Oracle AI Database — a CopilotKit chat over AG-UI backed by a portable Oracle Agent Spec agent on LangGraph, with Oracle Agent Memory (durable recall + supersession) and human-in-the-loop booking. | CopilotKit, Agent Spec, LangGraph, AG-UI, oracleagentmemory    |
| [spraay_x402_payment_agents_oracle](./partners/spraay/spraay_x402_payment_agents_oracle.ipynb) | Build payment-enabled AI agents with Oracle AI Database and Spraay x402 Gateway — cost-aware agents that pay for premium inference via USDC micropayments.                                                                    | Oracle AI Database, langchain-oracledb, LangChain, Spraay x402 |

## Build Paths

Oracle skills packaged as agent-agnostic markdown so that a coding agent (Claude Code, Cursor, Aider, or any agent that reads markdown skills) can scaffold a working Oracle AI project for you (`/build-paths`). Pick a path, answer a short interview, and the agent builds and verifies the project.

| Path                                       | What you build                                                                                    |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| [Beginner](./build-paths/beginner)         | A chat over your own PDFs, Markdown notes, or web pages with `langchain-oracledb` and Open WebUI. |
| [Intermediate](./build-paths/intermediate) | A tool-calling agent that talks to a live Oracle schema over MCP, with in-database embeddings.    |
| [Advanced](./build-paths/advanced)         | An agent system where Oracle AI Database is the only state store, including agent memory.         |

> See the [Build Paths README](./build-paths/README.md) for how it works and the [worked walk-throughs](./build-paths/GETTING_STARTED.md) for one build per path.

## Contributing

This project is open source. Please submit your contributions by forking this repository and submitting a pull request! Oracle appreciates any contributions that are made by the open-source community.

### Development Setup

Before contributing, please set up pre-commit hooks to ensure code is automatically formatted:

1. **Install pre-commit**:

   ```bash
   pip install pre-commit
   ```

2. **Install additional dependencies** (optional, includes pre-commit and ruff):

   ```bash
   pip install -r requirements-dev.txt
   ```

3. **Install pre-commit hooks**:

   ```bash
   pre-commit install
   ```

4. **Optional: Format existing code**:
   ```bash
   pre-commit run --all-files
   ```

The pre-commit hooks will automatically format your code using:

- **Ruff** for Python files (formatting and linting)
- **Prettier** for JavaScript, TypeScript, JSON, YAML, and Markdown files

For more detailed information, see [SETUP_PRE_COMMIT.md](./SETUP_PRE_COMMIT.md).

## License

Copyright (c) 2024 Oracle and/or its affiliates.

Licensed under the Universal Permissive License (UPL), Version 1.0.

See [LICENSE](LICENSE) for more details.

ORACLE AND ITS AFFILIATES DO NOT PROVIDE ANY WARRANTY WHATSOEVER, EXPRESS OR IMPLIED, FOR ANY SOFTWARE, MATERIAL OR CONTENT OF ANY KIND CONTAINED OR PRODUCED WITHIN THIS REPOSITORY, AND IN PARTICULAR SPECIFICALLY DISCLAIM ANY AND ALL IMPLIED WARRANTIES OF TITLE, NON-INFRINGEMENT, MERCHANTABILITY, AND FITNESS FOR A PARTICULAR PURPOSE. FURTHERMORE, ORACLE AND ITS AFFILIATES DO NOT REPRESENT THAT ANY CUSTOMARY SECURITY REVIEW HAS BEEN PERFORMED WITH RESPECT TO ANY SOFTWARE, MATERIAL OR CONTENT CONTAINED OR PRODUCED WITHIN THIS REPOSITORY. IN ADDITION, AND WITHOUT LIMITING THE FOREGOING, THIRD PARTIES MAY HAVE POSTED SOFTWARE, MATERIAL OR CONTENT TO THIS REPOSITORY WITHOUT ANY REVIEW. USE AT YOUR OWN RISK.

---

**Note**: This repository is actively maintained and updated with new resources, examples, and best practices for Oracle AI development.
