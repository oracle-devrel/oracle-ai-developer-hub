# Session memory with Oracle AI Agent Memory

[Open the notebook](session_memory.ipynb) to save a preference, retrieve it after reconnecting, extract another preference automatically, and recall a message from an earlier thread. Learn about the [Oracle AI Agent Memory SDK](https://www.oracle.com/database/ai-agent-memory/) and its [setup guide](https://docs.oracle.com/en/database/oracle/agent-memory/26.8/guide/get-started.html).

## Files

| File | Purpose |
| --- | --- |
| `session_memory.ipynb` | Executable walkthrough with saved outputs |
| `memory_demo.py` | Connection, in-database embeddings, model calls, capture and replay helpers |
| `requirements.txt` | Pinned Python dependencies |
| `captures/*.json` | Real OpenAI answers and SDK extraction output, including inputs and capture dates |
| `.env.example` | Configuration keys; copy values into the checkout-root `.env` |

Keep this folder intact. It contains the notebook, helper code, and captured model responses needed to run the examples.

## Prerequisites

Use Python 3.10-3.14 on a platform supported by the pinned `oracleagentmemory` wheel, and Oracle AI Database 26ai with AI Vector Search. The validation environment uses Python 3.14. Oracle is required in both live and recorded modes. An OpenAI API key is optional; live calls incur provider charges.

The SDK's managed schema requires `CREATE TABLE`, `CREATE PROCEDURE`, `CREATE PROPERTY GRAPH`, and `CREATE TRIGGER`. `CREATE JOB` allows it to create its retention purge job; without that privilege the SDK documents a warning and still initializes. The model-loading cell also requires `CREATE MINING MODEL`. Use a schema owner for this demo. A database administrator should grant these privileges to the existing demo user; the notebook does not elevate its connection.

## Database setup

Set `DB_USER`, `DB_PASSWORD`, and `DB_DSN` in the Developer Hub root `.env`, the same file used by the other companions. Existing environment variables take precedence. Wallet configuration is outside this example. For a local database, follow [Oracle's local setup guide](https://docs.oracle.com/en/database/oracle/agent-memory/26.8/guide/run-locally.html).

The notebook uses `memory_store_id="SM_VIDEO"` for its SDK-managed database objects. It never recreates an existing store. Each execution uses a new synthetic user so fixtures from a previous interrupted run do not alter retrieval.

Embeddings run inside Oracle. If `SM_MINILM_L12_V2` is missing, the helper downloads Oracle's augmented all-MiniLM-L12-v2 ONNX model (about 130 MB) from Oracle Object Storage and uploads it through `DBMS_VECTOR.LOAD_ONNX_MODEL` using a BLOB. Tokenization is included in the model. The notebook machine needs outbound HTTPS for that first download. Set `SESSION_MEMORY_EMBED_MODEL` to reuse an existing 384-dimensional compatible model. No OpenAI embedding service is required.

```dotenv
DB_USER=
DB_PASSWORD=
DB_DSN=localhost:1521/FREEPDB1
OPENAI_API_KEY=
SESSION_MEMORY_MODEL=gpt-4.1-mini
SESSION_MEMORY_EXTRACTION_MODEL=gpt-4.1-mini
SESSION_MEMORY_DEMO_DATE=2026-11-20
SESSION_MEMORY_TIMEZONE=America/New_York
```

The Oracle program identifier is `devs-explains-agent-session-memory`, set before opening connections.

## Python setup

From the Developer Hub root, run:

```sh
jupyter lab notebooks/session_memory/session_memory.ipynb
```

The first code cell installs pinned packages into the running kernel. Restart the kernel after installation if incompatible package versions were already imported, then run the notebook in order.

The notebook locates the `.env` at the nearest Git checkout root. `SESSION_MEMORY_ENV_FILE` can explicitly select a different ignored configuration file. Credentials are never printed or written into captures.

## Live calls and recorded results

When `OPENAI_API_KEY` is set, answers use the OpenAI Responses API and the SDK extraction uses its `Llm` adapter configured with `openai/<model>`. Both use the same key; their models can be configured separately. Inline extraction makes the extracted records available before the next cell. Extraction instructions keep explicit lasting preferences; automatic linking and context summaries are disabled to keep the example focused.

Without a key, answers replay their committed captures only when the assembled request matches the captured request exactly. Extraction replay validates its source message and instructions, then explicitly inserts the captured records with `origin="recorded-extraction-replay"`. Output labels say "RECORDED". No-key mode never pretends that an LLM ran. Oracle writes, reconnect, searches, and cleanup remain live. A failed live API call raises an error instead of silently switching modes.

Normal live runs save model artifacts to ignored `results/`. Set `SESSION_MEMORY_CAPTURE=1` only when intentionally refreshing the committed synthetic captures. Review changes to the captured inputs, model identifiers, and dates along with the outputs. A changed demo date changes the history-answer input and requires a fresh capture. Recorded model responses do not establish that a new live run produced the same wording.

## Reading the demo cells

The cells show their question, source message, preference, and extraction instructions inline. Retrieved text stays dynamic and is printed before the answer so the displayed context comes from the database. `asyncio.to_thread` runs the blocking OpenAI/capture helper in a worker thread while `await` lets Jupyter wait without blocking its event loop; it does not start another agent or conversation.

History retrieval uses the full answer-free question `Where have I worked from recently?`. The SDK is explicitly configured with `SearchStrategy.VECTOR`; Oracle embeds the question and ranks stored message vectors by similarity. The notebook takes the top result and displays its source timestamp and thread. It performs no date parsing or answer-string selection. "Recently" is conversational wording here, not an enforced time window. A specific-day question would need temporal filtering.

## Check results

The notebook checks that the manually saved preference survives reconnection, the new thread differs from the old one, the preference is in the model input, the coffee-shop statement is absent from that coding input, the recalled evidence belongs to the correct source thread, and another synthetic user's search returns no preference. The answer's language choice alone is not proof of retrieval.

History search retrieves at most five semantic candidates within the synthetic user's scope. It does not enforce recency. A production app should use authenticated identity for scoping. Retrieved text is quoted evidence; this labeling alone does not prevent prompt injection.

## Cleanup

The final cell calls `memory.delete_user(user_id, cascade=True)` to remove this run's threads, messages, and memories, verifies empty retrieval, and closes the pool. It leaves the managed `SM_VIDEO` store and embedding model available for reuse. Interrupted runs may leave synthetic users behind; use their printed IDs with the SDK's deletion API. Remove store objects or models only as a separate, deliberate database administration task.

## References

- [SDK setup and supported models](https://docs.oracle.com/en/database/oracle/agent-memory/26.8/guide/get-started.html)
- [Automatic extraction configuration](https://docs.oracle.com/en/database/oracle/agent-memory/26.8/guide/int-customize-memory-extraction.html)
- [Thread API](https://docs.oracle.com/en/database/oracle/agent-memory/26.8/guide/api/thread.html)
- [Search scope and record lifecycle](https://docs.oracle.com/en/database/oracle/agent-memory/26.8/guide/api/search.html)
