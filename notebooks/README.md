# Notebooks

This folder contains Jupyter notebooks that demonstrate how to build AI applications, agents, and systems using Oracle AI Database and OCI services. These notebooks provide hands-on tutorials, examples, and best practices for developers working with Oracle's AI capabilities.

## Contents

The notebooks cover various aspects of AI development including:

- **Memory Engineering**: Building persistent memory systems for AI agents
- **Context Engineering**: Managing LLM context windows efficiently
- **RAG (Retrieval Augmented Generation)**: Building semantic search and RAG applications
- **AI Agents**: Creating intelligent agents that interact with Oracle AI Database
- **Vector Search**: Implementing vector similarity search and embeddings
- **Evaluation & Metrics**: Measuring and evaluating AI system performance

## Notebooks

| Title                                      | Stack                                         | Use Case                                                                                                                                      | Notebook                                                                                                                                     |
| ------------------------------------------ | --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Memory & Context Engineering for AI Agents | LangChain, Oracle AI Database, OpenAI, Tavily | Build AI agents with 6 types of persistent memory. Covers memory engineering, context window management, and just-in-time retrieval patterns. | [![Open Notebook](https://img.shields.io/badge/Open%20Notebook-orange?style=flat-square)](./memory_context_engineering_agents.ipynb)         |
| Oracle RAG Agents: Zero to Hero            | Oracle AI Database, OpenAI, OpenAI Agents SDK | Learn to build RAG agents from scratch using Oracle AI Database.                                                                              | [![Open Notebook](https://img.shields.io/badge/Open%20Notebook-orange?style=flat-square)](./oracle_rag_agents_zero_to_hero.ipynb)            |
| Oracle RAG with Evaluations                | Oracle AI Database, OpenAI, BEIR, Galileo     | Build RAG systems with comprehensive evaluation metrics.                                                                                      | [![Open Notebook](https://img.shields.io/badge/Open%20Notebook-orange?style=flat-square)](./oracle_rag_with_evals.ipynb)                     |
| Code Review Assistant AgentSpec            | Agent Spec, Wayflow, Langgraph                | Build an AI agent specialized in code review assistance using AgentSpec.                                                                      | [![Open Notebook](https://img.shields.io/badge/Open%20Notebook-orange?style=flat-square)](./agentspec/code_review_assistant_agentspec.ipynb) |

## Getting Started

1. Ensure you have Jupyter Notebook or JupyterLab installed
2. Install required dependencies (each notebook includes installation instructions)
3. Set up Oracle AI Database (local Docker installation or cloud instance)
4. Open the notebook and follow along with the tutorial

## Prerequisites

- Python 3.8+
- Oracle AI Database (26ai) - Free tier available via Docker
- Jupyter Notebook or JupyterLab
- Required Python packages (specified in each notebook)

## Contributing

If you'd like to contribute a notebook, please ensure it:

- Includes clear documentation and explanations
- Uses Oracle AI Database or OCI services
- Follows best practices for AI/ML development
- Includes installation and setup instructions
