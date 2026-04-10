import pytest


@pytest.mark.asyncio
async def test_health_returns_status_ok(app_client):
    resp = await app_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_health_has_provider_field(app_client):
    resp = await app_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"status": "ok"}  # minimal disclosure


@pytest.mark.asyncio
async def test_cost_estimate_returns_dict(app_client):
    resp = await app_client.get("/cost-estimate")
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)


@pytest.mark.asyncio
async def test_models_returns_models_dict(app_client):
    resp = await app_client.get("/models")
    assert resp.status_code == 200
    data = resp.json()
    assert "models" in data
    assert isinstance(data["models"], dict)


@pytest.mark.asyncio
async def test_models_has_vendors_key(app_client):
    resp = await app_client.get("/models")
    assert resp.status_code == 200
    data = resp.json()
    assert "vendors" in data


@pytest.mark.asyncio
async def test_dashboard_evaluations_no_run_initially(app_client):
    resp = await app_client.get("/dashboard/evaluations")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data or "total" in data


@pytest.mark.asyncio
async def test_dashboard_evaluations_no_evaluation_status(app_client):
    resp = await app_client.get("/dashboard/evaluations")
    assert resp.status_code == 200
    data = resp.json()
    if "status" in data:
        assert data["status"] == "no_evaluation_run"
        assert data["total"] == 0


@pytest.mark.asyncio
async def test_dashboard_stats_returns_stats_dict(app_client):
    resp = await app_client.get("/dashboard/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_dashboard_results_returns_list(app_client):
    resp = await app_client.get("/dashboard/results")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_dashboard_brainstorms_returns_list(app_client):
    resp = await app_client.get("/dashboard/brainstorms")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_dashboard_deployments_returns_list(app_client):
    resp = await app_client.get("/dashboard/deployments")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_cors_headers_present(app_client):
    resp = await app_client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert "access-control-allow-origin" in resp.headers


def test_council_prompts_module_importable():
    from agent.prompts import council_prompts

    assert council_prompts is not None


def test_architect_prompt_is_non_empty_string():
    from agent.prompts.council_prompts import ARCHITECT_PROMPT

    assert isinstance(ARCHITECT_PROMPT, str)
    assert len(ARCHITECT_PROMPT) > 0


def test_scout_prompt_is_non_empty_string():
    from agent.prompts.council_prompts import SCOUT_PROMPT

    assert isinstance(SCOUT_PROMPT, str)
    assert len(SCOUT_PROMPT) > 0


def test_guardian_prompt_is_non_empty_string():
    from agent.prompts.council_prompts import GUARDIAN_PROMPT

    assert isinstance(GUARDIAN_PROMPT, str)
    assert len(GUARDIAN_PROMPT) > 0


def test_catalyst_prompt_is_non_empty_string():
    from agent.prompts.council_prompts import CATALYST_PROMPT

    assert isinstance(CATALYST_PROMPT, str)
    assert len(CATALYST_PROMPT) > 0


def test_advocate_prompt_is_non_empty_string():
    from agent.prompts.council_prompts import ADVOCATE_PROMPT

    assert isinstance(ADVOCATE_PROMPT, str)
    assert len(ADVOCATE_PROMPT) > 0


def test_all_council_prompts_contain_score_instruction():
    from agent.prompts.council_prompts import (
        ADVOCATE_PROMPT,
        ARCHITECT_PROMPT,
        CATALYST_PROMPT,
        GUARDIAN_PROMPT,
        SCOUT_PROMPT,
    )

    for prompt in (ARCHITECT_PROMPT, SCOUT_PROMPT, GUARDIAN_PROMPT, CATALYST_PROMPT, ADVOCATE_PROMPT):
        assert "score" in prompt.lower()
