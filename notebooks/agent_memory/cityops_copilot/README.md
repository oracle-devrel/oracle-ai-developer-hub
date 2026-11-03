# CityOps Copilot · Notebook

[`cityops_copilot_agent_memory_ollama.ipynb`](./cityops_copilot_agent_memory_ollama.ipynb) builds a
field copilot for the inspectors who keep a city's infrastructure safe: bridges, substations,
pipelines, water-treatment plants and seawalls. When an inspector writes up what they see on
site, the copilot suggests a likely diagnosis and points to that asset's history. Its memory
spans inspectors and visits, so a new inspector at Harbor Bridge starts from what the previous
one observed, recommended and graded.

It runs on Oracle AI Database 26ai and Oracle AI Agent Memory (`oracleagentmemory` 26.4), with
in-database ONNX embeddings and `llama3.2` on a local Ollama server.

| Part | What you build                                                                                      |
| ---- | --------------------------------------------------------------------------------------------------- |
| 1    | the Oracle connection: one converged database for domain data and memory                            |
| 2    | the in-database embedder and the `OracleAgentMemory` client                                         |
| 3    | threads, verbatim messages and automatic memory extraction from inspection narratives               |
| 4    | structured findings in a `VECTOR(384)` table with an HNSW index, searched with filters in one query |
| 5    | scoping: private turns per inspector, knowledge shared per asset                                    |
| 6    | `call_copilot`, end to end, and the cross-inspector handoff                                         |

**Appbook:** [`apps/appbooks/cityops_copilot`](https://github.com/oracle-devrel/oracle-ai-developer-hub/tree/main/apps/appbooks/cityops_copilot) is the interactive
companion. Each Part becomes a page of diagrams that runs this notebook's code live, with a data
explorer for every row it writes.

## Files

| Path                                        | What it is                                                 |
| ------------------------------------------- | ---------------------------------------------------------- |
| `cityops_copilot_agent_memory_ollama.ipynb` | the notebook, saved with the outputs of a full run         |
| `data/`                                     | `maintenance_logs.json` and `inspection_reports.json`      |
| `diagrams/`                                 | the notebook's diagrams (SVG, with their Mermaid source)   |
| `requirements.txt`                          | the package versions the notebook was run with             |
| `.env.example`                              | settings; copy to `.env` (the appbook reads the same file) |

## Run

```bash
cd notebooks/agent_memory/cityops_copilot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env               # then set DBPASSWORD
ollama pull llama3.2
jupyter lab cityops_copilot_agent_memory_ollama.ipynb
```

### Oracle AI Database

The notebook expects an Oracle AI Database 26ai user (`prism` by default) with the
`ALL_MINILM_L12_V2` ONNX embedding model in its schema, on `localhost:1522/FREEPDB1`. With the
Free container, these steps match how the Oracle LiveLabs image sets up its database:

```bash
docker run -d --name oracle-free -p 1522:1521 -e ORACLE_PWD='<password>' \
  container-registry.oracle.com/database/free:latest
# once the log says DATABASE IS READY TO USE:
docker exec oracle-free bash -c 'mkdir -p /opt/oracle/dmdump && curl -fL -o /opt/oracle/dmdump/all_MiniLM_L12_v2.onnx \
  https://adwc4pm.objectstorage.us-ashburn-1.oci.customer-oci.com/p/iPX9W0MZeRkwJKWdFmdJCemmN-iKAl_bFvNGYLW7YqIrw4kKsukL24J2q93Beb9S/n/adwc4pm/b/OML-ai-models/o/all_MiniLM_L12_v2.onnx'
docker exec -i oracle-free sqlplus -s / as sysdba <<'SQL'
alter session set container = FREEPDB1;
create user prism identified by "<password>" default tablespace users quota unlimited on users;
grant connect, resource, db_developer_role, create mining model, create property graph to prism;
grant execute on dbms_vector to prism;
grant execute on dbms_vector_chain to prism;
create or replace directory dm_dump as '/opt/oracle/dmdump';
grant read, write on directory dm_dump to prism;
alter session set current_schema = prism;
begin
  dbms_vector.load_onnx_model(
    directory  => 'DM_DUMP',
    file_name  => 'all_MiniLM_L12_v2.onnx',
    model_name => 'ALL_MINILM_L12_V2',
    metadata   => json('{"function":"embedding","embeddingOutput":"embedding","input":{"input":["DATA"]}}'));
end;
/
SQL
```

### Ollama

Install [Ollama](https://ollama.com) and pull `llama3.2`. The notebook reads `OLLAMA_BASE_URL`
(default `http://localhost:11434`).
