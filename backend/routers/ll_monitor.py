"""
Multi-park Lightning Lane monitor with Web Push support.

Polls themeparks.wiki every 30s for live wait / LL data across five parks:
  disneyland, magic_kingdom, epcot, hollywood_studios, animal_kingdom

Push notifications are sent via the Web Push protocol (VAPID) so iOS PWAs
can receive alerts even when the screen is locked or the app is closed.

Routes:
  GET  /api/ll/parks                   → list of supported parks
  GET  /api/ll/vapid-public-key        → VAPID public key for the browser to subscribe
  POST /api/ll/push-subscribe          → register (or update) a device's watch config
  DELETE /api/ll/push-subscribe/{id}   → unregister a device
  GET  /api/ll/{park}/status           → current snapshot (?force=true bypasses cache)
  GET  /api/ll/{park}/stream           → SSE live feed (fallback for non-iOS / foreground)
  GET  /api/ll/{park}/debug            → raw API response for debugging
"""
from __future__ import annotations

import asyncio
import base64
import dataclasses
import json
import logging
import os
import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pywebpush import WebPushException, webpush

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ll", tags=["ll-monitor"])

_POLL_INTERVAL = 30  # seconds

# ── VAPID config ──────────────────────────────────────────────────────────────

_VAPID_EMAIL = os.getenv("VAPID_EMAIL", "mailto:admin@example.com")
_VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
_VAPID_PRIVATE_PEM = os.getenv("VAPID_PRIVATE_KEY_PEM", "")


def _raw_b64url_to_pem(raw_b64url: str) -> str:
    """Convert a base64url-encoded raw EC private key scalar to a SEC1 PEM string.

    Avoids storing multiline PEM in env vars (newlines get corrupted in some
    hosting environments). The cryptography package is already a transitive
    dependency of pywebpush, so this import is always available.
    """
    from cryptography.hazmat.primitives.asymmetric.ec import SECP256R1, derive_private_key
    from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
    raw = base64.urlsafe_b64decode(raw_b64url + "==")
    private_int = int.from_bytes(raw, "big")
    key = derive_private_key(private_int, SECP256R1())
    return key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption()).decode()


# Prefer the single-line raw key (no newline corruption risk) over PEM env var.
_raw_key = os.getenv("VAPID_PRIVATE_KEY_RAW", "")
if _raw_key:
    try:
        _VAPID_PRIVATE_PEM = _raw_b64url_to_pem(_raw_key)
    except Exception as _e:
        log.error("Failed to decode VAPID_PRIVATE_KEY_RAW: %s", _e)

# Load .env if keys are still missing (local dev convenience)
if not _VAPID_PUBLIC_KEY or not _VAPID_PRIVATE_PEM:
    _env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    if os.path.exists(_env_path):
        _pem_lines: list[str] = []
        _collecting_pem = False
        with open(_env_path) as _f:
            for _line in _f:
                _line = _line.rstrip("\n")
                if _line.startswith("VAPID_EMAIL="):
                    _VAPID_EMAIL = _line[len("VAPID_EMAIL="):]
                elif _line.startswith("VAPID_PUBLIC_KEY="):
                    _VAPID_PUBLIC_KEY = _line[len("VAPID_PUBLIC_KEY="):]
                elif _line.startswith("VAPID_PRIVATE_KEY_RAW=") and not _raw_key:
                    try:
                        _VAPID_PRIVATE_PEM = _raw_b64url_to_pem(_line[len("VAPID_PRIVATE_KEY_RAW="):])
                    except Exception as _e:
                        log.error("Failed to decode VAPID_PRIVATE_KEY_RAW from .env: %s", _e)
                elif _line.startswith("VAPID_PRIVATE_KEY_PEM="):
                    _collecting_pem = True
                    _pem_lines = [_line[len("VAPID_PRIVATE_KEY_PEM="):]]
                elif _collecting_pem:
                    _pem_lines.append(_line)
                    if "-----END" in _line:
                        _collecting_pem = False
        if _pem_lines and not _VAPID_PRIVATE_PEM:
            _VAPID_PRIVATE_PEM = "\n".join(_pem_lines)

if not _VAPID_PUBLIC_KEY:
    log.warning("VAPID_PUBLIC_KEY not set — Web Push disabled")
if not _VAPID_PRIVATE_PEM:
    log.warning("VAPID_PRIVATE_KEY_PEM not set — Web Push disabled")

_PUSH_ENABLED = bool(_VAPID_PUBLIC_KEY and _VAPID_PRIVATE_PEM)

# ── Park registry ──────────────────────────────────────────────────────────────

_PARKS: dict[str, dict] = {
    "disneyland": {
        "name": "Disneyland",
        "icon": "🏯",
        "park_id": "7340550b-c14d-4def-80bb-acdb51d49a66",
    },
    "magic_kingdom": {
        "name": "Magic Kingdom",
        "icon": "🏰",
        "park_id": "75ea578a-adc8-4116-a54d-dccb60765ef9",
    },
    "epcot": {
        "name": "EPCOT",
        "icon": "🌍",
        "park_id": "47f90d2c-e191-4239-a466-5892ef59a88b",
    },
    "hollywood_studios": {
        "name": "Hollywood Studios",
        "icon": "🎬",
        "park_id": "288747d1-8b4f-4a64-867e-ea7c9b27bad8",
    },
    "animal_kingdom": {
        "name": "Animal Kingdom",
        "icon": "🌿",
        "park_id": "1c84a229-8862-4648-9c71-378ddd2c7693",
    },
}

# Per-park SSE state
_states: dict[str, dict] = {
    pk: {"latest": {"rides": {}, "fetchedAt": None}, "subscribers": []}
    for pk in _PARKS
}

# ── Push subscription storage ─────────────────────────────────────────────────

@dataclass
class DeviceWatch:
    device_id: str
    push_sub: dict          # Full PushSubscription JSON from browser
    park: str
    watches: dict[str, Optional[int]]   # ride_key → wait threshold (None = no threshold)
    # Change-detection state — populated on first poll after registration
    prev_ll: dict[str, Optional[str]] = field(default_factory=dict)
    prev_status: dict[str, Optional[str]] = field(default_factory=dict)
    prev_wait: dict[str, Optional[int]] = field(default_factory=dict)
    initialized: bool = False

_subscriptions: dict[str, DeviceWatch] = {}  # device_id → DeviceWatch

_SUBS_PATH = os.getenv("SUBSCRIPTIONS_PATH", "/tmp/ll_subscriptions.json")


def _save_subscriptions() -> None:
    try:
        with open(_SUBS_PATH, "w") as f:
            json.dump({k: dataclasses.asdict(v) for k, v in _subscriptions.items()}, f)
    except Exception as exc:
        log.warning("Failed to save subscriptions: %s", exc)


def _load_subscriptions() -> None:
    try:
        if not os.path.exists(_SUBS_PATH):
            return
        with open(_SUBS_PATH) as f:
            data = json.load(f)
        for item in data.values():
            watch = DeviceWatch(**item)
            _subscriptions[watch.device_id] = watch
        log.info("Loaded %d push subscriptions from disk", len(_subscriptions))
    except Exception as exc:
        log.warning("Failed to load subscriptions: %s", exc)


_load_subscriptions()


def _ride_slug(name: str) -> str:
    s = re.sub(r"[^\w\s]", "", name.lower())
    return re.sub(r"\s+", "_", s.strip())


# ── Park fetching ─────────────────────────────────────────────────────────────

async def _fetch_park(park_key: str) -> dict:
    park_id = _PARKS[park_key]["park_id"]
    url = f"https://api.themeparks.wiki/v1/entity/{park_id}/live"

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.json()

    rides: dict[str, dict] = {}
    for item in data.get("liveData", []):
        queue = item.get("queue", {})
        if not queue:
            continue  # skip shows/dining/shops with no queue data

        standby = queue.get("STANDBY") or {}
        # WDW has both LLMP (RETURN_TIME) and LLSP (PAID_RETURN_TIME)
        ll = queue.get("RETURN_TIME") or queue.get("PAID_RETURN_TIME") or {}

        name = item.get("name", "")
        key = _ride_slug(name) or item.get("id", name)

        rides[key] = {
            "name": name,
            "status": item.get("status", "UNKNOWN"),
            "entityType": item.get("entityType", "ATTRACTION"),
            "llState": ll.get("state"),
            "returnStart": ll.get("returnStart"),
            "returnEnd": ll.get("returnEnd"),
            "waitMinutes": standby.get("waitTime"),
        }

    return {"rides": rides, "fetchedAt": datetime.now(timezone.utc).isoformat()}


# ── Push sending ──────────────────────────────────────────────────────────────

def _send_push(watch: DeviceWatch, title: str, body: str) -> None:
    if not _PUSH_ENABLED:
        return
    try:
        webpush(
            subscription_info=watch.push_sub,
            data=json.dumps({"title": title, "body": body}),
            vapid_private_key=_VAPID_PRIVATE_PEM,
            vapid_claims={"sub": _VAPID_EMAIL},
        )
        log.info("Push sent to %s: %s", watch.device_id[:8], title)
    except WebPushException as exc:
        status = getattr(exc.response, "status_code", None)
        if status in (404, 410):
            # Subscription expired — remove it
            _subscriptions.pop(watch.device_id, None)
            _save_subscriptions()
            log.info("Removed expired subscription for %s", watch.device_id[:8])
        else:
            log.warning("Push failed for %s: %s", watch.device_id[:8], exc)
    except Exception as exc:
        log.warning("Push error for %s: %s", watch.device_id[:8], exc)


async def _welcome_push(device_id: str) -> None:
    """Fire a welcome notification 60–150 s after a new device registers."""
    delay = random.uniform(60, 150)
    await asyncio.sleep(delay)
    watch = _subscriptions.get(device_id)
    if not watch:
        return  # unregistered in the meantime
    park_name = _PARKS.get(watch.park, {}).get("name", "the park")
    _send_push(
        watch,
        title="⚡ LL Monitor active",
        body=f"Push notifications are working! Star rides on {park_name} to get alerted when LL opens or waits drop — even when the app is closed.",
    )
    log.info("Welcome push sent to %s", device_id[:8])


def _check_and_push(watch: DeviceWatch, snapshot: dict) -> None:
    """Compare current snapshot against prev state; push if conditions changed."""
    rides = snapshot["rides"]

    if not watch.initialized:
        for key in watch.watches:
            ride = rides.get(key)
            if ride:
                watch.prev_ll[key] = ride["llState"]
                watch.prev_status[key] = ride["status"]
                watch.prev_wait[key] = ride["waitMinutes"]
        watch.initialized = True
        return

    for ride_key, threshold in list(watch.watches.items()):
        ride = rides.get(ride_key)
        if not ride:
            continue

        # LL opened
        if ride["llState"] == "AVAILABLE" and watch.prev_ll.get(ride_key) != "AVAILABLE":
            body = f"Return: {ride['returnStart']}" if ride.get("returnStart") else "Book now!"
            _send_push(watch, f"⚡ {ride['name']} LL Open!", body)

        # Ride opened or closed
        prev_st = watch.prev_status.get(ride_key)
        if prev_st is not None and prev_st != ride["status"]:
            if ride["status"] == "OPERATING":
                _send_push(watch, f"✅ {ride['name']} is OPEN", "Ride is back up!")
            elif prev_st == "OPERATING":
                _send_push(watch, f"🚫 {ride['name']} closed", f"Status: {ride['status']}")

        # Wait dropped below threshold
        prev_w = watch.prev_wait.get(ride_key)
        cur_w = ride["waitMinutes"]
        if (
            threshold is not None
            and cur_w is not None
            and prev_w is not None
            and prev_w > threshold
            and cur_w <= threshold
        ):
            _send_push(watch, f"⏱️ {ride['name']} wait is {cur_w} min",
                       f"Dropped below your {threshold} min alert!")

        # Advance state
        watch.prev_ll[ride_key] = ride["llState"]
        watch.prev_status[ride_key] = ride["status"]
        watch.prev_wait[ride_key] = ride["waitMinutes"]


# ── Poll loop ─────────────────────────────────────────────────────────────────

async def _broadcast(park_key: str, snapshot: dict) -> None:
    state = _states[park_key]
    state["latest"] = snapshot
    payload = json.dumps(snapshot)
    dead: list[asyncio.Queue] = []
    for q in list(state["subscribers"]):
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        state["subscribers"].remove(q)


async def _poll_park(park_key: str) -> None:
    while True:
        try:
            snapshot = await _fetch_park(park_key)
            await _broadcast(park_key, snapshot)

            # Check push subscriptions for this park
            for watch in list(_subscriptions.values()):
                if watch.park == park_key:
                    _check_and_push(watch, snapshot)

            log.info(
                "LL poll OK [%s] %d rides %d SSE %d push",
                park_key, len(snapshot["rides"]),
                len(_states[park_key]["subscribers"]),
                sum(1 for w in _subscriptions.values() if w.park == park_key),
            )
        except Exception as exc:
            log.warning("LL poll failed [%s]: %s", park_key, exc)
        await asyncio.sleep(_POLL_INTERVAL)


async def poll_loop() -> None:
    """Start all per-park poll loops concurrently (called from lifespan)."""
    await asyncio.gather(*(_poll_park(pk) for pk in _PARKS))


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/parks")
async def list_parks() -> dict:
    return {
        "parks": [
            {"key": k, "name": v["name"], "icon": v["icon"]}
            for k, v in _PARKS.items()
        ]
    }


@router.get("/vapid-public-key")
async def vapid_public_key() -> dict:
    if not _PUSH_ENABLED:
        raise HTTPException(status_code=503, detail="Push notifications not configured")
    return {"publicKey": _VAPID_PUBLIC_KEY}


class PushWatch(BaseModel):
    key: str
    threshold: Optional[int] = None


class PushSubscribeRequest(BaseModel):
    device_id: str
    push_subscription: dict   # Full PushSubscription JSON from browser
    park: str
    watches: list[PushWatch]  # Rides to watch


@router.post("/push-subscribe")
async def push_subscribe(req: PushSubscribeRequest) -> dict:
    if not _PUSH_ENABLED:
        raise HTTPException(status_code=503, detail="Push notifications not configured on server")
    if req.park not in _PARKS:
        raise HTTPException(status_code=400, detail=f"Unknown park: {req.park}")

    existing = _subscriptions.get(req.device_id)
    is_new = existing is None

    watch = DeviceWatch(
        device_id=req.device_id,
        push_sub=req.push_subscription,
        park=req.park,
        watches={w.key: w.threshold for w in req.watches},
        # Carry over prev state if park unchanged so we don't re-fire on re-register
        prev_ll=existing.prev_ll if existing and existing.park == req.park else {},
        prev_status=existing.prev_status if existing and existing.park == req.park else {},
        prev_wait=existing.prev_wait if existing and existing.park == req.park else {},
        initialized=existing.initialized if existing and existing.park == req.park else False,
    )
    _subscriptions[req.device_id] = watch
    _save_subscriptions()
    log.info("Push subscription registered: %s → %s (%d watches)",
             req.device_id[:8], req.park, len(req.watches))

    # Send a welcome push to new devices so they can confirm notifications work.
    if is_new:
        asyncio.create_task(_welcome_push(req.device_id))

    return {"status": "ok", "park": req.park, "watches": len(req.watches)}


@router.delete("/push-subscribe/{device_id}")
async def push_unsubscribe(device_id: str) -> dict:
    removed = _subscriptions.pop(device_id, None)
    if removed:
        _save_subscriptions()
    return {"status": "removed" if removed else "not_found"}


@router.get("/{park_key}/status")
async def get_status(park_key: str, force: bool = False) -> dict:
    if park_key not in _PARKS:
        raise HTTPException(status_code=404, detail=f"Unknown park: {park_key}")
    state = _states[park_key]
    if force or state["latest"]["fetchedAt"] is None:
        try:
            snapshot = await _fetch_park(park_key)
            await _broadcast(park_key, snapshot)
        except Exception as exc:
            return {"rides": {}, "fetchedAt": None, "error": str(exc)}
    return state["latest"]


async def _event_generator(q: asyncio.Queue, initial: dict) -> AsyncGenerator[str, None]:
    yield f"data: {json.dumps(initial)}\n\n"
    while True:
        try:
            payload = await asyncio.wait_for(q.get(), timeout=30)
            yield f"data: {payload}\n\n"
        except asyncio.TimeoutError:
            yield ": heartbeat\n\n"


@router.get("/{park_key}/stream")
async def sse_stream(park_key: str) -> StreamingResponse:
    if park_key not in _PARKS:
        raise HTTPException(status_code=404, detail=f"Unknown park: {park_key}")
    state = _states[park_key]
    q: asyncio.Queue = asyncio.Queue(maxsize=4)
    state["subscribers"].append(q)

    async def generator() -> AsyncGenerator[str, None]:
        try:
            async for chunk in _event_generator(q, state["latest"]):
                yield chunk
        finally:
            try:
                state["subscribers"].remove(q)
            except ValueError:
                pass

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{park_key}/debug")
async def debug_park(park_key: str) -> dict:
    if park_key not in _PARKS:
        raise HTTPException(status_code=404, detail=f"Unknown park: {park_key}")
    park_id = _PARKS[park_key]["park_id"]
    url = f"https://api.themeparks.wiki/v1/entity/{park_id}/live"
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()
