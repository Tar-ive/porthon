from __future__ import annotations

import pytest

from deepagent.stream import StreamBroker


@pytest.mark.fast
@pytest.mark.asyncio
async def test_stream_broker_publish_subscribe():
    broker = StreamBroker()
    sid, queue = broker.subscribe()

    payload = {"type": "cycle_end", "created_at": "2026-03-04T00:00:00Z"}
    await broker.publish(payload)

    received = await queue.get()
    assert received == payload

    broker.unsubscribe(sid)
