# Sample Notebooks

Explore these VecDB-focused Jupyter notebooks for guided workflows that showcase ingestion, querying, and evaluation patterns on Oracle AI Database.

| Title | Stack | Highlights | Path |
| ----- | ----- | ---------- | ---- |
| Finance Accounts Auto | Oracle VecDB, Python, Pandas | Use hosted embedding models to vectorize financial account metadata automatically and query with filters. | [Open](./finance/finance-accounts-auto.ipynb) |
| Finance Accounts BYOV | Oracle VecDB, Python, Pandas, SentenceTransformers | Generate embeddings locally, upsert vectors, and run similarity plus metadata-filtered searches. | [Open](./finance/finance-accounts-byov.ipynb) |
| Parks Demo | Oracle VecDB, Python, Pandas | Inspect vector table stats and execute similarity queries on the National Parks dataset, with cleanup steps. | [Open](./parks/parks-demo.ipynb) |
| Search Diagnostics | Oracle VecDB, Python, Pandas | Explore seeded marketing data, compound filters, and VecDB debug payloads for semantic search. | [Open](./search/search-diagnostics.ipynb) |
| Embedding Ingest Patterns | Oracle VecDB, Python, Pandas, SentenceTransformers | Compare auto-embedding tables and bring-your-own embeddings while batching ingest workloads. | [Open](./embeddings/embedding-ingest-patterns.ipynb) |
| Maintenance Indexing Playbook | Oracle VecDB, Python, Pandas | Schedule background indexing jobs, monitor vector table health, and clean up archived partitions. | [Open](./maintenance/maintenance-indexing.ipynb) |
| Gemini VecDB RAG | Oracle VecDB, Google Gemini, Python, Pandas | Combine VecDB semantic retrieval with Gemini model completions to deliver grounded RAG answers. | [Open](./gemini/gemini-vecdb-rag.ipynb) |
| OCI Embedding Pipeline | Oracle VecDB, OCI Generative AI, Python, Pandas | Call OCI Generative AI for embeddings, persist vectors in VecDB, and refresh/query the dataset end to end. | [Open](./oci/oci-embedding-pipeline.ipynb) |
| HNSW Index Tuning | Oracle VecDB, Python, SentenceTransformers | Build an explicit HNSW index, monitor VecDB jobs, and demonstrate how `efsearch` controls candidate beam width per query. | [Open](./index_model/hnsw-efsearch-demo.ipynb) |
| Index & Model Workbench | Oracle VecDB, Python, Pandas | Manage index lifecycle, inspect hosted models, and capture annotation governance patterns in one workflow. | [Open](./index_model/index-model-workbench.ipynb) |
| Bulk Loading & Listings | Oracle VecDB, Python, Pandas | Demonstrate the three bulk-ingest flows—integrated embeddings, BYO vectors with manual IDs, and BYO vectors with auto IDs—while monitoring load jobs and listing results. | [Open](./bulk_loading/) |

Need full application samples? Visit the [Sample Apps](../../apps/vecdb) catalog.