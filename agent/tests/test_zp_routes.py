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


@pytest.mark.asyncio
async def test_run_zp_pipeline_does_not_pause_after_five_rejections(monkeypatch: pytest.MonkeyPatch):
    import agent.server as srv

    orch = srv._get_zp_orchestrator()
    session, _ = orch.create_session(goal=5)
    session_id = session.session_id

    rounds = 0

    async def fake_discover(_session_id: str):
        nonlocal rounds
        rounds += 1
        if rounds == 1:
            return [(f"video-{i}", f"Title {i}", "") for i in range(5)]
        return []

    async def fake_exploration_step(
        target_session_id: str, video_id: str, *, video_title: str = "", video_description: str = ""
    ):
        current = orch.get_session(target_session_id)
        assert current is not None
        card = next(card for card in current.cards if card.video_id == video_id)
        card.title = video_title or video_id
        card.status = "nogo"
        return [{"type": "card.update", "card_id": card.card_id, "status": "nogo", "session_id": target_session_id}]

    async def fake_set_status(_orch, target_session_id: str, status: str):
        current = orch.get_session(target_session_id)
        assert current is not None
        current.status = status

    async def fake_trigger_pending_builds(_orch, _session_id: str):
        return None

    monkeypatch.setattr(srv, "_discover_videos", fake_discover)
    monkeypatch.setattr(orch, "exploration_step", fake_exploration_step)
    monkeypatch.setattr(srv, "_set_zp_session_status", fake_set_status)
    monkeypatch.setattr(srv, "_trigger_pending_builds", fake_trigger_pending_builds)
    monkeypatch.setattr(srv, "push_zp_event", lambda *_args, **_kwargs: None)

    await srv._run_zp_pipeline(orch, session_id, 5)

    assert session.status == "completed"
    assert len(session.cards) == 5
    assert all(card.status == "nogo" for card in session.cards)
