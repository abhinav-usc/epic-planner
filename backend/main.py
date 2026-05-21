"""
Epic Universe Day Planner — FastAPI entrypoint.

Run from repo root:
    uvicorn backend.main:app --reload --port 8000

In production the compiled frontend lives at /app/frontend/dist.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.routers import attractions, crowd, predictions, optimization, ai, data_refresh, history, ll, live
from backend.routers import ll_monitor


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

_STATIC = Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(ll_monitor.poll_loop())
    yield
    task.cancel()

app = FastAPI(
    title="Orlando Trip Planner",
    description="Plan your day at all Orlando theme parks. Wait times, optimization, AI helpers.",
    version="0.1.0",
    lifespan=lifespan,
)

# Local dev: Vite serves on 5173 by default.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(attractions.router)
app.include_router(crowd.router)
app.include_router(predictions.router)
app.include_router(optimization.router)
app.include_router(ai.router)
app.include_router(data_refresh.router)
app.include_router(ll_monitor.router)
app.include_router(history.router)
app.include_router(ll.router)
app.include_router(live.router)


@app.api_route("/api/health", methods=["GET", "HEAD"])
def health() -> dict:
    return {"status": "ok"}


# Serve built frontend (production). Must be mounted last so /api routes win.
if _STATIC.exists():
    app.mount("/", StaticFiles(directory=_STATIC, html=True), name="static")
