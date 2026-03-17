import json

import pytest


def _parse_sse_data(raw_text: str) -> list[dict]:
    events = []
    for line in raw_text.splitlines():
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return events


@pytest.mark.asyncio
async def test_zp_start_returns_sse_stream(app_client):
    resp = await app_client.post("/zero-prompt/start", json={"goal": 2})
    assert resp.status_code == 200
    events = _parse_sse_data(resp.text)
    assert len(events) >= 1
    assert events[0]["type"] == "zp.session.start"
    assert "session_id" in events[0]
    assert events[0]["goal_go_cards"] == 2


@pytest.mark.asyncio
async def test_zp_start_api_prefix(app_client):
    resp = await app_client.post("/api/zero-prompt/start", json={})
    assert resp.status_code == 200
    events = _parse_sse_data(resp.text)
    assert len(events) >= 1
    assert "session_id" in events[0]


def _extract_session_id(resp) -> str:
    events = _parse_sse_data(resp.text)
    return events[0]["session_id"]


@pytest.mark.asyncio
async def test_zp_get_session(app_client):
    start = await app_client.post("/zero-prompt/start", json={})
    session_id = _extract_session_id(start)

    resp = await app_client.get(f"/zero-prompt/{session_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == session_id


@pytest.mark.asyncio
async def test_zp_get_session_not_found(app_client):
    resp = await app_client.get("/zero-prompt/unknown-session-id")
    assert resp.status_code == 404
    assert "detail" in resp.json()


@pytest.mark.asyncio
async def test_zp_action_queue_build(app_client):
    start = await app_client.post("/zero-prompt/start", json={})
    session_id = _extract_session_id(start)

    resp = await app_client.post(
        f"/zero-prompt/{session_id}/actions",
        json={"action": "pause"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["type"] == "zp.action.pause"


@pytest.mark.asyncio
async def test_zp_action_unknown_returns_400(app_client):
    start = await app_client.post("/zero-prompt/start", json={})
    session_id = _extract_session_id(start)

    resp = await app_client.post(
        f"/zero-prompt/{session_id}/actions",
        json={"action": "explode"},
    )
    assert resp.status_code == 400
    assert "detail" in resp.json()
