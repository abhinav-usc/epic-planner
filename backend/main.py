"""
Epic Universe Day Planner — FastAPI entrypoint.

Run from repo root:
    uvicorn backend.main:app --reload --port 8000
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import attractions, crowd, predictions, optimization, ai, data_refresh
from backend.routers import lightning_lanes


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    lightning_lanes.start_poller()
    yield


app = FastAPI(
    title="Epic Universe Planner",
    description="Plan your day at Epic Universe. Wait times, optimization, AI helpers.",
    version="0.1.0",
    lifespan=lifespan,
)

# Local dev: Vite serves on 5173 by default.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
app.include_router(lightning_lanes.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
