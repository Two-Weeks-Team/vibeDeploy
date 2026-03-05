import asyncio

import pytest

from .conftest import parse_sse_events


@pytest.mark.asyncio
async def test_health_endpoint(app_client):
    resp = await app_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_put_then_get_result_roundtrip(app_client):
    body = {"score": 99, "verdict": "GO", "analyses": [], "debates": [], "documents": []}
    put_resp = await app_client.put("/test/result/roundtrip-1", json=body)
    assert put_resp.status_code == 200
    assert put_resp.json()["stored"] == "roundtrip-1"

    get_resp = await app_client.get("/result/roundtrip-1")
    assert get_resp.status_code == 200
    assert get_resp.json()["score"] == 99


@pytest.mark.asyncio
async def test_cors_headers(app_client):
    resp = await app_client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert "access-control-allow-origin" in resp.headers


@pytest.mark.asyncio
async def test_concurrent_pipelines(app_client, mock_eval_graph):
    async def run_pipeline(thread_id: str):
        return await app_client.post(
            "/run",
            json={"prompt": f"Concurrent test {thread_id}", "config": {"configurable": {"thread_id": thread_id}}},
        )

    results = await asyncio.gather(
        run_pipeline("concurrent-1"),
        run_pipeline("concurrent-2"),
    )
    for resp in results:
        assert resp.status_code == 200
        events = parse_sse_events(resp.text)
        assert any(e["event"] == "council.phase.complete" for e in events)
