import pytest


@pytest.mark.asyncio
async def test_zp_start_returns_json_session(app_client):
    resp = await app_client.post("/zero-prompt/start", json={"goal": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"]
    assert body["goal_go_cards"] == 2
    assert body["status"] == "exploring"


@pytest.mark.asyncio
async def test_zp_start_api_prefix(app_client):
    resp = await app_client.post("/api/zero-prompt/start", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"]


def _extract_session_id(resp) -> str:
    return resp.json()["session_id"]


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
        json={"action": "queue_build", "card_id": "missing-card"},
    )
    assert resp.status_code in {200, 422}
    if resp.status_code == 200:
        body = resp.json()
        assert body["type"] == "zp.action.error"
        assert body["error"] in {"session_not_found", "card_not_found", "card_not_go_ready"}


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
