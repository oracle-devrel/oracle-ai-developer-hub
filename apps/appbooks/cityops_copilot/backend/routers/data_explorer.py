"""Read-only Data Explorer routes (no SQL is accepted from the browser)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from ..core import explorer
from .deps import jobs_of, ready_lab

router = APIRouter(prefix="/api/explorer")


@router.get("/tables")
def tables(request: Request) -> dict:
    lab = ready_lab(request)
    return {"tables": explorer.tables(lab), "activity": jobs_of(request).recent(12)}


@router.get("/rows")
def rows(
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
