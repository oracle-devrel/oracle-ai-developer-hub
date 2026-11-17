"""The notebook's code as a long-lived runtime.

Every function here is the notebook's own: the same tables, SQL, SDK calls,
system prompt and models. Three differences:

* tables use the appbook's prefix (``CITYAPP_`` by default) instead of
  ``CITY_``, so the app never touches the notebook's state;
* functions take their inputs as arguments instead of reading notebook
  globals;
* each step is recorded on a :class:`~backend.core.jobs.Job`, and every LLM
  call the SDK makes internally is captured, so the page can show what
  happened inside a turn.
"""

from __future__ import annotations

import array
import asyncio
import json
import random
import time
import uuid
from collections import Counter
from types import SimpleNamespace
from typing import Any

import numpy as np
import requests
from oracleagentmemory.apis.embedders.embedder import IEmbedder
from oracleagentmemory.apis.llms.llm import ILlm
from oracleagentmemory.apis.thread import Message
from oracleagentmemory.core import OracleAgentMemory, SchemaPolicy
from oracleagentmemory.core.llms.llm import Llm

from ..config import Settings
from . import db
from .jobs import Job, JobManager

AGENT_ID = "CITY"

# The SDK's tables (it creates them) and the two domain tables (we create them).
SDK_TABLES = (
    "THREAD",
    "MESSAGE",
    "MEMORY",
    "RECORD_CHUNKS",
    "ACTOR_PROFILE",
    "ORACLEAGENTMEMORY_SCHEMA_META",
)
DOMAIN_TABLES = ("ASSET", "INSPECTION_FINDING")
# The notebook's reset order: domain tables first (FK into ASSET), then the SDK's.
DROP_ORDER = (
    "INSPECTION_FINDING",
    "ASSET",
    "MEMORY",
    "MESSAGE",
    "RECORD_CHUNKS",
    "THREAD",
    "ACTOR_PROFILE",
    "ORACLEAGENTMEMORY_SCHEMA_META",
)
RECORD_TYPES = ("fact", "preference", "guideline", "memory")

COPILOT_SYSTEM_PROMPT = """You are a CityOps inspection copilot.

Each turn you are given:
- The current inspection narrative
- The asset record (class)
- A thread context card (recent inspector messages + extracted facts/guidelines)
- Up to 3 similar past findings on the same asset (with category, severity,
  recommendation, prior inspector, prior overall grade)

Your job: suggest a likely diagnosis or characterisation; cite prior findings
with their inspector + grade + recommendation timeline; surface relevant
guidelines from the thread context. Keep responses ≤ 8 sentences.
When safety- or maintenance-critical guidelines apply, name them."""

# The notebook's handoff story, verbatim.
MERCER = "Evelyn_H_Mercer"
VANCE = "Jordan_Vance"
HANDOFF_ASSET = "Harbor Bridge"
MERCER_DAY1 = (
    "Quarterly inspection of Harbor Bridge. Surface corrosion observed on Pier 2 "
    "bearing assemblies (south side), estimated section loss ~25% on bearing plate "
    "edges with local rust bleeding onto the concrete pedestal. Corrosion extends "
    "roughly 1.5 m longitudinally along the bearing line. Standing guidance for Harbor Bridge: "
    "always remove loose corrosion products before applying inhibiting primer, and re-inspect "
    "Pier 2 bearings annually."
)
MERCER_FINDING = {
    "asset_id": HANDOFF_ASSET,
    "inspector": MERCER,
    "category": "corrosion",
    "severity": "medium",
    "description": (
        "Surface corrosion + pitting on steel bearing assemblies at Pier 2 south, "
        "~25% section loss; rust bleed onto concrete pedestal; ~1.5m longitudinal extent."
    ),
    "recommendation": (
        "Remove loose corrosion products, apply corrosion-inhibiting primer + finish "
        "coat to affected bearing assemblies within 60 days; re-inspect annually with "
        "caliper section-loss measurements."
    ),
    "overall_grade": "C",
    "days_ago": 0,
}
MERCER_FOLLOWUP = (
    "Coordinated with maintenance - recommend scheduling the bearing remediation "
    "to coincide with the deck wearing-surface resurfacing in Q3 to share access "
    "and traffic management."
)
VANCE_NARRATIVE = (
    "Reviewing Harbor Bridge as part of routine cycle. Noticing rust bleed near "
    "a pier on the south side and what looks like spalling on the concrete "
    "pedestal below."
)
HANDOFF_STEPS = ("mercer-day1", "mercer-log", "mercer-followup", "vance", "compare")

# Part 5's two demo memories, written with stable IDs so the demo can be re-run.
SCOPE_PERSONAL_ID = "scope-demo-mercer-personal"
SCOPE_CITY_ID = "scope-demo-city-guideline"
SCOPE_PERSONAL = "Remember to swap shifts with Jordan next Tuesday."
SCOPE_CITY = "On Harbor Bridge, inspect Pier 2 bearings annually - corrosion-prone since 2024."


def classify_asset(name: str) -> str:
    """The notebook's name heuristic: one of 8 asset classes."""
    n = name.lower()
    if "bridge" in n or "overpass" in n:
        return "bridge"
    if "substation" in n:
        return "substation"
    if "pipeline" in n:
        return "pipeline"
    if "water" in n or "outfall" in n or "treatment" in n:
        return "water"
    if "solar" in n or "gas distribution" in n:
        return "energy"
    if "sensor" in n or "array" in n or "monitor" in n or "gauge" in n:
        return "sensor"
    if "tower" in n or "relay" in n:
        return "comms"
    if "seawall" in n or "retaining" in n or "booster" in n:
        return "civil"
    return "other"


class OracleONNXEmbedder(IEmbedder):
    """Bridges Oracle's in-database ONNX embeddings to the SDK's IEmbedder.

    Embeddings are computed inside the database via VECTOR_EMBEDDING() using
    the loaded ONNX model. Zero text egress, no API key, no per-call cost.
    The notebook holds one connection for this; a long-running app borrows a
    pooled connection per call instead, so it survives a database restart.
    """

    def __init__(self, pool, model_name: str):
        self.pool = pool
        self.params = {"provider": "database", "model": model_name}

    def embed(self, texts: list[str], *, is_query: bool = False) -> np.ndarray:
        from langchain_oracledb.embeddings.oracleai import OracleEmbeddings

        with self.pool.acquire() as conn:
            vectors = OracleEmbeddings(conn=conn, params=self.params).embed_documents(list(texts))
        return np.asarray(vectors, dtype=np.float32)

    async def embed_async(self, texts: list[str], *, is_query: bool = False) -> np.ndarray:
        return await asyncio.to_thread(self.embed, texts, is_query=is_query)


def _purpose(prompt: Any, schema: dict | None) -> str:
    """Name an SDK-internal LLM call from what it asks for."""
    text = (
        (json.dumps(schema) if schema else "")
        + " "
        + (prompt if isinstance(prompt, str) else json.dumps(prompt))
    )
    low = text.lower()
    if "topics" in low and "summary" in low:
        return "context-card summary"
    if "guideline" in low and "preference" in low:
        return "memory extraction"
    if "summar" in low:
        return "thread summary"
    return "SDK LLM call"


class TracingLlm(ILlm):
    """The SDK's LLM, wrapped so each internal call is recorded on the running job."""

    def __init__(self, inner: Llm, jobs: JobManager):
        self.inner = inner
        self.jobs = jobs

    def _record(self, prompt, schema, text: str, started: float) -> None:
        job = self.jobs.current
        if job is not None:
            job.record_llm(
                "sdk",
                _purpose(prompt, schema),
                prompt,
                text,
                (time.perf_counter() - started) * 1000,
            )

    def generate(self, prompt, *, response_json_schema=None, **kwargs):
        started = time.perf_counter()
        resp = self.inner.generate(prompt, response_json_schema=response_json_schema, **kwargs)
        self._record(prompt, response_json_schema, resp.text, started)
        return resp

    async def generate_async(self, prompt, *, response_json_schema=None, **kwargs):
        started = time.perf_counter()
        resp = await self.inner.generate_async(
            prompt, response_json_schema=response_json_schema, **kwargs
        )
        self._record(prompt, response_json_schema, resp.text, started)
        return resp


def _result(r) -> dict:
    rec = r.record
    return {
        "id": getattr(rec, "id", None),
        "record_type": getattr(rec, "record_type", None),
        "content": getattr(rec, "content", None),
        "user_id": getattr(rec, "user_id", None),
        "agent_id": getattr(rec, "agent_id", None),
        "thread_id": getattr(rec, "thread_id", None),
        "metadata": db.plain(getattr(rec, "metadata", None)),
    }


class Lab:
    """Holds the pool, the embedder, the SDK client and the chat model."""

    def __init__(self, settings: Settings, jobs: JobManager):
        self.s = settings
        self.jobs = jobs
        self.pool = None
        self.embedder: OracleONNXEmbedder | None = None
        self.memory: OracleAgentMemory | None = None
        self.chat = None
        self.ready = False
        self.error: str | None = None
        self.handoff: dict[str, dict] = {}
        with open(settings.data_dir / "maintenance_logs.json") as f:
            self.logs: list[dict] = json.load(f)
        with open(settings.data_dir / "inspection_reports.json") as f:
            self.reports: list[dict] = json.load(f)
        names = sorted(
            {x["asset_name"] for x in self.logs} | {x["asset_name"] for x in self.reports}
        )
        self.equipment = [{"asset_id": n, "asset_class": classify_asset(n)} for n in names]

    # ------------------------------------------------------------------ setup

    def t(self, name: str) -> str:
        return f"{self.s.table_prefix}{name}"

    def start(self) -> None:
        """Connect, check the model, open the SDK and make sure the domain tables exist."""
        try:
            if not self.s.password_set:
                raise RuntimeError(
                    "No database password: set DBPASSWORD (the notebook reads the same variable)."
                )
            if self.pool is None:
                self.pool = db.create_pool(self.s)
            if not self.onnx_loaded():
                raise RuntimeError(
                    f"The ONNX model {self.s.onnx_model} is not loaded in {self.s.db_user}'s schema; "
                    "load it with DBMS_VECTOR.LOAD_ONNX_MODEL (the notebook needs it too)."
                )
            self.embedder = OracleONNXEmbedder(self.pool, self.s.onnx_model)
            self._open_sdk()
            from langchain_ollama import ChatOllama

            # Same ChatOllama setup as the notebook; temperature=0 keeps runs repeatable.
            self.chat = ChatOllama(
                model=self.s.ollama_model, base_url=self.s.ollama_base_url, temperature=0
            )
            self.ensure_domain()
            self.ready = True
            self.error = None
        except Exception as exc:
            self.ready = False
            self.error = f"{type(exc).__name__}: {exc}"

    def close(self) -> None:
        try:
            if self.pool is not None:
                self.pool.close(force=True)
        except Exception:
            pass
        self.pool = None

    def _open_sdk(self) -> None:
        # The SDK's LLM speaks LiteLLM; Ollama serves an OpenAI-compatible API at /v1.
        inner = Llm(
            model=f"openai/{self.s.ollama_model}",
            api_base=f"{self.s.ollama_base_url}/v1",
            api_key="ollama",
        )
        self.memory = OracleAgentMemory(
            connection=self.pool,
            embedder=self.embedder,
            llm=TracingLlm(inner, self.jobs),
            extract_memories=True,
            schema_policy=SchemaPolicy.CREATE_IF_NECESSARY,
            table_name_prefix=self.s.table_prefix,
        )

    def require(self) -> None:
        if not self.ready:
            raise RuntimeError(self.error or "The appbook runtime is not ready.")

    def onnx_loaded(self) -> bool:
        return bool(
            db.scalar(
                self.pool,
                "SELECT COUNT(*) FROM user_mining_models WHERE model_name = :m",
                {"m": self.s.onnx_model},
            )
        )

    def ollama_status(self) -> dict:
        url = self.s.ollama_base_url
        try:
            tags = requests.get(f"{url}/api/tags", timeout=3).json().get("models", [])
            names = [m.get("name", "") for m in tags]
            want = self.s.ollama_model
            present = any(
                n == want or n.split(":")[0] == want or n == f"{want}:latest" for n in names
            )
            return {
                "ok": present,
                "url": url,
                "model": want,
                "installed": names,
                "error": None if present else f"{want} is not pulled on this Ollama server",
            }
        except Exception as exc:
            return {
                "ok": False,
                "url": url,
                "model": self.s.ollama_model,
                "installed": [],
                "error": f"{type(exc).__name__}: {exc}",
            }

    # ------------------------------------------------------- workspace state

    def existing_tables(self) -> list[str]:
        names = [self.t(n) for n in DROP_ORDER]
        rows = db.query(
            self.pool,
            "SELECT table_name FROM user_tables WHERE table_name IN ("
            + ",".join(f":n{i}" for i in range(len(names)))
            + ")",
            {f"n{i}": n for i, n in enumerate(names)},
        )
        return [r["table_name"] for r in rows]

    def table_counts(self) -> dict[str, int]:
        counts = {}
        for name in self.existing_tables():
            counts[name] = int(db.scalar(self.pool, f'SELECT COUNT(*) FROM "{name}"'))
        return counts

    def deltas_since(self, before: dict[str, int]) -> dict[str, int]:
        after = self.table_counts()
        return {
            k: after.get(k, 0) - before.get(k, 0)
            for k in after
            if after.get(k, 0) != before.get(k, 0)
        }

    def max_seq(self, table: str) -> int:
        return int(
            db.scalar(self.pool, f'SELECT NVL(MAX(order_seq), 0) FROM "{self.t(table)}"') or 0
        )

    def reset(self, job: Job) -> dict:
        """Drop every table under the appbook's prefix, then rebuild and reseed."""
        job.begin("drop", "Drop the appbook's tables")
        dropped = []
        with self.pool.acquire() as conn, conn.cursor() as cur:
            for name in DROP_ORDER:
                table = self.t(name)
                try:
                    cur.execute(f'DROP TABLE "{table}" CASCADE CONSTRAINTS PURGE')
                    dropped.append(table)
                except Exception:
                    pass  # table didn't exist - fine
            conn.commit()
        job.end("drop", {"dropped": dropped}, detail=f"{len(dropped)} tables dropped")
        job.begin("sdk", "Re-open the SDK (it re-creates its tables)")
        self._open_sdk()
        job.end("sdk", {"tables": [self.t(n) for n in SDK_TABLES]})
        job.begin("domain", "Re-create and reload the domain tables")
        info = self.ensure_domain()
        job.end("domain", info, detail=f"{info['assets']} assets, {info['findings']} findings")
        self.handoff.clear()
        return {"dropped": dropped, **info}

    # ------------------------------------------------------- Part 3: assets

    def ensure_domain(self) -> dict:
        if not db.table_exists(self.pool, self.t("ASSET")):
            self.create_asset_table()
        if not db.table_exists(self.pool, self.t("INSPECTION_FINDING")):
            self.create_findings_table()
            self.seed_findings(self.s.demo_finding_count)
        return {
            "assets": int(db.scalar(self.pool, f'SELECT COUNT(*) FROM "{self.t("ASSET")}"')),
            "findings": int(
                db.scalar(self.pool, f'SELECT COUNT(*) FROM "{self.t("INSPECTION_FINDING")}"')
            ),
        }

    def create_asset_table(self) -> None:
        with self.pool.acquire() as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                CREATE TABLE {self.t("ASSET")} (
                    asset_id     VARCHAR2(128) PRIMARY KEY,
                    asset_class  VARCHAR2(32) NOT NULL,
                    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            cur.executemany(
                f"INSERT INTO {self.t('ASSET')} (asset_id, asset_class) VALUES (:1, :2)",
                [(e["asset_id"], e["asset_class"]) for e in self.equipment],
            )
            conn.commit()

    def get_asset(self, asset_id: str) -> dict | None:
        rows = db.query(
            self.pool,
            f"SELECT asset_id, asset_class FROM {self.t('ASSET')} WHERE asset_id = :id",
            {"id": asset_id},
        )
        return rows[0] if rows else None

    def assets(self) -> list[dict]:
        logs = Counter(x["asset_name"] for x in self.logs)
        reports = Counter(x["asset_name"] for x in self.reports)
        rows = db.query(
            self.pool,
            f"""
            SELECT a.asset_id, a.asset_class, COUNT(f.finding_id) AS findings
              FROM {self.t('ASSET')} a LEFT JOIN {self.t('INSPECTION_FINDING')} f ON f.asset_id = a.asset_id
             GROUP BY a.asset_id, a.asset_class ORDER BY a.asset_id""",
        )
        for r in rows:
            r["findings"] = int(r["findings"])
            r["narratives"] = logs.get(r["asset_id"], 0)
            r["reports"] = reports.get(r["asset_id"], 0)
        return rows

    # ----------------------------------------- Part 3: memory + extraction

    def _thread(self, thread_id: str):
        try:
            return self.memory.get_thread(thread_id)
        except Exception:
            return None

    async def report_event(
        self, asset_id: str, inspector: str, narrative: str, thread_id: str
    ) -> list:
        """Persist a maintenance event narrative and trigger SDK auto-extraction."""
        t = self._thread(thread_id)
        if t is None:
            t = self.memory.create_thread(
                user_id=inspector,
                thread_id=thread_id,
                agent_id=AGENT_ID,
                # Keep a rolling <=2-sentence thread summary, refreshed every 2 messages.
                enable_context_summary=True,
                context_summary_update_frequency=2,
            )
        content = f"[Asset: {asset_id}] [Inspector: {inspector}] {narrative}"
        return await t.add_messages_async([Message(role="user", content=content)])

    async def run_report_event(
        self, job: Job, asset_id: str, inspector: str, narrative: str, thread_id: str
    ) -> dict:
        """report_event with the before/after view the page shows."""
        self.require()
        before = self.table_counts()
        mem_seq, msg_seq = self.max_seq("MEMORY"), self.max_seq("MESSAGE")
        job.begin(
            "write",
            "add_messages(): store the narrative and run the extractor",
            detail=f"thread {thread_id} · user_id {inspector}",
        )
        ids = await self.report_event(asset_id, inspector, narrative, thread_id)
        job.end("write", {"message_ids": ids})
        job.begin("diff", "Read back what was persisted")
        new = {
            "messages": self.rows_after("MESSAGE", msg_seq),
            "memories": self.rows_after("MEMORY", mem_seq),
        }
        deltas = self.deltas_since(before)
        job.add_deltas(deltas)
        job.end(
            "diff",
            new,
            detail=f"{len(new['messages'])} message(s), {len(new['memories'])} memory record(s)",
        )
        return {
            "thread_id": thread_id,
            "user_id": inspector,
            "message_ids": ids,
            **new,
            "deltas": deltas,
        }

    def sample_narratives(self, n: int) -> list[dict]:
        """The notebook's stratified sample: a mix of severities, multiple assets."""
        rng = random.Random(42)  # same sequence as random.seed(42) in the notebook
        buckets: dict[str, list] = {"routine": [], "warning": [], "critical": []}
        for log in self.logs:
            buckets.get(log["severity"], []).append(log)
        n_routine, n_warning, n_critical = (
            max(1, n // 2),
            max(1, n // 3),
            max(1, n - n // 2 - n // 3),
        )
        picks = (
            rng.sample(buckets["routine"], min(n_routine, len(buckets["routine"])))
            + rng.sample(buckets["warning"], min(n_warning, len(buckets["warning"])))
            + rng.sample(buckets["critical"], min(n_critical, len(buckets["critical"])))
        )
        return picks[:n]

    async def run_extraction_demo(self, job: Job, n: int) -> dict:
        """Part 3's loop: report n sampled narratives as inspector_demo on thread inspect_demo."""
        self.require()
        picks = self.sample_narratives(n)
        before = self.table_counts()
        mem_seq = self.max_seq("MEMORY")
        for i, narr in enumerate(picks, 1):
            key = f"n{i}"
            job.begin(
                key, f"Narrative {i} of {len(picks)} · {narr['asset_name']} [{narr['severity']}]"
            )
            seq = self.max_seq("MEMORY")
            await self.report_event(
                narr["asset_name"], "inspector_demo", narr["narrative"], "inspect_demo"
            )
            got = self.rows_after("MEMORY", seq)
            job.end(
                key, {"narrative": narr, "memories": got}, detail=f"{len(got)} record(s) extracted"
            )
        deltas = self.deltas_since(before)
        job.add_deltas(deltas)
        return {
            "narratives": picks,
            "memories": self.rows_after("MEMORY", mem_seq),
            "deltas": deltas,
        }

    def rows_after(self, table: str, seq: int) -> list[dict]:
        if table == "MESSAGE":
            sql = f"""SELECT order_seq, record_id, thread_id, user_id, agent_id, message_role AS role, content,
                             TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') AS created
                        FROM {self.t('MESSAGE')} WHERE order_seq > :s ORDER BY order_seq"""
        else:
            sql = f"""SELECT order_seq, record_id, thread_id, user_id, agent_id, memory_type, content, metadata,
                             TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') AS created
                        FROM {self.t('MEMORY')} WHERE order_seq > :s ORDER BY order_seq"""
        return [db.plain(self._meta(r)) for r in db.query(self.pool, sql, {"s": seq})]

    @staticmethod
    def _meta(row: dict) -> dict:
        if "metadata" in row:
            meta = db.parse_json(row["metadata"]) or {}
            row["metadata"] = meta
            if isinstance(meta, dict):
                row["importance"] = meta.get("importance")
                row["valid_to"] = meta.get("valid_to")
        return row

    def view_memories(
        self, user_id=None, record_type=None, thread_id=None, newest_first=True, limit=50
    ) -> list[dict]:
        """Read-only view of the SDK's append-only memory log (the notebook's view_memories)."""
        where, binds = [], {}
        if user_id is not None:
            where.append("user_id = :usr")
            binds["usr"] = user_id
        if record_type is not None:
            where.append("memory_type = :mtype")
            binds["mtype"] = record_type
        if thread_id is not None:
            where.append("thread_id = :tid")
            binds["tid"] = thread_id
        clause = ("WHERE " + " AND ".join(where)) if where else ""
        order = "DESC" if newest_first else "ASC"
        binds["lim"] = limit
        rows = db.query(
            self.pool,
            f"""
            SELECT order_seq,
                   TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI') AS created,
                   memory_type, user_id, thread_id, agent_id, record_id, content, metadata
              FROM {self.t('MEMORY')}
              {clause}
             ORDER BY order_seq {order}
             FETCH FIRST :lim ROWS ONLY""",
            binds,
        )
        return [db.plain(self._meta(r)) for r in rows]

    def messages(self, thread_id: str | None = None, limit: int = 100) -> list[dict]:
        where = "WHERE thread_id = :tid" if thread_id else ""
        binds = {"tid": thread_id, "lim": limit} if thread_id else {"lim": limit}
        rows = db.query(
            self.pool,
            f"""
            SELECT order_seq, thread_id, user_id, agent_id, message_role AS role, content,
                   TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI') AS created
              FROM {self.t('MESSAGE')} {where}
             ORDER BY order_seq DESC FETCH FIRST :lim ROWS ONLY""",
            binds,
        )
        return [db.plain(r) for r in rows]

    def threads(self) -> list[dict]:
        rows = db.query(
            self.pool,
            f"""
            SELECT t.record_id AS thread_id, t.user_id, t.agent_id,
                   (SELECT COUNT(*) FROM {self.t('MESSAGE')} m WHERE m.thread_id = t.record_id) AS messages,
                   (SELECT COUNT(*) FROM {self.t('MEMORY')} r WHERE r.thread_id = t.record_id) AS memories,
                   TO_CHAR(t.created_at, 'YYYY-MM-DD HH24:MI') AS created
              FROM {self.t('THREAD')} t ORDER BY t.created_at""",
        )
        return [db.plain(r) for r in rows]

    async def search(
        self,
        query: str,
        *,
        user_id,
        agent_id=None,
        thread_id=None,
        exact_thread_match=None,
        record_types=None,
        max_results=10,
    ) -> dict:
        """memory.search_async with the scope spelled out, as the page shows it."""
        self.require()
        kwargs: dict[str, Any] = {"user_id": user_id, "max_results": max_results}
        if agent_id is not None:
            kwargs["agent_id"] = agent_id
        if thread_id is not None:
            kwargs["thread_id"] = thread_id
        if exact_thread_match is not None:
            kwargs["exact_thread_match"] = exact_thread_match
        if record_types:
            kwargs["record_types"] = list(record_types)
        started = time.perf_counter()
        results = await self.memory.search_async(query=query, **kwargs)
        return {
            "query": query,
            "call": kwargs,
            "results": [_result(r) for r in results],
            "ms": round((time.perf_counter() - started) * 1000),
        }

    # --------------------------------------------- Part 2: the embedder

    def embed_preview(self, texts: list[str]) -> dict:
        self.require()
        started = time.perf_counter()
        vecs = self.embedder.embed(texts)
        ms = round((time.perf_counter() - started) * 1000)
        norms = np.linalg.norm(vecs, axis=1)
        unit = vecs / np.where(norms[:, None] == 0, 1, norms[:, None])
        dist = 1 - unit @ unit.T  # cosine distance, what VECTOR_DISTANCE(..., COSINE) returns
        return {
            "model": self.s.onnx_model,
            "shape": list(vecs.shape),
            "dtype": str(vecs.dtype),
            "ms": ms,
            "vectors": [[round(float(x), 4) for x in v] for v in vecs],
            "norms": [round(float(n), 4) for n in norms],
            "distances": [[round(float(x), 4) for x in row] for row in dist],
            "sql": f"SELECT VECTOR_EMBEDDING({self.s.onnx_model} USING :text AS data) FROM dual",
        }

    # ---------------------------------- Part 4: findings + vector search

    def create_findings_table(self) -> None:
        with self.pool.acquire() as conn, conn.cursor() as cur:
            # Constraint and index names are schema-wide, so they carry the prefix too.
            cur.execute(
                f"""
                CREATE TABLE {self.t("INSPECTION_FINDING")} (
                    finding_id      VARCHAR2(64) PRIMARY KEY,
                    asset_id        VARCHAR2(128) NOT NULL,
                    inspector       VARCHAR2(128),
                    overall_grade   VARCHAR2(2),
                    category        VARCHAR2(32),
                    severity        VARCHAR2(16),
                    description     CLOB NOT NULL,
                    recommendation  CLOB,
                    days_ago        NUMBER,
                    embedding       VECTOR(384) NOT NULL,
                    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT {self.t("FK_FINDING_ASSET")} FOREIGN KEY (asset_id) REFERENCES {self.t("ASSET")}(asset_id)
                )
            """
            )
            try:
                cur.execute(
                    f"""
                    CREATE VECTOR INDEX {self.t("FINDING_EMB_IDX")}
                    ON {self.t("INSPECTION_FINDING")} (embedding)
                    ORGANIZATION INMEMORY NEIGHBOR GRAPH
                    DISTANCE COSINE
                    WITH TARGET ACCURACY 95
                    PARAMETERS (TYPE HNSW, M 16, EFCONSTRUCTION 200)
                """
                )
            except Exception:
                pass  # the notebook skips the HNSW index too when the vector pool is unavailable
            conn.commit()

    def has_hnsw_index(self) -> bool:
        return bool(
            db.scalar(
                self.pool,
                "SELECT COUNT(*) FROM user_indexes WHERE index_name = :n",
                {"n": self.t("FINDING_EMB_IDX")},
            )
        )

    def _dataset_findings(self):
        for report in self.reports:
            for finding in report["findings"]:
                yield report, finding

    def seed_findings(self, limit: int | None) -> int:
        """Embed and insert dataset findings that are not loaded yet (the notebook loads the first N)."""
        loaded = {
            r["description"]
            for r in db.query(
                self.pool,
                f"SELECT description FROM {self.t('INSPECTION_FINDING')} WHERE inspector NOT IN (:a, :b)",
                {"a": MERCER, "b": "checkpoint_test"},
            )
        }
        rows = []
        for i, (report, finding) in enumerate(self._dataset_findings()):
            if limit is not None and i >= limit:
                break
            if finding["description"] in loaded:
                continue
            rows.append(
                {
                    "finding_id": str(uuid.uuid4())[:12],
                    "asset_id": report["asset_name"],
                    "inspector": report["inspector"],
                    "overall_grade": report["overall_grade"],
                    "category": finding["category"],
                    "severity": finding["severity"],
                    "description": finding["description"],
                    "recommendation": finding["recommendation"],
                    "days_ago": report["days_ago"],
                }
            )
        for start in range(0, len(rows), 32):
            batch = rows[start : start + 32]
            vecs = self.embedder.embed([r["description"] for r in batch])
            for r, v in zip(batch, vecs, strict=False):
                r["embedding"] = array.array("f", v.tolist())
        if rows:
            with self.pool.acquire() as conn, conn.cursor() as cur:
                cur.executemany(
                    f"""
                    INSERT INTO {self.t('INSPECTION_FINDING')}
                      (finding_id, asset_id, inspector, overall_grade, category, severity,
                       description, recommendation, days_ago, embedding)
                    VALUES (:finding_id, :asset_id, :inspector, :overall_grade, :category, :severity,
                            :description, :recommendation, :days_ago, :embedding)""",
                    rows,
                )
                conn.commit()
        return len(rows)

    def dataset_finding_total(self) -> int:
        return sum(len(r["findings"]) for r in self.reports)

    def log_finding(
        self,
        asset_id: str,
        inspector: str,
        category: str,
        severity: str,
        description: str,
        recommendation: str = "",
        overall_grade: str | None = None,
        days_ago: int = 0,
    ) -> str:
        """Persist a new inspection finding (the deliberate write path)."""
        self.require()
        finding_id = str(uuid.uuid4())[:12]
        vec = array.array("f", self.embedder.embed([description])[0].tolist())
        with self.pool.acquire() as conn, conn.cursor() as cur:
            cur.execute(
                f"""INSERT INTO {self.t('INSPECTION_FINDING')}
                     (finding_id, asset_id, inspector, overall_grade, category, severity,
                      description, recommendation, days_ago, embedding)
                   VALUES (:finding_id, :asset_id, :inspector, :overall_grade, :category, :severity,
                           :description, :recommendation, :days_ago, :embedding)""",
                finding_id=finding_id,
                asset_id=asset_id,
                inspector=inspector,
                overall_grade=overall_grade,
                category=category,
                severity=severity,
                description=description,
                recommendation=recommendation,
                days_ago=days_ago,
                embedding=vec,
            )
            conn.commit()
        return finding_id

    def similar_sql(self) -> str:
        return f"""SELECT finding_id, asset_id, inspector, overall_grade, category, severity,
       description, recommendation, days_ago,
       VECTOR_DISTANCE(embedding, :q, COSINE) AS score
  FROM {self.t('INSPECTION_FINDING')}
 WHERE (:asset_id IS NULL OR asset_id = :asset_id)
   AND (:category IS NULL OR category = :category)
 ORDER BY score
 FETCH FIRST :k ROWS ONLY"""

    def find_similar_findings(
        self, description: str, asset_id: str | None = None, category: str | None = None, k: int = 3
    ) -> list[dict]:
        """Vector-search the findings, optionally narrowed to one asset and/or category."""
        query_vec = array.array("f", self.embedder.embed([description])[0].tolist())
        with self.pool.acquire() as conn, conn.cursor() as cur:
            cur.execute(self.similar_sql(), q=query_vec, asset_id=asset_id, category=category, k=k)
            cols = [d[0].lower() for d in cur.description]
            rows = []
            for r in cur.fetchall():
                row = dict(zip(cols, r, strict=False))
                for key in ("description", "recommendation"):
                    v = row.get(key)
                    if v is not None and hasattr(v, "read"):
                        row[key] = v.read()
                rows.append(db.plain(row))
        return rows

    def findings_summary(self) -> dict:
        rows = db.query(
            self.pool,
            f"SELECT category, COUNT(*) AS n FROM {self.t('INSPECTION_FINDING')} GROUP BY category ORDER BY 2 DESC",
        )
        logged = db.query(
            self.pool,
            f"""SELECT finding_id, asset_id, inspector, category, severity, overall_grade,
                                                description, recommendation, TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI') AS created
                                           FROM {self.t('INSPECTION_FINDING')} WHERE days_ago = 0
                                          ORDER BY created_at DESC FETCH FIRST 20 ROWS ONLY""",
        )
        total = sum(int(r["n"]) for r in rows)
        return {
            "total": total,
            "dataset_total": self.dataset_finding_total(),
            "by_category": [{"category": r["category"], "n": int(r["n"])} for r in rows],
            "logged": [db.plain(r) for r in logged],
            "hnsw": self.has_hnsw_index(),
            "categories": sorted({f["category"] for _, f in self._dataset_findings()}),
        }

    # ------------------------------------------------- Part 5: scoping

    def _memory_exists(self, record_id: str) -> bool:
        return bool(
            db.scalar(
                self.pool,
                f"SELECT COUNT(*) FROM {self.t('MEMORY')} WHERE record_id = :r",
                {"r": record_id},
            )
        )

    async def run_scoping_demo(self, job: Job) -> dict:
        self.require()
        before = self.table_counts()
        job.begin("write", "Mercer writes one personal note and one city-wide guideline")
        wrote = []
        if not self._memory_exists(SCOPE_PERSONAL_ID):
            # Inspector Mercer writes a personal note (user-scoped, invisible to others)
            self.memory.add_memory(
                content=SCOPE_PERSONAL, user_id=MERCER, memory_id=SCOPE_PERSONAL_ID
            )
            wrote.append("personal")
        if not self._memory_exists(SCOPE_CITY_ID):
            # Mercer also writes a city-wide tribal-knowledge guideline (agent-scoped)
            self.memory.add_memory(content=SCOPE_CITY, agent_id=AGENT_ID, memory_id=SCOPE_CITY_ID)
            wrote.append("city")
        job.end(
            "write",
            {
                "personal": {"content": SCOPE_PERSONAL, "user_id": MERCER, "agent_id": None},
                "city": {"content": SCOPE_CITY, "user_id": None, "agent_id": AGENT_ID},
                "written_now": wrote,
            },
            detail="already there from an earlier run"
            if not wrote
            else f"wrote {', '.join(wrote)}",
        )
        job.begin("personal", "Vance searches at his own user scope for 'shift swap notes'")
        personal = await self.search(
            "shift swap notes", user_id=VANCE, record_types=["memory"], max_results=10
        )
        job.end("personal", personal, detail=f"{len(personal['results'])} hit(s) (should be 0)")
        job.begin("city", "Vance searches at city scope for 'Harbor Bridge Pier 2 bearings'")
        city = await self.search(
            "Harbor Bridge Pier 2 bearings",
            user_id=None,
            agent_id=AGENT_ID,
            record_types=["memory"],
            max_results=10,
        )
        job.end("city", city, detail=f"{len(city['results'])} hit(s) (should be ≥ 1)")
        job.begin("mercer", "Mercer searches at her own user scope for the same note")
        mercer = await self.search(
            "shift swap notes", user_id=MERCER, record_types=["memory"], max_results=10
        )
        job.end("mercer", mercer, detail=f"{len(mercer['results'])} hit(s)")
        no_leak = all("shift swap" not in (r["content"] or "").lower() for r in personal["results"])
        city_ok = any("Pier 2" in (r["content"] or "") for r in city["results"])
        job.add_deltas(self.deltas_since(before))
        return {
            "personal": personal,
            "city": city,
            "mercer": mercer,
            "checks": {"no_leak": no_leak, "city_visible": city_ok},
        }

    # ------------------------------------------- Part 6: the copilot turn

    COPILOT_STEPS = [
        ("thread", "1 · Resolve this inspector's private thread"),
        ("asset", "2 · Look up the asset record"),
        ("card", "3 · Build the context card (this thread)"),
        ("similar", "4 · Find similar past findings (vector SQL)"),
        ("pooled", "4b · Search the asset's pooled memory"),
        ("prompt", "5 · Assemble the prompt"),
        ("answer", "6 · Ask the agent LLM"),
        ("persist", "7 · Persist the turn: add_messages()"),
        ("learned", "8 · What memory learned from this turn"),
    ]

    async def call_copilot(
        self, job: Job, narrative: str, inspector_id: str, asset_id: str
    ) -> dict:
        """End-to-end CityOps copilot turn: build context, query LLM, persist.

        Scoping: each inspector gets a PRIVATE per-asset thread (asset_id::inspector_id),
        so raw turns stay between that inspector and the copilot. But every thread for an
        asset shares user_id=asset_id, so the SDK's auto-extracted facts/guidelines pool
        per asset - retrieved in step 4b via a thread-relaxed memory.search_async.
        """
        self.require()
        before = self.table_counts()
        mem_seq, msg_seq = self.max_seq("MEMORY"), self.max_seq("MESSAGE")

        # 1. Resolve this inspector's PRIVATE per-asset thread (get-or-create).
        job.begin("thread")
        thread_id = f"{asset_id}::{inspector_id}"
        t = self._thread(thread_id)
        created = t is None
        if t is None:
            t = self.memory.create_thread(
                user_id=asset_id,  # the ASSET is the memory principal (shared facts/guidelines)
                thread_id=thread_id,
                agent_id=AGENT_ID,
                enable_context_summary=True,
                context_summary_update_frequency=2,
            )
        job.end(
            "thread",
            {"thread_id": thread_id, "user_id": asset_id, "agent_id": AGENT_ID, "created": created},
            detail=("new thread" if created else "existing thread") + f" {thread_id}",
        )

        # 2. Asset record - straight SQL lookup.
        job.begin("asset")
        asset = self.get_asset(asset_id)
        asset_info = (
            f"Asset {asset['asset_id']} (class: {asset['asset_class']})"
            if asset
            else "(no asset record found)"
        )
        job.end(
            "asset",
            {
                "asset": asset,
                "sql": f"SELECT asset_id, asset_class FROM {self.t('ASSET')} WHERE asset_id = :id",
            },
            detail=asset_info,
        )

        # 3. Context card (thread state + extracted facts/guidelines).
        job.begin("card")
        card = await t.get_context_card_async(
            fallback_message_count=100, max_recent_messages=10, max_relevant_results=8
        )
        card_text = getattr(card, "formatted_content", None) or getattr(card, "content", "") or ""
        job.end(
            "card",
            {"xml": card_text, "chars": len(card_text)},
            detail=f"{len(card_text)} characters of XML"
            if card_text
            else "empty: first turn on this thread",
        )

        # 4. Similar past findings on this asset.
        job.begin("similar")
        similar = self.find_similar_findings(narrative, asset_id=asset_id, k=3)
        if similar:
            similar_text = "\n\n".join(
                f"  (score={r['score']:.3f})  [{r['category']}/{r['severity']}]  "
                f"inspector={r['inspector']}, grade={r['overall_grade']}, days_ago={r['days_ago']}\n"
                f"     description: {r['description']}\n"
                f"     recommendation: {r['recommendation']}"
                for r in similar
            )
        else:
            similar_text = "  (no prior findings for this asset)"
        job.end(
            "similar",
            {
                "rows": similar,
                "sql": self.similar_sql(),
                "binds": {"asset_id": asset_id, "category": None, "k": 3},
            },
            detail=f"{len(similar)} finding(s)",
        )

        # 4b. Asset-pooled memory - facts/guidelines other inspectors left on THIS asset.
        #     Thread-relaxed search on the shared user_id=asset_id; record_types excludes raw messages.
        job.begin("pooled")
        pooled = await self.memory.search_async(
            query=narrative,
            user_id=asset_id,
            agent_id=AGENT_ID,
            exact_thread_match=False,
            record_types=["fact", "guideline", "memory"],
            max_results=3,
        )
        if pooled:
            pooled_text = "\n".join(
                f"  - [{r.record.record_type}] {r.record.content}" for r in pooled
            )
        else:
            pooled_text = "  (no prior memory for this asset)"
        job.end(
            "pooled",
            {
                "results": [_result(r) for r in pooled],
                "call": {
                    "user_id": asset_id,
                    "agent_id": AGENT_ID,
                    "exact_thread_match": False,
                    "record_types": ["fact", "guideline", "memory"],
                    "max_results": 3,
                },
            },
            detail=f"{len(pooled)} record(s)",
        )

        # 5. Assemble the context string.
        job.begin("prompt")
        context = (
            f"# Current inspection narrative\n"
            f"Asset: {asset_id}\n"
            f"Inspector: {inspector_id}\n"
            f"Narrative: {narrative}\n\n"
            f"# Asset record\n{asset_info}\n\n"
            f"# Thread context\n{card_text}\n\n"
            f"# Relevant memory from prior inspections on this asset\n{pooled_text}\n\n"
            f"# Similar past findings (from {self.t('INSPECTION_FINDING')})\n{similar_text}"
        )
        messages = [
            {"role": "system", "content": COPILOT_SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ]
        sections = {
            "narrative": f"Asset: {asset_id}\nInspector: {inspector_id}\nNarrative: {narrative}",
            "asset": asset_info,
            "card": card_text,
            "pooled": pooled_text,
            "similar": similar_text,
        }
        job.end(
            "prompt",
            {"system": COPILOT_SYSTEM_PROMPT, "user": context, "sections": sections},
            detail=f"{len(context)} characters",
        )

        # 6. LLM call.
        job.begin("answer", detail=f"{self.s.ollama_model} via Ollama")
        answer = await self.ask(job, messages, purpose="copilot answer")
        job.end("answer", {"answer": answer})

        # 7. Persist - both messages trigger SDK auto-extraction.
        job.begin("persist", detail="the SDK stores both messages, then runs its extractor")
        ids = await t.add_messages_async(
            [
                Message(role="user", content=f"[{inspector_id} @ {asset_id}] {narrative}"),
                Message(role="assistant", content=answer),
            ]
        )
        job.end(
            "persist",
            {"message_ids": ids, "messages": self.rows_after("MESSAGE", msg_seq)},
            detail=f"{len(ids)} message(s) written",
        )

        # 8. What the extractor distilled (it ran inside add_messages).
        job.begin("learned")
        learned = self.rows_after("MEMORY", mem_seq)
        deltas = self.deltas_since(before)
        job.add_deltas(deltas)
        job.end(
            "learned",
            {"memories": learned, "deltas": deltas},
            detail=f"{len(learned)} new memory record(s)",
        )
        return {
            "answer": answer,
            "thread_id": thread_id,
            "inspector_id": inspector_id,
            "asset_id": asset_id,
            "similar": similar,
            "pooled": [_result(r) for r in pooled],
            "learned": learned,
            "deltas": deltas,
        }

    async def ask(self, job: Job | None, messages: list[dict], purpose: str) -> str:
        """The notebook's call_ollama_chat: one chat call to the local model."""
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        role_to_cls = {"system": SystemMessage, "user": HumanMessage, "assistant": AIMessage}
        lc_msgs = [role_to_cls[m["role"]](content=m["content"]) for m in messages]
        started = time.perf_counter()
        resp = await self.chat.ainvoke(lc_msgs)
        resp = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=resp.content))]
        )
        answer = resp.choices[0].message.content or ""
        if job is not None:
            job.record_llm(
                "agent", purpose, messages, answer, (time.perf_counter() - started) * 1000
            )
        return answer

    async def stateless(self, job: Job, narrative: str) -> dict:
        """The same narrative with no memory layers at all: just the LLM."""
        self.require()
        job.begin("answer", "Ask the LLM with no thread, card, pooled memory or findings")
        stateless_messages = [
            {"role": "system", "content": COPILOT_SYSTEM_PROMPT},
            {"role": "user", "content": narrative},
        ]
        answer = await self.ask(job, stateless_messages, purpose="stateless answer")
        job.end("answer", {"answer": answer, "user": narrative})
        return {"answer": answer, "narrative": narrative}

    # ------------------------------------------- the handoff story

    def handoff_state(self) -> dict:
        state = {}
        mercer_findings = 0
        if self.ready:
            mercer_findings = int(
                db.scalar(
                    self.pool,
                    f"SELECT COUNT(*) FROM {self.t('INSPECTION_FINDING')} WHERE inspector = :i",
                    {"i": MERCER},
                )
                or 0
            )
        for step in HANDOFF_STEPS:
            state[step] = self.handoff.get(step)
        return {
            "steps": state,
            "mercer_findings": mercer_findings,
            "narratives": {
                "mercer-day1": MERCER_DAY1,
                "mercer-followup": MERCER_FOLLOWUP,
                "vance": VANCE_NARRATIVE,
            },
            "finding": MERCER_FINDING,
            "asset": HANDOFF_ASSET,
            "mercer": MERCER,
            "vance": VANCE,
        }

    async def run_handoff(self, job: Job, step: str) -> dict:
        self.require()
        if step == "mercer-day1":
            out = await self.call_copilot(job, MERCER_DAY1, MERCER, HANDOFF_ASSET)
        elif step == "mercer-log":
            before = self.table_counts()
            job.begin("log", "log_finding(): Mercer records the structured finding")
            fid = self.log_finding(**MERCER_FINDING)
            job.end("log", {"finding_id": fid, **MERCER_FINDING}, detail=f"finding {fid}")
            deltas = self.deltas_since(before)
            job.add_deltas(deltas)
            out = {"finding_id": fid, "finding": MERCER_FINDING, "deltas": deltas}
        elif step == "mercer-followup":
            out = await self.call_copilot(job, MERCER_FOLLOWUP, MERCER, HANDOFF_ASSET)
        elif step == "vance":
            out = await self.call_copilot(job, VANCE_NARRATIVE, VANCE, HANDOFF_ASSET)
        elif step == "compare":
            out = await self.stateless(job, VANCE_NARRATIVE)
            out["with_memory"] = (self.handoff.get("vance") or {}).get("answer")
        else:
            raise ValueError(f"unknown handoff step {step!r}")
        self.handoff[step] = {**out, "job_id": job.id, "at": time.time()}
        return out
