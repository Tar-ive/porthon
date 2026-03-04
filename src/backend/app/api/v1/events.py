"""POST/GET /v1/events — Event ingestion & streaming."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.v1.schemas import ListObject, generate_id, epoch_now, paginate
from app.auth import get_livemode
from app.deps import get_master
from deepagent.loop import AlwaysOnMaster

router = APIRouter()


class CreateEventRequest(BaseModel):
    type: str
    payload: dict[str, Any] = {}


@router.post("/events")
async def create_event(
    body: CreateEventRequest,
    master: AlwaysOnMaster = Depends(get_master),
):
    result = await master.ingest_event(body.type, body.payload)
    event = result.get("event", {})
    evt_id = event.get("event_id", "")
    if not evt_id.startswith("evt_"):
        evt_id = generate_id("evt_")

    return {
        "id": evt_id,
        "object": "event",
        "created": epoch_now(),
        "livemode": True,
        "metadata": {},
        "type": event.get("type", body.type),
        "payload": event.get("payload", body.payload),
        "cycle": result.get("cycle"),
    }


@router.get("/events")
async def list_events(
    request: Request,
    quest: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    starting_after: str | None = Query(None),
    master: AlwaysOnMaster = Depends(get_master),
):
    state = await master.get_state()
    events = state.get("event_history", [])
    livemode = get_livemode(request.headers.get("Authorization"))

    resources = []
    for e in events:
        evt_id = e.get("event_id", "")
        if not evt_id.startswith("evt_"):
            evt_id = f"evt_{evt_id}" if evt_id else generate_id("evt_")
        resources.append(
            {
                "id": evt_id,
                "object": "event",
                "created": epoch_now(),
                "livemode": livemode,
                "metadata": {},
                "type": e.get("type", ""),
                "payload": e.get("payload", {}),
            }
        )

    page, has_more = paginate(resources, limit=limit, starting_after=starting_after)
    return ListObject(data=page, has_more=has_more, url="/v1/events").model_dump(
        mode="json"
    )


@router.get("/events/stream")
async def stream_events(master: AlwaysOnMaster = Depends(get_master)):
    sid, queue = master.stream.subscribe()

    async def event_generator():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=20.0)
                    # Prefix event IDs
                    if isinstance(event, dict) and "event_id" in event:
                        eid = event["event_id"]
                        if not eid.startswith("evt_"):
                            event["event_id"] = f"evt_{eid}"
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            master.stream.unsubscribe(sid)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
