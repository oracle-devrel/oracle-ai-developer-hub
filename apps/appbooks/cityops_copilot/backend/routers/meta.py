"""Health, workspace status, reset and job polling."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Request

from ..config import NOTEBOOK_FILE, NOTEBOOK_URL
from ..core import db
from ..core.jobs import Job
from ..core.lab import RECORD_TYPES
from .deps import jobs_of, lab_of, ready_lab

router = APIRouter(prefix="/api")


@router.get("/health")
def health(request: Request) -> dict:
    lab = lab_of(request)
    s = lab.s
    out = {
        "ready": lab.ready,
        "error": lab.error,
        "notebook": NOTEBOOK_FILE,
        "notebook_url": NOTEBOOK_URL,
        "db": {"user": s.db_user, "dsn": s.db_dsn, "password_set": s.password_set, "ok": False},
        "onnx": {"model": s.onnx_model, "ok": False},
        "ollama": lab.ollama_status(),
        "prefix": s.table_prefix,
        "jobs": jobs_of(request).active(),
    }
    if lab.pool is not None:
        try:
            db.scalar(lab.pool, "SELECT 1 FROM dual")
            out["db"]["ok"] = True
            out["onnx"]["ok"] = lab.onnx_loaded()
            try:
                out["db"]["version"] = db.scalar(
                    lab.pool,
                    "SELECT version_full FROM product_component_version FETCH FIRST 1 ROW ONLY",
                )
            except Exception:
                out["db"]["version"] = None
        except Exception as exc:
            out["db"]["error"] = f"{type(exc).__name__}: {exc}"
    return out


@router.post("/reconnect")
async def reconnect(request: Request) -> dict:
    lab = lab_of(request)
    await asyncio.to_thread(lab.start)
    return {"ready": lab.ready, "error": lab.error}


@router.get("/overview")
def overview(request: Request) -> dict:
    lab = ready_lab(request)
    counts = lab.table_counts()
    by_type = {
        r["memory_type"]: int(r["n"])
        for r in db.query(
            lab.pool,
            f"SELECT memory_type, COUNT(*) AS n FROM {lab.t('MEMORY')} GROUP BY memory_type",
        )
    }
    return {
        "tables": counts,
        "memory_by_type": {t: by_type.get(t, 0) for t in RECORD_TYPES},
        "threads": len(lab.threads()),
        "assets": len(lab.equipment),
        "dataset": {
            "narratives": len(lab.logs),
            "reports": len(lab.reports),
            "findings": lab.dataset_finding_total(),
        },
        "hnsw": lab.has_hnsw_index(),
        "prefix": lab.s.table_prefix,
    }


@router.post("/reset")
async def reset(request: Request) -> dict:
    lab = ready_lab(request)
    job = Job(
        "reset",
        "Reset the appbook's workspace",
        [
            ("drop", "Drop the appbook's tables"),
            ("sdk", "Re-open the SDK"),
            ("domain", "Reload the domain tables"),
        ],
    )

    async def work(j: Job):
        return await asyncio.to_thread(lab.reset, j)

    return jobs_of(request).submit(job, work).summary()


@router.get("/jobs")
def jobs(request: Request) -> dict:
    manager = jobs_of(request)
    return {"active": manager.active(), "recent": manager.recent()}


@router.get("/jobs/{job_id}")
def job(job_id: str, request: Request) -> dict:
    found = jobs_of(request).get(job_id)
    if found is None:
        raise HTTPException(
            404, detail="no such job (jobs are kept in memory until the server restarts)"
        )
    return found.to_dict()
