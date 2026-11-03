"""CityOps Copilot appbook: FastAPI backend + a static single-page frontend."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import DIAGRAMS_DIR, FRONTEND_DIR, load_settings
from .core.jobs import JobManager
from .core.lab import Lab
from .routers import data_explorer, meta, parts


@asynccontextmanager
async def lifespan(app: FastAPI):
    jobs = JobManager()
    lab = Lab(load_settings(), jobs)
    app.state.jobs = jobs
    app.state.lab = lab
    # Connect in the background: the page loads at once and shows progress
    # (or a clear error) instead of the server refusing connections.
    lab.error = "Connecting to Oracle AI Database…"
    asyncio.get_running_loop().run_in_executor(None, lab.start)
    yield
    lab.close()


app = FastAPI(
    title="CityOps Copilot appbook", lifespan=lifespan, docs_url="/api/docs", redoc_url=None
)
app.include_router(meta.router)
app.include_router(parts.router)
app.include_router(data_explorer.router)
app.mount("/diagrams", StaticFiles(directory=DIAGRAMS_DIR), name="diagrams")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html", headers={"Cache-Control": "no-cache"})


app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend")
