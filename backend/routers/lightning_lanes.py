"""
Disneyland Lightning Lane availability monitor.

Polls ThemeParks.wiki API every 2 minutes, caches the latest status,
and streams live updates to connected clients via Server-Sent Events.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

import httpx
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/lightning-lanes", tags=["lightning-lanes"])
log = logging.getLogger(__name__)

# ThemeParks.wiki open API — no key required
THEMEPARKS_API = "https://api.themeparks.wiki/v1"
# Disneyland Park (Anaheim, CA) entity ID on ThemeParks.wiki
DISNEYLAND_PARK_ID = "7340550b-c14d-4def-80bb-acbe51adbb05"

TRACKED = [
    "Big Thunder Mountain Railroad",
    "Matterhorn Bobsleds",
    "Indiana Jones Adventure",
]

_cache: dict[str, dict] = {}
_updated_at: Optional[str] = None
_clients: list[asyncio.Queue] = []
_poller_task: Optional[asyncio.Task] = None


def _match_name(entity_name: str) -> Optional[str]:
    """Fuzzy-match a ThemeParks entity name against our tracked list."""
    en = entity_name.lower()
    for tracked in TRACKED:
        # Require all words longer than 3 chars to appear in the entity name
        keywords = [w for w in tracked.lower().split() if len(w) > 3]
        if keywords and all(k in en for k in keywords):
            return tracked
    return None


async def _fetch_live_data() -> dict[str, dict]:
    """Fetch live data from ThemeParks.wiki and extract LL status."""
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                f"{THEMEPARKS_API}/entity/{DISNEYLAND_PARK_ID}/live",
                headers={"User-Agent": "epic-planner/1.0"},
            )
            resp.raise_for_status()
            data = resp.json()

        result: dict[str, dict] = {}
        for entity in data.get("liveData", []):
            matched = _match_name(entity.get("name", ""))
            if matched is None:
                continue

            queue = entity.get("queue", {})
            # RETURN_TIME = Lightning Lane Multi Pass (LLMP)
            llmp = queue.get("RETURN_TIME", {})
            # PAID_RETURN_TIME = Individual Lightning Lane (ILL)
            ill = queue.get("PAID_RETURN_TIME", {})

            if llmp.get("state"):
                ll_state = llmp["state"]
                ll_return_start = llmp.get("returnStart")
                ll_return_end = llmp.get("returnEnd")
                ll_type = "LLMP"
            elif ill.get("state"):
                ll_state = ill["state"]
                ll_return_start = ill.get("returnStart")
                ll_return_end = ill.get("returnEnd")
                ll_type = "ILL"
            else:
                ll_state = None
                ll_return_start = None
                ll_return_end = None
                ll_type = None

            result[matched] = {
                "name": entity.get("name"),
                "status": entity.get("status", "UNKNOWN"),
                "standby_wait": queue.get("STANDBY", {}).get("waitTime"),
                "ll_state": ll_state,
                "ll_return_start": ll_return_start,
                "ll_return_end": ll_return_end,
                "ll_type": ll_type,
            }

        # Fill any unmatched tracked attractions as unknown
        for name in TRACKED:
            if name not in result:
                result[name] = {
                    "name": name,
                    "status": "UNKNOWN",
                    "standby_wait": None,
                    "ll_state": None,
                    "ll_return_start": None,
                    "ll_return_end": None,
                    "ll_type": None,
                }

        return result

    except Exception as exc:
        log.exception("LL fetch failed: %s", exc)
        return {
            name: {
                "name": name,
                "status": "ERROR",
                "standby_wait": None,
                "ll_state": None,
                "ll_return_start": None,
                "ll_return_end": None,
                "ll_type": None,
            }
            for name in TRACKED
        }


async def _broadcast(payload: str) -> None:
    dead: list[asyncio.Queue] = []
    for q in _clients:
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        if q in _clients:
            _clients.remove(q)


async def _poll_loop() -> None:
    """Fetch every 2 minutes and push to connected SSE clients."""
    global _cache, _updated_at
    while True:
        data = await _fetch_live_data()
        _cache = data
        _updated_at = datetime.now(timezone.utc).isoformat()
        payload = json.dumps({"attractions": _cache, "updated_at": _updated_at})
        await _broadcast(payload)
        log.info("LL status refreshed — %d client(s) connected", len(_clients))
        await asyncio.sleep(120)


def start_poller() -> None:
    """Start the background polling task. Call once from app startup."""
    global _poller_task
    if _poller_task is None or _poller_task.done():
        _poller_task = asyncio.create_task(_poll_loop())
        log.info("Lightning Lane poller started")


@router.get("/status")
async def get_status():
    """Snapshot of current LL status (fetches live if cache is empty)."""
    data = _cache if _cache else await _fetch_live_data()
    return {"attractions": data, "updated_at": _updated_at}


@router.get("/stream")
async def sse_stream():
    """SSE endpoint — sends current state immediately, then every 2 minutes."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=10)
    _clients.append(queue)

    async def generate() -> AsyncGenerator[str, None]:
        if _cache:
            payload = json.dumps({"attractions": _cache, "updated_at": _updated_at})
            yield f"data: {payload}\n\n"
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {msg}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except (asyncio.CancelledError, GeneratorExit):
            pass
        finally:
            if queue in _clients:
                _clients.remove(queue)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
