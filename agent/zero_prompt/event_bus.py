import asyncio
from collections import defaultdict

_event_buses: dict[str, asyncio.Queue] = defaultdict(lambda: asyncio.Queue(maxsize=100))


def push_zp_event(event: dict) -> None:
    for q in list(_event_buses.values()):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass
