"""
Disneyland Lightning Lane monitor.

Polls themeparks.wiki every 2 minutes for PAID_RETURN_TIME status on
Big Thunder Mountain, Matterhorn, and Indiana Jones Adventure.

SSE stream: GET /api/ll/stream
Snapshot:   GET /api/ll/status
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator

import httpx
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ll", tags=["ll-monitor"])

# themeparks.wiki entity ID for Disneyland Park (California)
_PARK_ID = "b7678dab-5544-48d5-8fdc-c1a0127cfbcd"
_LIVE_URL = f"https://api.themeparks.wiki/v1/entity/{_PARK_ID}/live"
_POLL_INTERVAL = 30  # seconds

_TRACKED = {
    "big thunder": "Big Thunder Mountain Railroad",
    "matterhorn": "Matterhorn Bobsleds",
    "indiana jones": "Indiana Jones Adventure",
    "star tours": "Star Tours – The Adventures Continue",
}

# Shared state
_latest: dict = {"rides": {}, "fetchedAt": None}
_subscribers: list[asyncio.Queue] = []


async def _fetch() -> dict:
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(_LIVE_URL)
        r.raise_for_status()
        data = r.json()

    rides: dict[str, dict] = {}
    for item in data.get("liveData", []):
        name_lower = item.get("name", "").lower()
        for key in _TRACKED:
            if key in name_lower:
                queue = item.get("queue", {})
                ll = queue.get("PAID_RETURN_TIME") or {}
                standby = queue.get("STANDBY") or {}
                rides[key] = {
                    "name": item.get("name", _TRACKED[key]),
                    "status": item.get("status", "UNKNOWN"),
                    "llState": ll.get("state"),            # AVAILABLE | TEMPORARILY_FULL | FINISHED | None
                    "returnStart": ll.get("returnStart"),
                    "returnEnd": ll.get("returnEnd"),
                    "price": (ll.get("price") or {}).get("amount"),
                    "waitMinutes": standby.get("waitTime"),
                }
                break  # stop checking other keys for this item

    # Fill missing rides so frontend always gets all three keys
    for key, display in _TRACKED.items():
        if key not in rides:
            rides[key] = {
                "name": display,
                "status": "UNKNOWN",
                "llState": None,
                "returnStart": None,
                "returnEnd": None,
                "price": None,
                "waitMinutes": None,
            }

    return {"rides": rides, "fetchedAt": datetime.now(timezone.utc).isoformat()}


async def poll_loop() -> None:
    """Background task started at app startup."""
    global _latest
    while True:
        try:
            snapshot = await _fetch()
            _latest = snapshot
            payload = json.dumps(snapshot)
            dead: list[asyncio.Queue] = []
            for q in list(_subscribers):
                try:
                    q.put_nowait(payload)
                except asyncio.QueueFull:
                    dead.append(q)
            for q in dead:
                _subscribers.remove(q)
            log.info("LL poll OK – %d subscriber(s)", len(_subscribers))
        except Exception as exc:
            log.warning("LL poll failed: %s", exc)
        await asyncio.sleep(_POLL_INTERVAL)


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/status")
async def get_status() -> dict:
    """Return the latest cached snapshot immediately."""
    if _latest["fetchedAt"] is None:
        # First request before the poller has run – fetch inline
        try:
            snapshot = await _fetch()
            _latest.update(snapshot)
        except Exception as exc:
            return {"rides": {}, "fetchedAt": None, "error": str(exc)}
    return _latest


async def _event_generator(q: asyncio.Queue) -> AsyncGenerator[str, None]:
    # Send the current state immediately on connect
    yield f"data: {json.dumps(_latest)}\n\n"
    try:
        while True:
            payload = await asyncio.wait_for(q.get(), timeout=30)
            yield f"data: {payload}\n\n"
    except asyncio.TimeoutError:
        # Heartbeat so the connection stays alive through proxies
        yield ": heartbeat\n\n"
        async for chunk in _event_generator(q):
            yield chunk


@router.get("/debug")
async def debug_raw() -> dict:
    """Return raw API response for the tracked rides — use to inspect field names."""
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(_LIVE_URL)
        r.raise_for_status()
        data = r.json()

    results = {}
    for item in data.get("liveData", []):
        name_lower = item.get("name", "").lower()
        for key in _TRACKED:
            if key in name_lower:
                results[key] = item  # full raw item
                break
    all_items = [{"name": i.get("name"), "id": i.get("id"), "keys": list(i.keys())} for i in data.get("liveData", [])]
    return {"raw": results, "totalItems": len(data.get("liveData", [])), "allItems": all_items, "topLevelKeys": list(data.keys())}
async def sse_stream() -> StreamingResponse:
    """SSE stream – sends a new event every time the poller runs."""
    q: asyncio.Queue = asyncio.Queue(maxsize=4)
    _subscribers.append(q)

    async def generator() -> AsyncGenerator[str, None]:
        try:
            async for chunk in _event_generator(q):
                yield chunk
        finally:
            try:
                _subscribers.remove(q)
            except ValueError:
                pass

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable Nginx buffering
        },
    )
