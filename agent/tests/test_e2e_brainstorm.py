import pytest

from .conftest import parse_sse_events


@pytest.mark.asyncio
async def test_brainstorm_sse_stream(app_client, mock_brainstorm_graph):
    resp = await app_client.post(
        "/brainstorm",
        json={"prompt": "Social fitness app", "config": {"configurable": {"thread_id": "bs-1"}}},
    )
    assert resp.status_code == 200
    events = parse_sse_events(resp.text)
    event_types = [e["event"] for e in events]
    assert "brainstorm.phase.start" in event_types
    assert "brainstorm.node.start" in event_types
    assert "brainstorm.node.complete" in event_types
    assert "brainstorm.agent.insight" in event_types
    assert "brainstorm.phase.complete" in event_types


@pytest.mark.asyncio
async def test_brainstorm_persists_result(app_client, mock_brainstorm_graph):
    await app_client.post(
        "/brainstorm",
        json={"prompt": "Persist test", "config": {"configurable": {"thread_id": "bs-persist"}}},
    )

    resp = await app_client.get("/brainstorm/result/bs-persist")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["insights"]) >= 2
    assert "synthesis" in data
    assert data["synthesis"]["top_ideas"] == ["combined1"]


@pytest.mark.asyncio
async def test_brainstorm_404_for_missing(app_client):
    resp = await app_client.get("/brainstorm/result/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_brainstorm_error_emits_sse_error(app_client, mock_brainstorm_error_graph):
    resp = await app_client.post(
        "/brainstorm",
        json={
            "prompt": "This brainstorm will fail with an error",
            "config": {"configurable": {"thread_id": "bs-error"}},
        },
    )
    events = parse_sse_events(resp.text)
    error_events = [e for e in events if e["event"] == "brainstorm.error"]
    assert len(error_events) == 1
    assert "Brainstorm LLM error" in error_events[0]["data"]["error"]


@pytest.mark.asyncio
async def test_brainstorm_insight_format(app_client, mock_brainstorm_graph):
    resp = await app_client.post(
        "/brainstorm",
        json={"prompt": "Format test", "config": {"configurable": {"thread_id": "bs-format"}}},
    )
    events = parse_sse_events(resp.text)
    insight_events = [e for e in events if e["event"] == "brainstorm.agent.insight"]
    assert len(insight_events) >= 1
    for ie in insight_events:
        assert "agent" in ie["data"]
        assert "ideas" in ie["data"]
        assert isinstance(ie["data"]["ideas"], list)
        assert "opportunities" in ie["data"]
        assert "wild_card" in ie["data"]
        assert "action_items" in ie["data"]
