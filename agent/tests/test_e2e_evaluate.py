import pytest

from .conftest import parse_sse_events


@pytest.mark.asyncio
async def test_evaluate_sse_stream_go(app_client, mock_eval_graph):
    resp = await app_client.post(
        "/run",
        json={"prompt": "A task manager app", "config": {"configurable": {"thread_id": "eval-1"}}},
    )
    assert resp.status_code == 200
    events = parse_sse_events(resp.text)
    event_types = [e["event"] for e in events]
    assert "council.phase.start" in event_types
    assert "council.node.start" in event_types
    assert "council.node.complete" in event_types
    assert "council.agent.analysis" in event_types
    assert "council.verdict" in event_types
    assert "deploy.complete" in event_types
    assert "council.phase.complete" in event_types


@pytest.mark.asyncio
async def test_evaluate_persists_result(app_client, mock_eval_graph):
    await app_client.post(
        "/run",
        json={"prompt": "Persist test", "config": {"configurable": {"thread_id": "eval-persist"}}},
    )

    resp = await app_client.get("/result/eval-persist")
    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] == 82
    assert data["verdict"] == "GO"
    assert len(data["analyses"]) > 0
    assert data["deployment"]["liveUrl"] == "https://test.app"


@pytest.mark.asyncio
async def test_evaluate_404_for_missing_result(app_client):
    resp = await app_client.get("/result/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_evaluate_nogo_pipeline(app_client, mock_nogo_graph):
    resp = await app_client.post(
        "/run",
        json={"prompt": "Build something bad and unfeasible", "config": {"configurable": {"thread_id": "eval-nogo"}}},
    )
    events = parse_sse_events(resp.text)
    event_types = [e["event"] for e in events]
    assert "council.phase.complete" in event_types

    result_resp = await app_client.get("/result/eval-nogo")
    assert result_resp.status_code == 200
    assert result_resp.json()["verdict"] == "NO-GO"
    assert result_resp.json()["score"] == 30


@pytest.mark.asyncio
async def test_evaluate_error_emits_sse_error(app_client, mock_error_graph):
    resp = await app_client.post(
        "/run",
        json={
            "prompt": "This evaluation will fail with an error",
            "config": {"configurable": {"thread_id": "eval-error"}},
        },
    )
    events = parse_sse_events(resp.text)
    error_events = [e for e in events if e["event"] == "council.error"]
    assert len(error_events) == 1
    assert "LLM provider error" in error_events[0]["data"]["error"]


@pytest.mark.asyncio
async def test_evaluate_verdict_schema(app_client, mock_eval_graph):
    resp = await app_client.post(
        "/run",
        json={"prompt": "Schema test", "config": {"configurable": {"thread_id": "eval-schema"}}},
    )
    events = parse_sse_events(resp.text)
    verdict_events = [e for e in events if e["event"] == "council.verdict"]
    assert len(verdict_events) == 1
    verdict = verdict_events[0]["data"]
    assert "final_score" in verdict
    assert "decision" in verdict
    assert isinstance(verdict["final_score"], (int, float))
    assert verdict["decision"] in ("GO", "CONDITIONAL", "NO_GO")
