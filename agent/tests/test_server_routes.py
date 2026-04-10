"""Tests for server.py HTTP routes — covers previously uncovered GET/POST endpoints.

Uses the `app_client` fixture from conftest.py which provides an AsyncClient
wired to the FastAPI ASGI app with an in-memory SQLite store.
"""

import pytest

# ── Health / Info endpoints ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_health(app_client):
    resp = await app_client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert len(body) == 1  # Only status field — no internal config disclosure


@pytest.mark.asyncio
async def test_health_root_alias(app_client):
    """GET / is aliased to the health endpoint."""
    resp = await app_client.get("/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_models_endpoint(app_client):
    resp = await app_client.get("/api/models")
    assert resp.status_code == 200
    body = resp.json()
    assert "models" in body
    assert "selected_runtime_model" in body
    assert "vendors" in body
    assert isinstance(body["models"], dict)


@pytest.mark.asyncio
async def test_models_bare_path(app_client):
    """GET /models is aliased to /api/models."""
    resp = await app_client.get("/models")
    assert resp.status_code == 200
    assert "models" in resp.json()


@pytest.mark.asyncio
async def test_cost_estimate(app_client):
    resp = await app_client.get("/api/cost-estimate")
    assert resp.status_code == 200
    body = resp.json()
    assert "total_cost_usd" in body


@pytest.mark.asyncio
async def test_cost_estimate_bare_path(app_client):
    resp = await app_client.get("/cost-estimate")
    assert resp.status_code == 200
    assert "total_cost_usd" in resp.json()


# ── Result 404 endpoints ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_result_not_found(app_client):
    resp = await app_client.get("/result/nonexistent-thread-id")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "not_found"


@pytest.mark.asyncio
async def test_get_result_api_path_not_found(app_client):
    resp = await app_client.get("/api/result/nonexistent-thread-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_brainstorm_result_not_found(app_client):
    resp = await app_client.get("/brainstorm/result/nonexistent-thread-id")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "not_found"


@pytest.mark.asyncio
async def test_get_brainstorm_result_api_path_not_found(app_client):
    resp = await app_client.get("/api/brainstorm/result/nonexistent-thread-id")
    assert resp.status_code == 404


# ── Dashboard GET endpoints ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dashboard_stats(app_client):
    resp = await app_client.get("/dashboard/stats")
    assert resp.status_code == 200
    body = resp.json()
    # Should return a stats dict with numeric fields
    assert isinstance(body, dict)


@pytest.mark.asyncio
async def test_dashboard_stats_bare_path(app_client):
    resp = await app_client.get("/stats")
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)


@pytest.mark.asyncio
async def test_dashboard_results(app_client):
    resp = await app_client.get("/dashboard/results")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_dashboard_results_bare_path(app_client):
    resp = await app_client.get("/results")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_dashboard_brainstorms(app_client):
    resp = await app_client.get("/dashboard/brainstorms")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_dashboard_brainstorms_bare_path(app_client):
    resp = await app_client.get("/brainstorms")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_dashboard_deployments(app_client):
    resp = await app_client.get("/dashboard/deployments")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_dashboard_deployments_bare_path(app_client):
    resp = await app_client.get("/deployments")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_dashboard_active(app_client):
    resp = await app_client.get("/dashboard/active")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_dashboard_active_bare_path(app_client):
    resp = await app_client.get("/active")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_dashboard_evaluations_no_run(app_client):
    """When no evaluation has been run, returns sentinel status."""
    resp = await app_client.get("/dashboard/evaluations")
    assert resp.status_code == 200
    body = resp.json()
    # Either no_evaluation_run sentinel or a valid summary dict
    assert isinstance(body, dict)
    if "status" in body:
        assert body["status"] == "no_evaluation_run"
        assert body["total"] == 0


@pytest.mark.asyncio
async def test_dashboard_evaluations_bare_path(app_client):
    resp = await app_client.get("/evaluations")
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)


# ── POST endpoints — validation ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_empty_prompt_rejected(app_client):
    """Empty prompt should be rejected by guardrails with HTTP 400."""
    resp = await app_client.post("/api/run", json={"prompt": ""})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_brainstorm_empty_prompt_rejected(app_client):
    """Empty prompt for brainstorm should be rejected by guardrails."""
    resp = await app_client.post("/api/brainstorm", json={"prompt": ""})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_brainstorm_valid_idea_streams(app_client, mock_brainstorm_graph):
    """Valid brainstorm prompt should return 200 SSE stream."""
    resp = await app_client.post(
        "/api/brainstorm",
        json={"prompt": "A restaurant queue management app with QR codes"},
    )
    assert resp.status_code == 200
    # SSE streams use text/event-stream content type
    content_type = resp.headers.get("content-type", "")
    assert "text/event-stream" in content_type


@pytest.mark.asyncio
async def test_run_valid_idea_streams(app_client, mock_eval_graph):
    """Valid evaluation prompt should return 200 SSE stream."""
    resp = await app_client.post(
        "/api/run",
        json={"prompt": "An expense tracker with AI categorization"},
    )
    assert resp.status_code == 200
    content_type = resp.headers.get("content-type", "")
    assert "text/event-stream" in content_type


# ── Test-only PUT endpoints ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_put_test_result_enabled(app_client):
    """With VIBEDEPLOY_ENABLE_TEST_API=1 fixture, PUT /test/result should work."""
    resp = await app_client.put(
        "/test/result/test-thread-123",
        json={"verdict": "GO", "score": 80},
    )
    assert resp.status_code == 200
    assert resp.json()["stored"] == "test-thread-123"


@pytest.mark.asyncio
async def test_put_test_brainstorm_enabled(app_client):
    """With VIBEDEPLOY_ENABLE_TEST_API=1 fixture, PUT /test/brainstorm should work."""
    resp = await app_client.put(
        "/test/brainstorm/brainstorm-123",
        json={"synthesis": {"top_ideas": ["idea1"]}},
    )
    assert resp.status_code == 200
    assert resp.json()["stored"] == "brainstorm-123"


@pytest.mark.asyncio
async def test_result_roundtrip(app_client):
    """Store a result via test endpoint, retrieve it via /result/{id}."""
    thread_id = "roundtrip-thread-456"
    payload = {"verdict": "GO", "score": 77, "idea_summary": "Test idea"}

    put_resp = await app_client.put(f"/test/result/{thread_id}", json=payload)
    assert put_resp.status_code == 200

    get_resp = await app_client.get(f"/result/{thread_id}")
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["verdict"] == "GO"
    assert body["score"] == 77


@pytest.mark.asyncio
async def test_brainstorm_result_roundtrip(app_client):
    """Store a brainstorm result, retrieve it via /brainstorm/result/{id}."""
    thread_id = "brainstorm-roundtrip-789"
    payload = {"synthesis": {"top_ideas": ["idea-a", "idea-b"]}}

    put_resp = await app_client.put(f"/test/brainstorm/{thread_id}", json=payload)
    assert put_resp.status_code == 200

    get_resp = await app_client.get(f"/brainstorm/result/{thread_id}")
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert "synthesis" in body


# ── Ops reconcile endpoint — auth guard ──────────────────────────────────────


@pytest.mark.asyncio
async def test_reconcile_requires_token(app_client):
    """Without ops token, reconcile endpoint returns 403."""
    resp = await app_client.post(
        "/api/ops/dashboard/reconcile",
        json={"showcase_apps": [{"name": "app", "live_url": "https://app.example.com", "repo_url": "gh/repo"}]},
    )
    # Without a valid token, should be forbidden
    assert resp.status_code in (403, 400)
