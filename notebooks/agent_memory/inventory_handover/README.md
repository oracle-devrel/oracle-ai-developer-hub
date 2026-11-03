# Inventory Handover · Notebook

[`inventory_handover_agent_memory_oci.ipynb`](./inventory_handover_agent_memory_oci.ipynb),
_Agent Memory: Introduction to context and memory engineering_, builds a memory aware agent that
helps the next inventory planner pick up an unfinished restocking decision. Alice proposed 80
ceramic mugs, the manager approved 120 under PO-1048, and no supplier order has been submitted.
The same question comes back in every Part: a bare model, a transient tool-using agent and
finally an agent that recalls the decision from Oracle. You can see exactly which building block
changes the evidence the model gets.

It is a guided lab with 17 TODOs (this is the complete edition, with the worked code). It uses
Oracle AI Agent Memory (OAMP) 26.8, Oracle AI Database 26ai with in-database ONNX embeddings,
LangChain, and Grok (`xai.grok-4.3`) on OCI Generative AI. Allow 150–180 minutes.

| Part | What you learn                                                                    |
| ---- | --------------------------------------------------------------------------------- |
| 1–2  | the inventory process, and where context, tools and durable memory belong         |
| 3    | the services and the case                                                         |
| 4    | why a fluent answer is not persistent knowledge                                   |
| 5    | why tools alone do not retain prior experience                                    |
| 6    | storing episodes, facts and procedures, and superseding a fact without erasing it |
| 7    | how a fresh session recalls an earlier decision                                   |
| 8    | retrieval, pruning, operation events and the context card                         |
| 9    | review before a write, reusing a lesson, expiry and scoped cleanup                |

**Appbook:** [`apps/appbooks/inventory_handover`](https://github.com/oracle-devrel/oracle-ai-developer-hub/tree/main/apps/appbooks/inventory_handover) is the interactive
companion. Each Part becomes a page of diagrams that runs this notebook's code live. It shows
every model call's prompt and reply, and the review gate asks you to approve the handover draft.

## Files

| Path                                        | What it is                                                 |
| ------------------------------------------- | ---------------------------------------------------------- |
| `inventory_handover_agent_memory_oci.ipynb` | the notebook, saved with the outputs of a full run         |
| `inventory_data.json`                       | the case                                                   |
| `diagrams/`                                 | the notebook's diagrams (SVG)                              |
| `requirements.txt`                          | OAMP 26.8.0 and the versions the lab pins                  |
| `.env.example`                              | settings; copy to `.env` (the appbook reads the same file) |

## Run

The notebook was written for the Oracle LiveLabs workshop image, whose environment ships an
older OAMP. Its first cell therefore installs `requirements.txt` into a `.packages` folder beside
the notebook and imports OAMP 26.8 from there. That cell installs with `--no-deps`, so on your
own machine install the same file normally first:

```bash
cd notebooks/agent_memory/inventory_handover
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt jupyterlab pandas oci-openai
cp .env.example .env               # then set DBPASSWORD and OCI_GENAI_API_KEY (or COMPARTMENT_OCID)
jupyter lab inventory_handover_agent_memory_oci.ipynb
```

`oci-openai` is only needed for OCI config-file signing; an API key works without it.

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

### OCI Generative AI

Use either an API key (`OCI_GENAI_API_KEY`), or OCI config-file signing (`~/.oci/config`) with
`COMPARTMENT_OCID`. An API key works only in the region it was created in, so set `ENDPOINT` to
that region's inference endpoint. Requests are billed to the tenancy.
