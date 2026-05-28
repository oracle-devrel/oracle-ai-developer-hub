# Agent Harness

End-to-end notebook that constructs a production-grade agent _harness_ on Oracle AI Database 26ai. An agent harness is everything around the model — memory, retrieval, tool dispatch, identity, budgets — built here from Oracle primitives (OAMP, in-DB ONNX embeddings, HNSW + Oracle Text, MLE, DBFS, Duality Views, DDS) running on a single local container.

## Contents

| Content                                                                              | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | Open                                                                                                                                                                                                                                   |
| ------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`enterprise_data_agent_heavyweight.ipynb`](enterprise_data_agent_heavyweight.ipynb) | Full build on a local Oracle AI Database 26ai container. Walks through DSN + dedicated `AGENT` user, in-database ONNX embeddings + HNSW indexes, cross-encoder reranking, hybrid vector + Oracle Text retrieval fused via RRF, vector-indexed `toolbox` and `skillbox` registries, a DBFS scratchpad with a `UTL_TO_TEXT` / `UTL_TO_CHUNKS` promotion path to OAMP, sandboxed JavaScript via Oracle MLE, the agent loop, JSON Relational Duality Views, `DBMS_SCHEDULER`-driven re-scans, and identity-aware authorization via Deep Data Security (DDS). | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/agent_harness/enterprise_data_agent_heavyweight.ipynb) |

## Layout

```
agent_harness/
├── README.md
├── enterprise_data_agent_heavyweight.ipynb
└── images/        # diagrams referenced inline by the notebook
    ├── cover-oracle-native-arch.png
    ├── cover-oracle-reference-arch.png
    ├── cover-duality-view.png
    ├── cover-skillbox-flow.png
    ├── cover-toolbox-flow.png
    ├── oamp_memory_discpline.png
    ├── oamp_breakdown.png
    ├── dual_memory_substrate.png
    └── ingestion-pipeline.png
```
