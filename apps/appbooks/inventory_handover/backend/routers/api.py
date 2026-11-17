"""All routes: health, the lab run, one job per notebook step, approval, Data Explorer."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..config import NOTEBOOK_FILE, NOTEBOOK_URL
from ..core import db, explorer
from ..core.jobs import Job, JobManager
from ..core.lab import LAB_ORDER, STEPS, Lab

router = APIRouter(prefix="/api")


def lab_of(request: Request) -> Lab:
    return request.app.state.lab


def jobs_of(request: Request) -> JobManager:
    return request.app.state.jobs


def ready_lab(request: Request) -> Lab:
    lab = lab_of(request)
    if not lab.ready:
        raise HTTPException(
            503,
            detail=lab.error or "The appbook is still connecting to Oracle and OCI Generative AI.",
        )
    return lab


class ApproveRequest(BaseModel):
    phrase: str = Field(min_length=1, max_length=80)


# ------------------------------------------------------------------ meta


@router.get("/health")
def health(request: Request) -> dict:
    lab = lab_of(request)
    s = lab.s
    out = {
        "ready": lab.ready,
        "error": lab.error,
        "notebook": NOTEBOOK_FILE,
        "notebook_url": NOTEBOOK_URL,
        "store": s.store,
        "db": {"user": s.db_user, "dsn": s.db_dsn, "password_set": s.password_set, "ok": False},
        "onnx": {"model": s.onnx_model, "ok": False},
        "oci": {
            "model": s.model,
            "endpoint": s.endpoint,
            "region": s.region,
            "auth": s.auth_mode,
            "configured": bool(s.oci_api_key or s.compartment_id),
            "ok": lab.ready,
        },
        "versions": lab.versions,
        "run_id": lab.run.run_id if lab.run else None,
        "jobs": jobs_of(request).active(),
    }
    if lab.pool is not None:
        try:
            db.scalar(lab.pool, "SELECT 1 FROM dual")
            out["db"]["ok"] = True
            out["onnx"]["ok"] = bool(
                db.scalar(
                    lab.pool,
                    "SELECT COUNT(*) FROM user_mining_models WHERE model_name = :m",
                    {"m": s.onnx_model},
                )
            )
        except Exception as exc:
            out["db"]["error"] = f"{type(exc).__name__}: {exc}"
    return out


@router.post("/reconnect")
async def reconnect(request: Request) -> dict:
    lab = lab_of(request)
    await asyncio.to_thread(lab.start)
    return {"ready": lab.ready, "error": lab.error}


@router.get("/case")
def case(request: Request) -> dict:
    return lab_of(request).data


@router.get("/state")
def state(request: Request) -> dict:
    return ready_lab(request).state()


@router.post("/new-run")
async def new_run(request: Request) -> dict:
    lab = ready_lab(request)
    if jobs_of(request).active():
        raise HTTPException(
            409, detail="A step is still running; start a new run when it finishes."
        )
    await lab.close_clients()
    run = lab.new_run()
    return {"run_id": run.run_id}


# ------------------------------------------------------------------ steps


@router.post("/steps/{key}")
async def run_step(key: str, request: Request) -> dict:
    lab = ready_lab(request)
    if key not in STEPS:
        raise HTTPException(404, detail=f"unknown step {key}")
    title, section, _ = STEPS[key]
    job = Job(f"step:{key}", f"{section} · {title}")
    return jobs_of(request).submit(job, lambda j: lab.run_steps(j, key)).summary()


@router.post("/run-all")
async def run_all(request: Request) -> dict:
    lab = ready_lab(request)
    keys = [k for k in LAB_ORDER if k != "cleanup"]
    job = Job(
        "run-all",
        "Run the lab from the top (everything except cleanup)",
        [(k, f"{STEPS[k][1]} · {STEPS[k][0]}") for k in keys],
    )

    async def work(j: Job):
        for key in keys:
            await lab.run_steps(j, key)
        return {"run_id": lab.run.run_id, "done": keys}

    return jobs_of(request).submit(job, work).summary()


@router.post("/approve")
async def approve(body: ApproveRequest, request: Request) -> dict:
    lab = ready_lab(request)
    try:
        return await lab.approve(body.phrase)
    except PermissionError as exc:
        raise HTTPException(403, detail=str(exc)) from None
    except RuntimeError as exc:
        raise HTTPException(409, detail=str(exc)) from None


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


# ------------------------------------------------------------- explorer


@router.get("/explorer/tables")
def explorer_tables(request: Request) -> dict:
    lab = ready_lab(request)
    return {
        "tables": explorer.tables(lab),
        "activity": jobs_of(request).recent(12),
        "run_id": lab.run.run_id if lab.run else None,
    }


@router.get("/explorer/rows")
def explorer_rows(
    request: Request,
    table: str = Query(..., max_length=64),
    limit: int = Query(50, ge=1, le=explorer.MAX_ROWS),
    offset: int = Query(0, ge=0, le=1_000_000),
    filter_column: str | None = Query(None, max_length=32),
    filter_value: str | None = Query(None, max_length=128),
) -> dict:
    lab = ready_lab(request)
    try:
        return explorer.rows(
            lab,
            table.upper(),
            limit=limit,
            offset=offset,
            filter_column=filter_column or None,
            filter_value=filter_value,
        )
    except KeyError as exc:
        raise HTTPException(404, detail=str(exc.args[0])) from None
