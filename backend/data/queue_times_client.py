"""
Thin async client for queue-times.com.

Public endpoints (no auth required):
  - GET /parks.json                       — all parks
  - GET /parks/{park_id}/queue_times.json — current live waits for a park
  - GET /parks/{park_id}/rides.json       — ride list (when supported)

Historical data is not exposed as a clean JSON feed by queue-times. We pull
what's available and cache it. The trainer treats missing days as gaps.

Epic Universe = park 334.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime
from typing import Optional

import httpx


EPIC_PARK_ID = 334
BASE = "https://queue-times.com"


class QueueTimesClient:
    def __init__(self, timeout: float = 15.0):
        self._client = httpx.AsyncClient(timeout=timeout, headers={
            "User-Agent": "epic-planner/0.1 (personal trip planner)",
        })

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "QueueTimesClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def live_queue_times(self, park_id: int = EPIC_PARK_ID) -> dict:
        """Live wait times for all rides at a park."""
        r = await self._client.get(f"{BASE}/parks/{park_id}/queue_times.json")
        r.raise_for_status()
        return r.json()

    async def parks(self) -> list[dict]:
        r = await self._client.get(f"{BASE}/parks.json")
        r.raise_for_status()
        return r.json()


def flatten_live(payload: dict) -> list[dict]:
    """
    queue-times.com payload comes back as { "lands": [...], "rides": [...] }.
    Flatten everything into a single list of rides.
    """
    out: list[dict] = []
    for land in payload.get("lands", []) or []:
        for ride in land.get("rides", []) or []:
            out.append({
                **ride,
                "land": land.get("name"),
            })
    for ride in payload.get("rides", []) or []:
        out.append(ride)
    return out


async def fetch_live_sample() -> list[dict]:
    """Convenience: fetch + flatten current live waits."""
    async with QueueTimesClient() as c:
        return flatten_live(await c.live_queue_times())


if __name__ == "__main__":
    import json
    data = asyncio.run(fetch_live_sample())
    print(json.dumps(data, indent=2))
