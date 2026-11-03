"""Background jobs with a step log the browser polls.

Every action that calls a model (extraction, the copilot, the handoff story)
runs as a job. Jobs run one at a time, because the notebook's flow is
sequential and one local Ollama model serves every call. The page polls
``GET api/jobs/{id}``, so a job keeps running, and can be picked up again,
when you leave the page.
"""

from __future__ import annotations

import asyncio
import time
import traceback
import uuid
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from typing import Any

PROMPT_CHAR_LIMIT = 20_000
KEEP_JOBS = 60


def _now_ms() -> float:
    return time.perf_counter() * 1000


class Job:
    def __init__(self, kind: str, title: str, steps: list[tuple[str, str]] | None = None):
        self.id = uuid.uuid4().hex[:12]
        self.kind = kind
        self.title = title
        self.status = "queued"
        self.created = time.time()
        self.started: float | None = None
        self.finished: float | None = None
        self.steps: list[dict] = [self._new_step(k, t) for k, t in (steps or [])]
        self.llm_calls: list[dict] = []
        self.deltas: dict[str, int] = {}
        self.result: Any = None
        self.error: str | None = None
        self._step_started: dict[str, float] = {}
        self._active_step: str | None = None

    @staticmethod
    def _new_step(key: str, title: str) -> dict:
        return {
            "key": key,
            "title": title,
            "status": "pending",
            "ms": None,
            "detail": "",
            "data": None,
        }

    def _step(self, key: str, title: str | None = None) -> dict:
        for step in self.steps:
            if step["key"] == key:
                if title:
                    step["title"] = title
                return step
        step = self._new_step(key, title or key)
        self.steps.append(step)
        return step

    def begin(self, key: str, title: str | None = None, detail: str = "") -> None:
        step = self._step(key, title)
        step["status"] = "running"
        step["detail"] = detail
        self._step_started[key] = _now_ms()
        self._active_step = key

    def end(
        self, key: str, data: Any = None, detail: str | None = None, status: str = "done"
    ) -> None:
        step = self._step(key)
        step["status"] = status
        started = self._step_started.get(key)
        step["ms"] = round(_now_ms() - started) if started else None
        if data is not None:
            step["data"] = data
        if detail is not None:
            step["detail"] = detail
        if self._active_step == key:
            self._active_step = None

    def skip(self, key: str, detail: str) -> None:
        step = self._step(key)
        step["status"] = "skipped"
        step["detail"] = detail

    def record_llm(self, who: str, purpose: str, prompt: Any, response: str, ms: float) -> None:
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = [
                {"role": m.get("role", "user"), "content": str(m.get("content", ""))}
                for m in prompt
            ]
        for m in messages:
            if len(m["content"]) > PROMPT_CHAR_LIMIT:
                m["content"] = (
                    m["content"][:PROMPT_CHAR_LIMIT]
                    + f"\n… ({len(m['content']) - PROMPT_CHAR_LIMIT} more characters)"
                )
        self.llm_calls.append(
            {
                "who": who,
                "purpose": purpose,
                "step": self._active_step,
                "messages": messages,
                "response": response,
                "ms": round(ms),
            }
        )

    def add_deltas(self, deltas: dict[str, int]) -> None:
        for table, n in deltas.items():
            if n:
                self.deltas[table] = self.deltas.get(table, 0) + n

    def to_dict(self) -> dict:
        end = self.finished or time.time()
        return {
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "status": self.status,
            "created": self.created,
            "seconds": round(end - self.started, 1) if self.started else 0,
            "steps": self.steps,
            "llm_calls": self.llm_calls,
            "deltas": self.deltas,
            "result": self.result,
            "error": self.error,
        }

    def summary(self) -> dict:
        return {"id": self.id, "kind": self.kind, "title": self.title, "status": self.status}


class JobManager:
    def __init__(self) -> None:
        self._jobs: OrderedDict[str, Job] = OrderedDict()
        self._lock = asyncio.Lock()
        self.current: Job | None = None  # read by the LLM wrapper to attribute calls

    def submit(self, job: Job, work: Callable[[Job], Awaitable[Any]]) -> Job:
        self._jobs[job.id] = job
        while len(self._jobs) > KEEP_JOBS:
            self._jobs.popitem(last=False)
        asyncio.get_running_loop().create_task(self._run(job, work))
        return job

    async def _run(self, job: Job, work: Callable[[Job], Awaitable[Any]]) -> None:
        async with self._lock:
            self.current = job
            job.status = "running"
            job.started = time.time()
            try:
                job.result = await work(job)
                job.status = "done"
            except Exception as exc:  # reported to the page, never raised into the loop
                job.status = "error"
                job.error = f"{type(exc).__name__}: {exc}"
                job.result = {"traceback": traceback.format_exc(limit=6)}
                for step in job.steps:
                    if step["status"] == "running":
                        step["status"] = "error"
            finally:
                job.finished = time.time()
                self.current = None

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def active(self) -> list[dict]:
        return [j.summary() for j in self._jobs.values() if j.status in ("queued", "running")]

    def recent(self, n: int = 20) -> list[dict]:
        jobs = list(self._jobs.values())[-n:]
        return [
            {**j.summary(), "deltas": j.deltas, "seconds": j.to_dict()["seconds"]}
            for j in reversed(jobs)
        ]
