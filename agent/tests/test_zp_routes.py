import pytest


@pytest.mark.asyncio
async def test_zp_start_returns_session_id(app_client):
    resp = await app_client.post("/zero-prompt/start", json={"goal": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert "session_id" in body
    assert body["status"] == "exploring"
    assert body["goal_go_cards"] == 2


@pytest.mark.asyncio
async def test_zp_start_api_prefix(app_client):
    resp = await app_client.post("/api/zero-prompt/start", json={})
    assert resp.status_code == 200
    assert "session_id" in resp.json()


@pytest.mark.asyncio
async def test_zp_get_session(app_client):
    start = await app_client.post("/zero-prompt/start", json={})
    session_id = start.json()["session_id"]

    resp = await app_client.get(f"/zero-prompt/{session_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == session_id


@pytest.mark.asyncio
async def test_zp_get_session_not_found(app_client):
    resp = await app_client.get("/zero-prompt/unknown-session-id")
    assert resp.status_code == 404
    assert "error" in resp.json()


@pytest.mark.asyncio
async def test_zp_action_queue_build(app_client):
    start = await app_client.post("/zero-prompt/start", json={})
    session_id = start.json()["session_id"]

    resp = await app_client.post(
        f"/zero-prompt/{session_id}/actions",
        json={"action": "queue_build", "card_id": "card-abc"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["action"] == "queue_build"


@pytest.mark.asyncio
async def test_zp_action_unknown_returns_400(app_client):
    start = await app_client.post("/zero-prompt/start", json={})
    session_id = start.json()["session_id"]

    resp = await app_client.post(
        f"/zero-prompt/{session_id}/actions",
        json={"action": "explode"},
    )
    assert resp.status_code == 400
    assert "error" in resp.json()


@pytest.mark.asyncio
async def test_zp_active(app_client):
    resp = await app_client.get("/zero-prompt/active")
    assert resp.status_code == 200
    assert "sessions" in resp.json()


@pytest.mark.asyncio
async def test_zp_active_api_prefix(app_client):
    resp = await app_client.get("/api/zero-prompt/active")
    assert resp.status_code == 200
    assert "sessions" in resp.json()
