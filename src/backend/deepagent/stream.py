"""In-memory event stream broker for frontend realtime updates."""

from __future__ import annotations

import asyncio
from itertools import count


class StreamBroker:
    def __init__(self) -> None:
        self._subscribers: dict[int, asyncio.Queue] = {}
        self._ids = count(1)

    async def publish(self, event: dict) -> None:
        stale: list[int] = []
        for sid, queue in self._subscribers.items():
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                stale.append(sid)

        for sid in stale:
            self._subscribers.pop(sid, None)

    def subscribe(self) -> tuple[int, asyncio.Queue]:
        sid = next(self._ids)
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._subscribers[sid] = queue
        return sid, queue

    def unsubscribe(self, sid: int) -> None:
        self._subscribers.pop(sid, None)
