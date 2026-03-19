import asyncio

import pytest

from agent.zero_prompt.schemas import ZPCard


@pytest.fixture(autouse=True)
async def reset_singleton_session(monkeypatch: pytest.MonkeyPatch):
    import agent.server as srv
    from agent.db import zp_store as _zps

    orch = srv._get_zp_orchestrator()
    srv._clear_zp_runtime(orch)

    async def fake_get_dashboard():
        sessions = list(orch._sessions.values())
        if not sessions:
            return {"session_id": None, "status": "idle", "cards": []}
        session = sessions[-1]
        return {
            "session_id": session.session_id,
            "status": session.status,
            "goal_go_cards": session.goal_go_cards,
            "cards": [card.model_dump() for card in session.cards if card.status != "deleted"],
        }

    async def fake_noop(*_args, **_kwargs):
        return None

    async def fake_add_card(_session_id: str, card_id: str, video_id: str, title: str = ""):
        return {"card_id": card_id, "video_id": video_id, "title": title, "status": "analyzing"}

    monkeypatch.setattr(_zps, "get_dashboard", fake_get_dashboard)
    monkeypatch.setattr(_zps, "reset_all_sessions", fake_noop)
    monkeypatch.setattr(_zps, "ensure_session", fake_noop)
    monkeypatch.setattr(_zps, "add_card", fake_add_card)
    monkeypatch.setattr(_zps, "update_card", fake_noop)
    monkeypatch.setattr(_zps, "update_session_status", fake_noop)


@pytest.mark.asyncio
async def test_clear_runtime_cancels_build_tasks():
    import agent.server as srv

    async def sleeper():
        await asyncio.sleep(60)

    task = asyncio.create_task(sleeper())
    srv._zp_build_tasks["s:c"] = task

    srv._clear_zp_runtime(srv._get_zp_orchestrator())
    await asyncio.sleep(0)

    assert task.cancelled()
    assert srv._zp_build_tasks == {}


@pytest.mark.asyncio
async def test_clear_runtime_cancels_analysis_tasks():
    import agent.server as srv

    async def sleeper():
        await asyncio.sleep(60)

    task = asyncio.create_task(sleeper())
    srv._zp_analysis_tasks["s:v"] = task

    srv._clear_zp_runtime(srv._get_zp_orchestrator())
    await asyncio.sleep(0)

    assert task.cancelled()
    assert srv._zp_analysis_tasks == {}


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
async def test_zp_get_latest_session_uses_dashboard_session(app_client):
    first = await app_client.post("/zero-prompt/start", json={})
    second = await app_client.post("/zero-prompt/start", json={})
    latest_session_id = _extract_session_id(second)

    resp = await app_client.get("/zero-prompt/latest")

    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == latest_session_id
    assert body["session_id"] == _extract_session_id(first)


@pytest.mark.asyncio
async def test_zp_start_reuses_singleton_session(app_client):
    first = await app_client.post("/zero-prompt/start", json={"goal": 2})
    second = await app_client.post("/zero-prompt/start", json={"goal": 5})

    assert first.status_code == 200
    assert second.status_code == 200
    assert _extract_session_id(first) == _extract_session_id(second)
    assert second.json()["goal_go_cards"] == 2


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
async def test_zp_action_latest_targets_most_recent_session(app_client):
    import agent.server as srv

    latest = await app_client.post("/zero-prompt/start", json={})
    latest_session_id = _extract_session_id(latest)
    orch = srv._get_zp_orchestrator()
    latest_session = orch.get_session(latest_session_id)
    assert latest_session is not None
    latest_session.cards.append(
        ZPCard(card_id="latest-card", video_id="v1", status="go_ready", score=80, title="Latest")
    )

    resp = await app_client.post(
        "/zero-prompt/latest/actions",
        json={"action": "queue_build", "card_id": "latest-card"},
    )

    assert resp.status_code == 200


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


@pytest.mark.asyncio
async def test_zp_action_delete_rejected_cards(app_client):
    import agent.server as srv

    orch = srv._get_zp_orchestrator()
    session, _ = orch.create_session(goal=5)
    session.status = "completed"
    session.cards.extend(
        [
            ZPCard(card_id="c1", video_id="v1", status="nogo", score=40, title="Rejected 1"),
            ZPCard(card_id="c2", video_id="v2", status="passed", score=42, title="Rejected 2"),
        ]
    )

    resp = await app_client.post(
        f"/zero-prompt/{session.session_id}/actions",
        json={"action": "delete_rejected_cards"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["type"] == "zp.action.delete_rejected_cards"
    assert body["deleted_count"] == 2
    assert all(card.status == "deleted" for card in session.cards)


@pytest.mark.asyncio
async def test_maybe_resume_allows_completed_restart_when_rejections_cleared(monkeypatch: pytest.MonkeyPatch):
    import agent.server as srv

    orch = srv._get_zp_orchestrator()
    session, _ = orch.create_session(goal=5)
    session.status = "completed"
    session.cards.append(ZPCard(card_id="gone", video_id="v1", status="deleted", score=0, title="Gone"))

    launched: list[tuple[str, int]] = []

    monkeypatch.setattr(srv, "_should_launch_zp_pipeline_background_task", lambda: True)
    monkeypatch.setattr(srv, "_launch_zp_pipeline", lambda _orch, session_id, goal: launched.append((session_id, goal)))
    monkeypatch.setattr(srv, "push_zp_event", lambda *_args, **_kwargs: None)

    await srv._maybe_resume_zp_pipeline(orch, session.session_id, allow_completed_restart=True)

    assert session.status == "exploring"
    assert launched == [(session.session_id, session.goal_go_cards)]


@pytest.mark.asyncio
async def test_force_go_sets_consistent_score_breakdown(app_client, monkeypatch: pytest.MonkeyPatch):
    import agent.server as srv

    orch = srv._get_zp_orchestrator()
    session, _ = orch.create_session(goal=5)
    session.cards.append(ZPCard(card_id="go1", video_id="v1", status="nogo", score=21, title="Force GO Card"))

    async def fake_update_card(*_args, **_kwargs):
        return None

    monkeypatch.setattr("agent.db.zp_store.update_card", fake_update_card)

    resp = await app_client.post(
        f"/zero-prompt/{session.session_id}/actions",
        json={"action": "force_go", "card_id": "go1"},
    )

    assert resp.status_code == 200
    card = session.cards[0]
    assert card.status == "go_ready"
    assert card.score == 75
    assert card.score_breakdown["proposal_clarity_points"] == 20.0
