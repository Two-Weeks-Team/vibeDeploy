import asyncio

_event_queues: dict[str, asyncio.Queue] = {}
_client_sessions: dict[str, str | None] = {}


def register_zp_client(client_id: str, session_id: str | None = None) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=300)
    _event_queues[client_id] = q
    _client_sessions[client_id] = session_id
    return q


def unregister_zp_client(client_id: str) -> None:
    _event_queues.pop(client_id, None)
    _client_sessions.pop(client_id, None)


def push_zp_event(event: dict) -> None:
    target_session = event.get("session_id")
    for client_id, q in list(_event_queues.items()):
        subscribed_session = _client_sessions.get(client_id)
        if target_session and subscribed_session and subscribed_session != target_session:
            continue
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass
