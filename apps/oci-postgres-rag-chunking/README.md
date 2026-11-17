# Choosing a chunking strategy for RAG: an OCI PostgreSQL case study

This repo compares three chunking strategies on one real troubleshooting question, using OCI Generative AI, OCI Database with PostgreSQL and pgvector. It measures two things:

- **Evidence coverage:** did each required passage of the procedure reach the model?
- **Answer correctness:** did the answer keep each required element, and is everything it says backed by the passages it was given?

**Result:** parent-child retrieval was the only strategy that delivered the whole procedure. It produced complete, grounded answers in every run.

## The question

> OCI PostgreSQL writes are blocked by a session that is idle inside an open transaction. How do I identify the root blocker, resolve it safely, and verify recovery?

A complete answer needs six passages from procedure 5 of the guide, *Locks and long transactions*:

1. The blocked-sessions SQL
2. Why an idle session can still block
3. Asking the owner to commit or roll back
4. The approval and fresh-PID check
5. Cancel versus terminate, and what each costs
6. The recovery check

These six points break down into 16 elements that a correct answer must keep.

## Results

Recorded run, in [`postgres_blocking_comparison_verbatim.json`](postgres_blocking_comparison_verbatim.json):

- **Models:** `cohere.embed-v4.0` for embeddings, `cohere.command-a-03-2025` for answers, and `xai.grok-4.7` as the judge.
- **Settings:** chunk size 900, overlap 180, top-k 2, three runs per strategy, `verbatim` answer style.

| Strategy | Evidence supplied | Points answered from evidence | Elements kept (of 16) | Gaps | Invented | Altered | Input tokens |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Fixed + overlap | 3 of 6 | 3 | 7 | 2 | 0 | 1 | 702 |
| Recursive + overlap | 3 of 6 | 3 | 7 | 3 | 0 | 0 | 532 |
| **Parent-child + overlap** | **6 of 6** | **6** | **15–16** | **0** | **0** | **0–1** | 880 |

Ranges cover the three runs.

- **Parent-child's one 15 is a judge error.** In one run, the judge marked one element as altered, but the answer repeats the guide's sentence exactly.
- **Fixed and recursive stop at about half the procedure.** No prompt can make the model answer from evidence it never received. Most of their gaps were silent: the answer didn't say anything was missing.
- **Parent-child's cost:** 348 more input tokens per answer than recursive retrieval.

An earlier run used the `preserve` answer style, which lets the model rephrase as long as it keeps conditions. There, parent-child kept 12–13 of 16 elements, because paraphrasing dropped conditions in the termination step. Copying the guide word for word closed that gap.

## How it works

```
Word guide ──► chunks ──► OCI embeddings ──► pgvector search ──► evidence ──► OCI answer ──► scoring
```

| Strategy | How it chunks | What reaches the model |
| --- | --- | --- |
| Fixed + overlap | 900-character windows, 180 overlap, ignoring structure | Top-2 windows |
| Recursive + overlap | Splits inside each procedure at paragraphs, lines and sentences | Top-2 children |
| Parent-child + overlap | Reuses the recursive search hits | The whole procedure each hit belongs to |

**Scoring:**

- **Coverage** is checked character by character against six passages copied from the guide (`FACTS`).
- **Correctness** uses a rubric of 16 elements (`RUBRIC`). Each element is tied to a phrase in the guide, and the script stops if that phrase is missing, so the rubric can't ask for anything the guide doesn't say.
- **The judge** marks each element `present`, `altered` or `absent`, and must quote the answer. The script checks every quote and does the counting itself.
- **A grounding check** lists statements the supplied passages don't support, labelled *invented* or *altered*.
- **Each point is classified** as grounded, partial, unused, cut-off evidence, from memory, honest gap or silent gap.

## Files

| File | Purpose |
| --- | --- |
| `blog_demo.py` | The whole experiment: parsing, chunking, embedding, search, answering and scoring |
| `OCI_PostgreSQL_Troubleshooting_Guide.docx` | The knowledge source: 11 procedures |
| `requirements.txt` | Python dependencies |
| `postgres_blocking_comparison_verbatim.json` | Full report from the recorded run: answers, verdicts, quotes and supplied passages |

## Prerequisites

- Python 3.11 or newer
- An OCI Database with PostgreSQL instance with the `vector` extension enabled, and a user with `CONNECT` and `TEMP` privileges
- Network access to the database and to OCI Generative AI
- An OCI API-key profile allowed to call the models

## Setup

```bash
git clone https://github.com/oracle-devrel/oracle-ai-developer-hub.git
cd oracle-ai-developer-hub/apps/oci-postgres-rag-chunking
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Create a `.env` file next to the script. Never commit it.

```bash
OCI_COMPARTMENT_ID=ocid1.compartment.REPLACE_ME
OCI_GENAI_ENDPOINT=https://inference.generativeai.REGION.oci.oraclecloud.com
OCI_PROFILE=DEFAULT
OCI_EMBED_MODEL=cohere.embed-v4.0
OCI_CHAT_MODEL=cohere.command-a-03-2025
OCI_JUDGE_MODEL=xai.grok-4.7          # a different vendor from the answer model

PGHOST=YOUR_DATABASE_ENDPOINT_FQDN
PGPORT=5432
PGDATABASE=YOUR_DATABASE_NAME
PGUSER=YOUR_DATABASE_USER
PGPASSWORD='YOUR_DATABASE_PASSWORD'
PGSSLMODE=verify-full
PGSSLROOTCERT=/absolute/path/to/dbsystem.pub
```

The script reads the standard `PG*` variables. For a local Bastion tunnel on port 15432, keep `PGHOST` as the real endpoint, so the certificate check still works, and add:

```bash
PGHOSTADDR=127.0.0.1
PGPORT=15432
```

Model availability varies by region. Check the OCI console for the model IDs offered in yours.

## Run

```bash
# Check the guide and chunks locally (no credentials, no cloud calls)
python blog_demo.py --inspect

# Full run: coverage, 3 answers per strategy, grading
python blog_demo.py --env-file .env

# Grade a saved run again, for example with a different judge, without re-running retrieval
python blog_demo.py --env-file .env --judge-from postgres_blocking_comparison_verbatim.json
```

`--inspect` should report 11 procedures, 42 fixed chunks and 45 recursive children. The answers are saved before grading starts, so a failed judge call never costs you the run.

| Flag | Default | Meaning |
| --- | --- | --- |
| `--size` | 900 | Maximum characters per child chunk |
| `--overlap` | 180 | Overlap in characters (0 < overlap < size) |
| `--top-k` | 2 | Search hits per strategy, before parent expansion |
| `--context-limit` | 6000 | Maximum characters of evidence sent to the model |
| `--runs` | 3 | Answers generated and graded per strategy |
| `--answer-style` | `verbatim` | `verbatim` copies the guide's sentences; `preserve` rephrases but keeps conditions |
| `--output` | `postgres_blocking_comparison_<style>.json` | Report path |
| `--skip-judge` | off | Measure coverage only |
| `--judge-from` | none | Grade a saved report |
| `OCI_JUDGE_MAX_TOKENS` (env) | 4000 | Output budget for the judge, which reasoning models need |

## Caveats

- **This is one question on one guide.** Treat it as a worked example, not a benchmark.
- **An LLM judge can be wrong.** The report saves every verdict and quote. Read them before relying on the numbers.
- **Use a judge from a different vendor.** By default the judge is the answer model, which tends to grade its own phrasing generously. Set `OCI_JUDGE_MODEL` to another model.
- **Retrieval can shift when the guide changes.** After the recovery step was rewritten, recursive search returned `r016` and `r018` instead of `r015` and `r016`. Coverage stayed at 3 of 6, but with a different half of the procedure.
- **Every run re-embeds the guide.** The script uses a `TEMP` table. A production assistant should store chunks, vectors and parent links permanently, with versioning.

## Source

Contributed from [somadey123/oci-postgres-rag-chunking](https://github.com/somadey123/oci-postgres-rag-chunking).
