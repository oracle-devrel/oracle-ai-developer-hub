# Quick start: vector search, hybrid search, RAG, and agent memory

These scripts run on a local Oracle AI Database in a Docker container. They need no sign-up and no
API key. Embeddings are computed inside the database by an ONNX model, so nothing leaves your
machine.

| Script                                                         | What it shows                                                                                                                                                                            |
| -------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`setup_database.py`](./setup_database.py)                     | Waits for the database, creates the user `quickstart`, loads the embedding model. Safe to run again.                                                                                     |
| [`vector_and_hybrid_search.py`](./vector_and_hybrid_search.py) | `VECTOR` column, vector index, similarity search with a metadata filter, hybrid vector index and `DBMS_HYBRID_VECTOR.SEARCH`, then the same through `OracleVS` and the hybrid retriever. |
| [`rag.py`](./rag.py)                                           | In-database chunking and embeddings, `OracleVS`, and a LangChain (LCEL) chain. Generates an answer when you name a local Ollama model.                                                   |
| [`agent_memory_langgraph.py`](./agent_memory_langgraph.py)     | A LangGraph agent whose thread state (`OracleSaver`) and long-term facts (`OracleStore`) live in the database.                                                                           |
| [`agent_memory_sdk.py`](./agent_memory_sdk.py)                 | Oracle AI Agent Memory (`oracleagentmemory`): store a memory, recall it in a later process.                                                                                              |

Each example script is self-contained: you can read, copy or run it on its own after setup.

## What you need

- Docker.
- Python 3.11 or newer. `oracleagentmemory` declares 3.11 as its minimum. Everything here was run
  on Python 3.12.3.
- Internet access for three downloads: the database image from `container-registry.oracle.com`, the
  Python packages from PyPI, and the embedding model from Oracle (about 117 MB). The image needs no
  registry login.
- About 3.4 GB of disk: 2.7 GB for the unpacked image (0.9 GB to download), 0.55 GB for the virtual
  environment and 0.12 GB for the model download.

This was tested on Linux (x86-64) only. The image is also published for arm64, but that was not
tested.

## One command with Docker Compose

This is an alternative to the step-by-step path below, which uses `docker run` and a local virtual
environment. Use one or the other. With Docker Compose you need only Docker: the Python packages
live in a small image, and the scripts in this folder are mounted into it.

```bash
git clone https://github.com/oracle-devrel/oracle-ai-developer-hub.git
cd oracle-ai-developer-hub/quickstart
docker compose up --attach quickstart
```

Compose builds the Python image, starts Oracle AI Database Free, waits until it is healthy, runs
`setup_database.py` and then `vector_and_hybrid_search.py`, and returns to the prompt when the
script is done. The database container keeps running. With the database image already downloaded,
the first run took two to three minutes on a Linux test machine: about half of that to build the
Python image, the rest to start the database, prepare it and run the example. The end of the
output:

```text
quickstart-1  | LangChain vector search for 'money back' (category = billing):
quickstart-1  |   Premium customers can request a full refund within 30 days.
quickstart-1  |   Annual plans are billed once a year and prorated on cancellation.
quickstart-1  | LangChain hybrid search for 'ORA-51803 vector dimensions':
quickstart-1  |   score 80.9  Error ORA-51803 means the vector has a different number of dimensions.
quickstart-1  |   score 47.6  Critical incidents are answered within one hour.
quickstart-1  |   score 47.1  Annual plans are billed once a year and prorated on cancellation.

quickstart-1 exited with code 0
```

Without `--attach quickstart`, `docker compose up` also works, but it keeps printing the database
log and does not return until you press Ctrl+C, which stops the database too. Running the command
again is safe: setup does nothing the second time.

Run the other examples against the same database. The password and the address of the database are
already set inside the container:

```bash
docker compose run --rm quickstart python rag.py
docker compose run --rm quickstart python agent_memory_langgraph.py --reset "My name is Ada"
docker compose run --rm quickstart python agent_memory_sdk.py remember --reset "The user prefers answers in French."
docker compose run --rm quickstart python agent_memory_sdk.py recall "What language does the user want?"
```

The output is the same as in the steps below. Edits to the scripts apply at once, because the folder
is mounted into the container.

If port 1521 on your machine is taken, publish the database on another port. The scripts talk to
the database over the Compose network, so only the published port changes:

```bash
QUICKSTART_DB_PORT=1522 docker compose up --attach quickstart
```

To remove the containers, the network and the database data:

```bash
docker compose down -v
```

### GitHub Codespaces

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/oracle-devrel/oracle-ai-developer-hub?devcontainer_path=.devcontainer%2Fquickstart%2Fdevcontainer.json)

The button opens a codespace with Python and the database as a second container, with the
environment variables set. When it is ready, open the terminal and run:

```bash
cd quickstart
python setup_database.py
python vector_and_hybrid_search.py
```

## Run it

The commands below are for a Bash shell. The output shown is from a new container and a new virtual
environment. Every script can be run again.

### 1. Start the database

```bash
export ORACLE_PWD=Quickstart2026
docker run -d --name oracle-free -p 127.0.0.1:1521:1521 -e ORACLE_PWD=$ORACLE_PWD \
  container-registry.oracle.com/database/free:latest-lite
```

`ORACLE_PWD` is the password of the database user `SYSTEM`. `setup_database.py` creates the user
`quickstart` with the same password, and every script logs in as `quickstart`. This is for a local,
throwaway database: do not reuse a real password. The port is published on `localhost` only.

Use letters and digits in the password. Characters such as `@`, `/` and `$` break shell quoting and
connection strings, and `setup_database.py` rejects a double quote.

The tag `latest-lite` is the smaller image of Oracle AI Database 26ai Free, release 23.26.4 when
this was written. The database is ready about 30 seconds after `docker run`. Look for `(healthy)`
in `docker ps`, or for this line in the log:

```bash
docker logs oracle-free | grep "DATABASE IS READY TO USE"
```

You do not have to wait: `setup_database.py` retries for up to five minutes.

### 2. Install the packages

From the `quickstart` folder:

```bash
cd quickstart
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell, activate with `venv\Scripts\Activate.ps1` and set the variable with
`$env:ORACLE_PWD = "Quickstart2026"`. Windows was not tested.

`requirements.txt` pins the six packages the scripts import. It took about 35 seconds and downloaded
about 125 MB.

### 3. Set up the database

```bash
python setup_database.py
```

```text
Connected to localhost:1521/FREEPDB1: Oracle Database 23.26.4.0.0
Created tablespace QS_DATA (/opt/oracle/oradata/FREE/FREEPDB1/qs_data01.dbf) because SYSTEM cannot hold vectors.
Created user QUICKSTART.
Downloading the embedding model (about 117 MB) ...
Loaded model ALL_MINILM_L12_V2 in 3.3s.
Ready. Log in as QUICKSTART at localhost:1521/FREEPDB1.
```

The first run took about 8 seconds. A second run takes under a second and prints
`Model ALL_MINILM_L12_V2 is already loaded.` The script does four things:

- It logs in as `SYSTEM`, retrying until the database accepts connections.
- It creates a tablespace `QS_DATA` only if the default tablespace cannot hold `VECTOR` columns. The
  `latest-lite` image has only `SYSTEM`, which cannot (error `ORA-43853`). The `latest` image has a
  suitable `USERS` tablespace, so the script creates nothing there.
- It creates `quickstart`, or resets its password to `ORACLE_PWD`, and grants it `create session`,
  `create table`, `create view`, `create sequence`, `create trigger`, `create procedure`,
  `create property graph` and `create mining model`. Each one is needed by at least one script.
- It loads the model `ALL_MINILM_L12_V2` (384 dimensions) from the URL in Oracle's documentation
  into the `quickstart` schema, binding the bytes as a BLOB. It needs no server directory and no
  `docker cp`. The download is cached in the system temp directory.

### 4. Vector search and hybrid search

```bash
python vector_and_hybrid_search.py
```

```text
Loaded 6 rows into QS_DOCS with in-database embeddings.
SQL vector search for 'money back' (category = billing):
  distance 0.645  Premium customers can request a full refund within 30 days.
  distance 0.806  Annual plans are billed once a year and prorated on cancellation.
SQL hybrid search for 'ORA-51803 vector dimensions':
  score 80.9 (vector 81.4, keyword 76.0)  Error ORA-51803 means the vector has a different number of dimensions.
  score 47.6 (vector 52.4, keyword 0.0)  Critical incidents are answered within one hour.
  score 47.1 (vector 51.8, keyword 0.0)  Annual plans are billed once a year and prorated on cancellation.
LangChain vector search for 'money back' (category = billing):
  Premium customers can request a full refund within 30 days.
  Annual plans are billed once a year and prorated on cancellation.
LangChain hybrid search for 'ORA-51803 vector dimensions':
  score 80.9  Error ORA-51803 means the vector has a different number of dimensions.
  score 47.6  Critical incidents are answered within one hour.
  score 47.1  Annual plans are billed once a year and prorated on cancellation.
```

What to look for:

- The refund sentence ranks first for "money back", although it shares no word with the query. A
  smaller distance is a closer match. The filter `category = billing` removes the support
  sentences.
- The hybrid search finds the sentence with the exact error code first, because the keyword score
  adds to the vector score. The other rows score on meaning alone (keyword score 0).
- The script takes 10 to 15 seconds. It uses an IVF vector index (see
  [HNSW indexes](#hnsw-indexes)).

### 5. RAG

```bash
python rag.py
```

```text
Split 2 documents into 6 chunks inside the database.
Question: How long do premium customers have to ask for a refund?
Retrieved context:
  [refund-policy] Premium customers can request a full refund within 30 days of purchase.
  [refund-policy] Refunds for annual plans are prorated after the first 30 days.
Prompt that would go to a language model:
Human: Answer the question using only the context below. Keep the answer short.

Context:
- Premium customers can request a full refund within 30 days of purchase.
- Refunds for annual plans are prorated after the first 30 days.

Question: How long do premium customers have to ask for a refund?
Answer:
No model set. To generate an answer, set OLLAMA_MODEL (see the file header).
```

Without a model, the script stops at the prompt. The retrieval half of RAG ran: the two refund
chunks came back, not the support chunks. See [Generate answers with Ollama](#generate-answers-with-ollama)
for the other half.

### 6. Agent memory with LangGraph

Run these three commands, each in its own process:

```bash
python agent_memory_langgraph.py --reset "My name is Ada"
python agent_memory_langgraph.py "What is my name?"
python agent_memory_langgraph.py --thread other "What is my name?"
```

```text
Thread 'demo', you: My name is Ada
Thread 'demo', agent: Noted: your name is Ada.
Messages in this thread, read back from the database: 2
Facts in the long-term store: {'name': 'Ada'}

Thread 'demo', you: What is my name?
Thread 'demo', agent: Your name is Ada.
Messages in this thread, read back from the database: 4
Facts in the long-term store: {'name': 'Ada'}

Thread 'other', you: What is my name?
Thread 'other', agent: Your name is Ada.
Messages in this thread, read back from the database: 2
Facts in the long-term store: {'name': 'Ada'}
```

- The second command is a new process. It finds four messages in thread `demo`: the two from the
  first process and the two it just added. `OracleSaver` stored them.
- The third command uses a new thread, which has only its own two messages, but it still knows the
  name. `OracleStore` holds that fact for every thread.
- `--reset` deletes all threads and facts first, so the sequence prints the same thing every time.
- The "model" is a few lines of pattern matching, so no key is needed. Replace the body of `reply`
  with a call to a real chat model and the persistence code stays as it is.

### 7. Agent memory with Oracle AI Agent Memory

```bash
python agent_memory_sdk.py remember --reset "The user prefers answers in French."
python agent_memory_sdk.py remember "Order 4711 was refunded on Monday."
python agent_memory_sdk.py recall "What language does the user want?"
```

```text
Stored memory: The user prefers answers in French.
Stored memory: Order 4711 was refunded on Monday.
Recalled for 'What language does the user want?', closest first:
  distance 0.458  The user prefers answers in French.
  distance 1.040  Order 4711 was refunded on Monday.
```

The memories were stored by earlier processes and found by meaning. The first call takes about 11
seconds because the SDK creates its tables, a PL/SQL package and a property graph; later calls take
a few seconds. The SDK normally also extracts memories from conversations with a language model.
That needs a model, so the script switches it off and stores the memory text itself.

## Generate answers with Ollama

`rag.py` can send the prompt to a local [Ollama](https://ollama.com) model. The import is optional:

```bash
docker run -d --name ollama -p 127.0.0.1:11434:11434 -v ollama:/root/.ollama ollama/ollama
docker exec ollama ollama pull llama3.2:1b
pip install langchain-ollama
OLLAMA_MODEL=llama3.2:1b python rag.py
```

```text
Split 2 documents into 6 chunks inside the database.
Question: How long do premium customers have to ask for a refund?
Retrieved context:
  [refund-policy] Premium customers can request a full refund within 30 days of purchase.
  [refund-policy] Refunds for annual plans are prorated after the first 30 days.
Answer from llama3.2:1b: Premium customers have 30 days from their purchase date to request a refund.
```

This ran on the CPU. Pulling the 1.3 GB model took 11 seconds and the script took about 4 seconds.
The `ollama/ollama` image is about 10.6 GB on disk; you can install Ollama from ollama.com instead.
If Ollama is not on `localhost:11434`, set `OLLAMA_BASE_URL`.

A model this small is sensitive to the wording of the prompt. Told to say "I do not know" when the
context lacks the answer, `llama3.2:1b` said so although the context held the answer.

## HNSW indexes

The scripts use IVF indexes (`organization neighbor partitions`). An HNSW index
(`organization inmemory neighbor graph`) needs memory reserved for vectors, and a fresh container
has none: `vector_memory_size` is 0, and creating an HNSW index fails with `ORA-51962: The vector
memory area is out of space for the current container`. Setting a 512 MB pool and restarting
the database made an HNSW index creation succeed:

```bash
docker exec -i oracle-free sqlplus -S / as sysdba <<'SQL'
alter system set vector_memory_size = 512M scope=spfile;
shutdown immediate
startup
SQL
```

The `startup` restarts the database inside the container, not the container.

## Use another database

Every script reads these variables:

| Variable      | Default                   | Meaning                                                        |
| ------------- | ------------------------- | -------------------------------------------------------------- |
| `ORACLE_PWD`  | none, required            | Password of `SYSTEM` (setup only) and of the user `quickstart` |
| `ORACLE_DSN`  | `localhost:1521/FREEPDB1` | `host:port/service_name`                                       |
| `ORACLE_USER` | `quickstart`              | Application user to create and use                             |

For another host or port, set `ORACLE_DSN` for every command, for example
`ORACLE_DSN=localhost:1522/FREEPDB1 python setup_database.py`. `setup_database.py` logs in as
`SYSTEM`, so it needs that password. The example scripts only need the `quickstart` user.

Other images were tried too, with the scripts unchanged:

- `container-registry.oracle.com/database/free:latest` ran setup and all four scripts without
  changes. It is a 2.1 GB download.
- `gvenzl/oracle-free:latest` also ran setup and all four scripts without changes, but it ignores
  `ORACLE_PWD`: the container exits at once and asks for `ORACLE_PASSWORD`. Start it with
  `-e ORACLE_PASSWORD=$ORACLE_PWD` instead.

Autonomous Database and other remote databases were not tested.

## Troubleshooting

- **`Set ORACLE_PWD to the password you passed to docker run.`** The variable is not set in this
  shell.
- **`Could not connect as quickstart ... ORA-01017` and `Run setup_database.py first.`** The user
  does not exist yet, or `ORACLE_PWD` differs from the password given to `docker run`.
- **`Model ALL_MINILM_L12_V2 is not loaded.`** Run `setup_database.py`.
- **`Waiting for the database` repeats.** The code in brackets is the last connection error.
  `DPY-6005` or `ORA-01109` means the container is still starting, or `ORACLE_DSN` points at the
  wrong host, port or service. `ORA-01017` for more than a few seconds means `ORACLE_PWD` is not the
  password given to `docker run`; a starting container also shows it briefly. After five minutes
  the script gives up and prints the full error.
- **Port already allocated.** `docker run` fails with "port is already allocated" when another
  container or process uses port 1521. Publish another host port, for example
  `-p 127.0.0.1:1522:1521`, and set `ORACLE_DSN=localhost:1522/FREEPDB1` for every command.
- **`ORA-43853: VECTOR type cannot be used in non-automatic segment space management tablespace`.**
  The user's default tablespace is `SYSTEM`. `setup_database.py` avoids this; it appears if you
  create the user yourself.

## Things to know

- `OracleEmbeddings` with `provider="database"` fails with python-oracledb 26.1 and 26.2 in thin
  mode: `DPY-3013: unsupported Python type str for database type DB_TYPE_CLOB` (langchain-oracledb
  1.7.0). The same call works with python-oracledb 4.0.2. `vector_and_hybrid_search.py` and `rag.py`
  therefore define a small subclass, `InDatabaseEmbeddings`, that calls the SQL function
  `VECTOR_EMBEDDING` instead. It keeps the `OracleEmbeddings` type, which
  `OracleHybridSearchRetriever` requires. `OracleEmbeddings` also sets
  `oracledb.defaults.fetch_lobs = False` as a side effect, which the hybrid retriever relies on, so
  `vector_and_hybrid_search.py` sets it itself.
- `vector_and_hybrid_search.py` and `rag.py` create tables whose names start with `QS_` and
  recreate them on every run. `agent_memory_langgraph.py` and `agent_memory_sdk.py` keep their data
  between runs on purpose; `--reset` clears it.
- To start over, run `docker rm -f oracle-free`. The container has no volume, so this deletes the
  database.

## Where to go next

- [Oracle AI Agent Memory developer guide notebook](../notebooks/agent_memory/oracle_agent_memory_developer_guide.ipynb):
  the `oracleagentmemory` API in depth.
- [Hybrid retrieval pipeline notebook](../notebooks/hybrid_retrieval_pipeline.ipynb): hybrid search
  with more data.
- [ONNX embeddings notebook](../notebooks/onnx_embeddings_oracle_ai_database.ipynb): loading other
  embedding models into the database.
- [Agentic RAG with `langchain-oracledb` notebook](../notebooks/agentic_rag_langchain_oracledb_demo.ipynb):
  RAG with an agent.
- [Agent Memory workshop](../workshops/agent_memory_workshop): a guided build of agent memory.
- [Top-level README](../README.md): all notebooks, apps and workshops.
