"""
Anthropic API proxy.

The frontend stores the user's API key in localStorage and sends it on each
request as an `X-Anthropic-Key` header. We never persist it server-side.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel


router = APIRouter(prefix="/api/ai", tags=["ai"])
log = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-5"  # latest available Sonnet


def _client(key: Optional[str]):
    if not key:
        raise HTTPException(status_code=401, detail="Missing X-Anthropic-Key header. Add your Anthropic API key in Settings.")
    try:
        import anthropic
    except ImportError:
        raise HTTPException(status_code=500, detail="anthropic package not installed on the server.")
    return anthropic.Anthropic(api_key=key)


class ChatRequest(BaseModel):
    prompt: str
    system: Optional[str] = None
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, x_anthropic_key: Optional[str] = Header(default=None)) -> ChatResponse:
    client = _client(x_anthropic_key)
    system = req.system or (
        "You are an expert Universal Epic Universe trip planner. "
        "You know the park's 5 lands (Celestial Park, Super Nintendo World, "
        "The Wizarding World of Harry Potter – Ministry of Magic, How to Train "
        "Your Dragon: Isle of Berk, Dark Universe) and their attractions, shows, "
        "and restaurants. Be concise, specific, and practical. When the user "
        "shares an itinerary or context, use it. Output short answers; use lists when helpful."
    )
    user_content = req.prompt
    if req.context:
        import json
        user_content += "\n\nContext (JSON):\n" + json.dumps(req.context, default=str, indent=2)

    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user_content}],
        )
    except Exception as e:
        log.exception("Anthropic API call failed")
        raise HTTPException(status_code=502, detail=f"Anthropic API error: {e}")

    text = "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")
    return ChatResponse(reply=text)


class EvaluateItinerary(BaseModel):
    items: list[dict]
    target_date: str
    crowd_label: Optional[str] = None


@router.post("/evaluate", response_model=ChatResponse)
def evaluate(req: EvaluateItinerary, x_anthropic_key: Optional[str] = Header(default=None)) -> ChatResponse:
    client = _client(x_anthropic_key)
    system = (
        "You are a strict, experienced Universal Epic Universe trip planner. "
        "Critique the user's proposed itinerary realistically. Call out: "
        "(1) wait-time risks, (2) walking inefficiency between lands, "
        "(3) missed must-do timing, (4) food-timing problems, (5) anything overlooked. "
        "Be direct. End with one concrete suggested change."
    )
    import json
    prompt = (
        f"Date: {req.target_date} (crowd: {req.crowd_label or 'unknown'}).\n\n"
        f"Itinerary:\n{json.dumps(req.items, default=str, indent=2)}"
    )
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1200,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        log.exception("Anthropic API call failed")
        raise HTTPException(status_code=502, detail=f"Anthropic API error: {e}")
    text = "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")
    return ChatResponse(reply=text)


class ResearchRequest(BaseModel):
    topic: str
    kind: str = "restaurant"  # "restaurant" | "ride" | "general"


@router.post("/research", response_model=ChatResponse)
def research(req: ResearchRequest, x_anthropic_key: Optional[str] = Header(default=None)) -> ChatResponse:
    client = _client(x_anthropic_key)
    system = (
        "You are a Universal Epic Universe insider. Give the user a fast, "
        "factual rundown about the topic they ask. For restaurants: signature "
        "dishes, typical wait, price tier, vibe, best time to go. For rides: "
        "duration, intensity, who shouldn't ride, single-rider availability, "
        "best time to ride. Bullets; no fluff."
    )
    prompt = f"Topic ({req.kind}): {req.topic}"
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=800,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        log.exception("Anthropic API call failed")
        raise HTTPException(status_code=502, detail=f"Anthropic API error: {e}")
    text = "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")
    return ChatResponse(reply=text)
