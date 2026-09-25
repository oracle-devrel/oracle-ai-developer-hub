# Using Jev and Oracle AI Database to govern agent memory

Companion code for the Oracle AI Database article [*Using Jev and Oracle AI Database to govern agent memory*](https://blogs.oracle.com/developers/using-jev-and-oracle-ai-database-to-govern-agent-memory).

[Open the notebook](oracle_jev_memory.ipynb) to run memory retrieval, context selection, and fact promotion against Oracle AI Database 26ai. Jev assesses supplied evidence through the TypeSafe API. The application applies the thresholds and writes accepted facts with their provenance.

All customer records are synthetic. A normal run makes 19 paid Jev calls and stores fixture data in the `DB_USER` schema, alongside the other memory notebooks. It produces an evidence package for a reasoning model; it doesn't generate a customer response or issue a refund.

## Files

| File | Purpose |
| --- | --- |
| `oracle_jev_memory.ipynb` | Walkthrough with saved execution outputs |
| `memory_examples.py` | Database operations, fixtures, and application policies |
| `schema.sql` | Memory table definitions, loaded by Python |

Keep these files together. The folder can be copied into the Developer Hub's `notebooks/` directory without the article workspace.

## Prerequisites

Use Python 3.11 or later and Oracle AI Database 26ai with Oracle Text available. You also need a [TypeSafe API key](https://docs.typesafe.ai/) with access to `jev-1.13.0`.

The notebook connects with the same `DB_USER`, `DB_PASSWORD`, and `DB_DSN` as the other memory notebooks, such as [hybrid_retrieval_pipeline.ipynb](../hybrid_retrieval_pipeline.ipynb). That user needs `DB_DEVELOPER_ROLE`, `CREATE SESSION`, `CREATE TABLE`, `CREATE MINING MODEL`, and `EXECUTE ON DBMS_RLS`. Wallet-based connections aren't configured by this example.

## Database setup

No manual database setup is needed. The notebook creates everything in the `DB_USER` schema.

If the user doesn't have `ALL_MINILM_L12_V2`, the notebook downloads Oracle's augmented all-MiniLM-L12-v2 ONNX model (about 130 MB) from Oracle Object Storage and loads it with the BLOB overload of `DBMS_VECTOR.LOAD_ONNX_MODEL`. The file goes from the notebook straight into the database, so no directory object or administrator step is needed, but the notebook machine needs outbound HTTPS. When the model is already loaded, the notebook only checks that it returns 384 dimensions.

The notebook then creates the `jev_*_memory` tables, the `set_jev_memory_ctx` package, the `jev_memory_ctx` application context, the `jev_memory_tenant_policy` VPD function, and the policies. The `jev_` prefix keeps them apart from the `memory_ctx`, `set_memory_ctx`, and unprefixed memory tables that the other memory notebooks create in the same schema.

## Python setup

Download the entire folder. The notebook's first code cell installs its pinned packages (`oracledb`, `typesafe-sdk`, `python-dotenv`) into the running kernel, so no separate install step is needed.

The same cell raises `httpcore` to 1.0.9 or later. `typesafe-sdk` needs `h11` 0.16 or newer, and earlier `httpcore` releases reject that version. JupyterLab's own `httpx` often uses one of those releases, so without the upgrade pip reports a dependency conflict when the kernel runs in the same environment as JupyterLab.

Add these keys to the `.env` at the repository root, the same file the other notebooks read:

```bash
DB_USER=
DB_PASSWORD=
DB_DSN=localhost:1521/FREEPDB1
TYPESAFE_API_KEY=
# Optional
JEV_MODEL=jev-1.13.0
```

`load_dotenv()` walks up from the working directory to find that file, and environment variables take precedence over `.env` values. Keep credentials out of notebook cells and outputs.

Open the notebook from the repository root:

```bash
jupyter lab notebooks/oracle_jev_memory/oracle_jev_memory.ipynb
```

Jupyter starts the kernel in the notebook's folder, so `load_dotenv()` finds the repository `.env` and the notebook can import `memory_examples.py`.

Select any Python 3.11+ kernel and run the cells in order. The first code cell installs the packages. The next cells connect, load the embedding model if it's missing, create missing tables, apply VPD policies, and seed new fixture tenants. Restart the kernel before a full rerun. Fixture tenants from earlier runs stay in the database unless their cleanup cell ran.

Each completed run writes `results/run-<id>.json`, which this folder's `.gitignore` excludes; the repository `.gitignore` excludes `.env`.

## Check the results

The notebook asserts database checks for tenant isolation and retrieval filtering, along with provenance and stale-evidence behavior. The final evaluation compares Jev's decisions with fixture expectations. A completed run can still report an evaluation miss; inspect those results before accepting a change. Saved probabilities and timings describe that run and can vary on subsequent calls.

The batching comparison alternates request order and reports API latency, token usage, and policy agreement. It has no reasoning-model baseline. Its cost estimate uses [TypeSafe's published Jev 1.13 rate](https://docs.typesafe.ai/models), checked September 23, 2026: $0.042 per million input tokens, with free outputs. Update `INPUT_PRICE_PER_MILLION` in `memory_examples.py` when the rate changes.

## Scope and lifecycle

This is a schema-owner demo. The owner can administer VPD, and the context setter accepts an explicit tenant ID. A deployed service needs a separate runtime principal and identity supplied by trusted authentication middleware. Concurrent promotion requires a coordinated write protocol beyond the evidence checks shown here.

The cleanup cell at the end of the notebook deletes the run's fixture tenants, assessments, and promoted rows. Skip it to keep them for inspection. To remove the demo entirely, drop the `jev_` tables' VPD policies and tables, then `jev_memory_tenant_policy`, the `jev_memory_ctx` context, and the `set_jev_memory_ctx` package. Deleting the local `results/` folder doesn't touch database records.

## References

- [Multi-tenant schema walkthrough](https://github.com/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/multitenant_schema_walkthrough.ipynb)
- [Two-layer memory walkthrough](https://github.com/oracle-devrel/oracle-ai-developer-hub/blob/main/notebooks/two_layer_pattern_walkthrough.ipynb)
- [Hybrid retrieval for agent memory](https://blogs.oracle.com/developers/hybrid-retrieval-for-agent-memory-vector-lexical-and-metadata-together)
- [TypeSafe primitives](https://docs.typesafe.ai/primitives)
