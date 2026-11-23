"""Shared helpers for the routers: the runtime objects and the error mapping."""

from __future__ import annotations

from fastapi import HTTPException, Request

from ..core.jobs import JobManager
from ..core.lab import Lab


def lab_of(request: Request) -> Lab:
    return request.app.state.lab


def jobs_of(request: Request) -> JobManager:
    return request.app.state.jobs


def ready_lab(request: Request) -> Lab:
    lab = lab_of(request)
    if not lab.ready:
        raise HTTPException(
            503, detail=lab.error or "The appbook is still connecting to Oracle and Ollama."
        )
    return lab
