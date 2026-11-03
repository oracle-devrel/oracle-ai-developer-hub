"""One group of routes per notebook Part, plus the handoff story.

Reads return JSON straight away. Anything that calls a model runs as a job
(see core/jobs.py) and returns ``{"id": ...}`` for the page to poll.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Query, Request

from ..core.jobs import Job
from ..core.lab import HANDOFF_STEPS, Lab
from ..schemas import (
    CopilotRequest,
    EmbedRequest,
    ExtractionDemoRequest,
    FindingSearchRequest,
    LogFindingRequest,
    ReportEventRequest,
    SearchRequest,
    StatelessRequest,
)
from .deps import jobs_of, ready_lab

router = APIRouter(prefix="/api")


# ---------------------------------------------------------------- Part 2


@router.post("/embed")
def embed(body: EmbedRequest, request: Request) -> dict:
    lab = ready_lab(request)
    try:
        texts = body.cleaned()
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from None
    return {"texts": texts, **lab.embed_preview(texts)}


# ---------------------------------------------------------------- Part 3


@router.get("/assets")
def assets(request: Request) -> dict:
    lab = ready_lab(request)
    return {"assets": lab.assets()}


@router.get("/narratives")
def narratives(
    request: Request,
    asset: str | None = Query(None, max_length=128),
    severity: str | None = Query(None, max_length=16),
    limit: int = Query(40, ge=1, le=200),
) -> dict:
    lab = ready_lab(request)
    rows = [
        {"index": i, **log}
        for i, log in enumerate(lab.logs)
        if (asset is None or log["asset_name"] == asset)
        and (severity is None or log["severity"] == severity)
    ]
    sample = lab.sample_narratives(lab.s.demo_narrative_count)
    return {"total": len(rows), "narratives": rows[:limit], "sample": sample}


@router.post("/report-event")
async def report_event(body: ReportEventRequest, request: Request) -> dict:
    lab = ready_lab(request)
    job = Job(
        "report-event",
        f"report_event · {body.asset_id}",
        [
            ("write", "add_messages(): store the narrative and run the extractor"),
            ("diff", "Read back what was persisted"),
        ],
    )
    return (
        jobs_of(request)
        .submit(
            job,
            lambda j: lab.run_report_event(
                j, body.asset_id, body.inspector, body.narrative, body.thread_id
            ),
        )
        .summary()
    )


@router.post("/extraction-demo")
async def extraction_demo(body: ExtractionDemoRequest, request: Request) -> dict:
    lab = ready_lab(request)
    picks = lab.sample_narratives(body.count)
    job = Job(
        "extraction-demo",
        f"Extract memories from {len(picks)} narratives",
        [
            (f"n{i}", f"Narrative {i} of {len(picks)} · {p['asset_name']} [{p['severity']}]")
            for i, p in enumerate(picks, 1)
        ],
    )
    return jobs_of(request).submit(job, lambda j: lab.run_extraction_demo(j, body.count)).summary()


@router.get("/memories")
def memories(
    request: Request,
    user_id: str | None = Query(None, max_length=128),
    record_type: str | None = Query(None, max_length=32),
    thread_id: str | None = Query(None, max_length=128),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    lab = ready_lab(request)
    rows = lab.view_memories(
        user_id=user_id or None,
        record_type=record_type or None,
        thread_id=thread_id or None,
        limit=limit,
    )
    return {"memories": rows}


@router.get("/messages")
def messages(
    request: Request,
    thread_id: str | None = Query(None, max_length=128),
    limit: int = Query(100, ge=1, le=200),
) -> dict:
    lab = ready_lab(request)
    return {"messages": lab.messages(thread_id or None, limit)}


@router.get("/threads")
def threads(request: Request) -> dict:
    lab = ready_lab(request)
    return {"threads": lab.threads()}


@router.post("/search")
async def search(body: SearchRequest, request: Request) -> dict:
    lab = ready_lab(request)
    try:
        return await lab.search(
            body.query,
            user_id=body.user_id,
            agent_id=body.agent_id,
            thread_id=body.thread_id,
            exact_thread_match=body.exact_thread_match,
            record_types=body.record_types,
            max_results=body.max_results,
        )
    except ValueError as exc:  # the SDK rejects some scopes; show its reason
        raise HTTPException(422, detail=str(exc)) from None


# ---------------------------------------------------------------- Part 4


@router.get("/findings")
def findings(request: Request) -> dict:
    lab = ready_lab(request)
    return lab.findings_summary()


@router.post("/findings/search")
def findings_search(body: FindingSearchRequest, request: Request) -> dict:
    lab = ready_lab(request)
    import time

    started = time.perf_counter()
    rows = lab.find_similar_findings(
        body.description, asset_id=body.asset_id or None, category=body.category or None, k=body.k
    )
    return {
        "rows": rows,
        "sql": lab.similar_sql(),
        "binds": {
            "q": "VECTOR(384) of the description",
            "asset_id": body.asset_id or None,
            "category": body.category or None,
            "k": body.k,
        },
        "ms": round((time.perf_counter() - started) * 1000),
    }


@router.post("/findings/log")
def findings_log(body: LogFindingRequest, request: Request) -> dict:
    lab = ready_lab(request)
    if lab.get_asset(body.asset_id) is None:
        raise HTTPException(422, detail=f"{body.asset_id} is not in {lab.t('ASSET')}")
    fid = lab.log_finding(**body.model_dump())
    return {"finding_id": fid}


@router.post("/findings/load-all")
async def findings_load_all(request: Request) -> dict:
    lab = ready_lab(request)
    job = Job(
        "load-findings",
        "Load every dataset finding",
        [("load", "Embed and insert the remaining findings")],
    )

    async def work(j: Job):
        before = lab.table_counts()
        j.begin("load")
        n = await asyncio.to_thread(lab.seed_findings, None)
        j.end("load", {"inserted": n}, detail=f"{n} finding(s) inserted")
        j.add_deltas(lab.deltas_since(before))
        return {"inserted": n}

    return jobs_of(request).submit(job, work).summary()


# ---------------------------------------------------------------- Part 5


@router.post("/scoping-demo")
async def scoping_demo(request: Request) -> dict:
    lab = ready_lab(request)
    job = Job(
        "scoping-demo",
        "Scoping: Mercer's private note vs the city-wide guideline",
        [
            ("write", "Mercer writes one personal note and one city-wide guideline"),
            ("personal", "Vance searches at his own user scope"),
            ("city", "Vance searches at city scope"),
            ("mercer", "Mercer searches at her own user scope"),
        ],
    )
    return jobs_of(request).submit(job, lab.run_scoping_demo).summary()


# ---------------------------------------------------------------- Part 6


@router.post("/copilot")
async def copilot(body: CopilotRequest, request: Request) -> dict:
    lab = ready_lab(request)
    if lab.get_asset(body.asset_id) is None:
        raise HTTPException(422, detail=f"{body.asset_id} is not in {lab.t('ASSET')}")
    job = Job("copilot", f"call_copilot · {body.inspector_id} @ {body.asset_id}", Lab.COPILOT_STEPS)
    return (
        jobs_of(request)
        .submit(
            job, lambda j: lab.call_copilot(j, body.narrative, body.inspector_id, body.asset_id)
        )
        .summary()
    )


@router.post("/stateless")
async def stateless(body: StatelessRequest, request: Request) -> dict:
    lab = ready_lab(request)
    job = Job(
        "stateless",
        "The same narrative, with no memory",
        [("answer", "Ask the LLM with no memory")],
    )
    return jobs_of(request).submit(job, lambda j: lab.stateless(j, body.narrative)).summary()


# --------------------------------------------------------- handoff story


@router.get("/handoff")
def handoff(request: Request) -> dict:
    lab = ready_lab(request)
    return lab.handoff_state()


HANDOFF_TITLES = {
    "mercer-day1": "Day 1 · Mercer asks the copilot about Pier 2 corrosion",
    "mercer-log": "Day 1 · Mercer records the finding with log_finding()",
    "mercer-followup": "Day 1 (afternoon) · Mercer's follow-up note",
    "vance": "Day N · Vance, a different inspector, asks about the same bridge",
    "compare": "Compare · Vance's narrative with no memory at all",
}


@router.post("/handoff/{step}")
async def handoff_step(step: str, request: Request) -> dict:
    lab = ready_lab(request)
    if step not in HANDOFF_STEPS:
        raise HTTPException(404, detail=f"unknown step {step}")
    if step in ("mercer-day1", "mercer-followup", "vance"):
        steps = Lab.COPILOT_STEPS
    elif step == "mercer-log":
        steps = [("log", "log_finding(): Mercer records the structured finding")]
    else:
        steps = [("answer", "Ask the LLM with no memory")]
    job = Job(f"handoff:{step}", HANDOFF_TITLES[step], steps)
    return jobs_of(request).submit(job, lambda j: lab.run_handoff(j, step)).summary()
