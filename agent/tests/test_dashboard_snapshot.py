import pytest


def _reset_dashboard_caches(server_module) -> None:
    server_module._dashboard_showcase_cache["expires_at"] = 0.0
    server_module._dashboard_showcase_cache["apps"] = []
    server_module._dashboard_snapshot_cache["expires_at"] = 0.0
    server_module._dashboard_snapshot_cache["meetings"] = []
    server_module._dashboard_snapshot_cache["brainstorms"] = []
    server_module._dashboard_snapshot_cache["filtered"] = False


def _showcase_app(name: str, live_url: str, repo: str) -> dict:
    family = name.split("-")[0]
    return {
        "name": name,
        "live_url": live_url,
        "repo_url": repo,
        "repo_candidates": {name, repo.lower().removeprefix("https://github.com/"), repo.rsplit("/", 1)[-1].lower()},
        "family_candidates": {family},
    }


@pytest.mark.asyncio
async def test_dashboard_reconciles_results_to_active_live_apps(app_client, monkeypatch):
    import agent.server as srv

    _reset_dashboard_caches(srv)

    async def fake_showcase_apps():
        return [
            _showcase_app(
                "demopilot-168642",
                "https://demopilot-168642-xbwvx.ondigitalocean.app",
                "https://github.com/Two-Weeks-Team/demopilot-168642",
            ),
            _showcase_app(
                "trihabit-166567",
                "https://trihabit-166567-2fpe6.ondigitalocean.app",
                "https://github.com/Two-Weeks-Team/trihabit-166567",
            ),
            _showcase_app(
                "smartspend-161898",
                "https://smartspend-161898-m59ar.ondigitalocean.app",
                "https://github.com/Two-Weeks-Team/smartspend-161898",
            ),
            _showcase_app(
                "queueless-158639",
                "https://queueless-158639-44pch.ondigitalocean.app",
                "https://github.com/Two-Weeks-Team/queueless-158639",
            ),
            _showcase_app(
                "studymate-165585",
                "https://studymate-165585-2mqzt.ondigitalocean.app",
                "https://github.com/Two-Weeks-Team/studymate-165585",
            ),
        ]

    monkeypatch.setattr(srv, "_get_showcase_live_apps", fake_showcase_apps)

    records = [
        (
            "campaign7-demopilot-1773168264",
            {
                "score": 93,
                "verdict": "GO",
                "analyses": [],
                "debates": [],
                "documents": [],
                "idea_summary": "Ace your pitch with AI-powered rehearsal and feedback",
                "deployment": {
                    "repoUrl": "https://github.com/Two-Weeks-Team/demopilot-168642",
                    "liveUrl": "",
                },
            },
        ),
        (
            "campaign6-trihabit-a66087b7",
            {
                "score": 88,
                "verdict": "GO",
                "analyses": [],
                "debates": [],
                "documents": [],
                "idea_summary": "Simplify habit tracking for busy professionals with AI-powered coaching.",
                "deployment": {
                    "repoUrl": "https://github.com/Two-Weeks-Team/trihabit-166567",
                    "liveUrl": "",
                },
            },
        ),
        (
            "spendsense-final-08e95a5a",
            {
                "score": 91,
                "verdict": "GO",
                "analyses": [],
                "debates": [],
                "documents": [],
                "idea_summary": "Track. Analyze. Save.",
                "deployment": {
                    "repoUrl": "https://github.com/Two-Weeks-Team/smartspend-161898",
                    "liveUrl": "https://smartspend-161898-m59ar.ondigitalocean.app",
                },
            },
        ),
        (
            "run4-e395a21f",
            {
                "score": 86,
                "verdict": "GO",
                "analyses": [],
                "debates": [],
                "documents": [],
                "idea_summary": "Ditch the wait, not the experience.",
                "deployment": {
                    "repoUrl": "https://github.com/Two-Weeks-Team/queueless-158639",
                    "liveUrl": "https://queueless-158639-44pch.ondigitalocean.app",
                },
            },
        ),
        (
            "060111-studymate",
            {
                "score": 84,
                "verdict": "CONDITIONAL",
                "analyses": [],
                "debates": [],
                "documents": [],
                "idea_summary": "AI-powered flashcard generator from study notes with spaced repetition",
                "deployment": {
                    "repoUrl": "https://github.com/Two-Weeks-Team/studymate-lite-060111",
                    "liveUrl": "https://studymate-lite-060111-5pth7.ondigitalocean.app",
                },
            },
        ),
        (
            "784480-queuebite",
            {
                "score": 80,
                "verdict": "GO",
                "analyses": [],
                "debates": [],
                "documents": [],
                "idea_summary": "Restaurant queue management with QR codes",
                "deployment": {
                    "repoUrl": "https://github.com/Two-Weeks-Team/queuebite-784480",
                    "liveUrl": "https://queuebite-784480-b4ioa.ondigitalocean.app",
                },
            },
        ),
    ]

    for thread_id, body in records:
        response = await app_client.put(f"/test/result/{thread_id}", json=body)
        assert response.status_code == 200

    brainstorm = await app_client.put(
        "/test/brainstorm/bs-edtech-001",
        json={"idea_summary": "AI-powered adaptive learning platform"},
    )
    assert brainstorm.status_code == 200

    results_response = await app_client.get("/dashboard/results")
    assert results_response.status_code == 200
    results = results_response.json()

    assert len(results) == 5
    result_ids = {item["thread_id"] for item in results}
    assert "784480-queuebite" not in result_ids
    assert {
        item["deployment"]["liveUrl"]
        for item in results
    } == {
        "https://demopilot-168642-xbwvx.ondigitalocean.app",
        "https://trihabit-166567-2fpe6.ondigitalocean.app",
        "https://smartspend-161898-m59ar.ondigitalocean.app",
        "https://queueless-158639-44pch.ondigitalocean.app",
        "https://studymate-165585-2mqzt.ondigitalocean.app",
    }

    studymate = next(item for item in results if item["thread_id"] == "060111-studymate")
    assert studymate["deployment"]["repoUrl"] == "https://github.com/Two-Weeks-Team/studymate-165585"
    assert studymate["deployment"]["liveUrl"] == "https://studymate-165585-2mqzt.ondigitalocean.app"

    deployments_response = await app_client.get("/dashboard/deployments")
    assert deployments_response.status_code == 200
    deployments = deployments_response.json()
    assert len(deployments) == 5
    assert {
        item["deployment"]["repoUrl"]
        for item in deployments
    } == {
        "https://github.com/Two-Weeks-Team/demopilot-168642",
        "https://github.com/Two-Weeks-Team/trihabit-166567",
        "https://github.com/Two-Weeks-Team/smartspend-161898",
        "https://github.com/Two-Weeks-Team/queueless-158639",
        "https://github.com/Two-Weeks-Team/studymate-165585",
    }

    brainstorms_response = await app_client.get("/dashboard/brainstorms")
    assert brainstorms_response.status_code == 200
    assert brainstorms_response.json() == []

    stats_response = await app_client.get("/dashboard/stats")
    assert stats_response.status_code == 200
    assert stats_response.json() == {
        "total_meetings": 5,
        "total_brainstorms": 0,
        "avg_score": 88.4,
        "go_count": 4,
        "nogo_count": 1,
    }


@pytest.mark.asyncio
async def test_dashboard_falls_back_to_store_when_no_showcase_inventory(app_client, monkeypatch):
    import agent.server as srv

    _reset_dashboard_caches(srv)

    async def no_showcase_apps():
        return []

    monkeypatch.setattr(srv, "_get_showcase_live_apps", no_showcase_apps)

    result_response = await app_client.put(
        "/test/result/basic-eval",
        json={
            "score": 77,
            "verdict": "GO",
            "analyses": [],
            "debates": [],
            "documents": [],
            "idea_summary": "Basic evaluation",
            "deployment": {"repoUrl": "https://github.com/Two-Weeks-Team/basic-eval", "liveUrl": ""},
        },
    )
    assert result_response.status_code == 200

    brainstorm_response = await app_client.put(
        "/test/brainstorm/basic-brainstorm",
        json={"idea_summary": "Basic brainstorm"},
    )
    assert brainstorm_response.status_code == 200

    results = (await app_client.get("/dashboard/results")).json()
    brainstorms = (await app_client.get("/dashboard/brainstorms")).json()
    stats = (await app_client.get("/dashboard/stats")).json()

    assert len(results) == 1
    assert results[0]["thread_id"] == "basic-eval"
    assert len(brainstorms) == 1
    assert brainstorms[0]["thread_id"] == "basic-brainstorm"
    assert stats == {
        "total_meetings": 1,
        "total_brainstorms": 1,
        "avg_score": 77.0,
        "go_count": 1,
        "nogo_count": 0,
    }


@pytest.mark.asyncio
async def test_dashboard_deployments_only_include_live_apps_without_showcase_inventory(app_client, monkeypatch):
    import agent.server as srv

    _reset_dashboard_caches(srv)

    async def no_showcase_apps():
        return []

    monkeypatch.setattr(srv, "_get_showcase_live_apps", no_showcase_apps)

    local_only = await app_client.put(
        "/test/result/local-only",
        json={
            "score": 80,
            "verdict": "GO",
            "analyses": [],
            "debates": [],
            "documents": [],
            "idea_summary": "Local-only app",
            "deployment": {"repoUrl": "https://github.com/Two-Weeks-Team/local-only", "liveUrl": "", "status": "local_running"},
        },
    )
    assert local_only.status_code == 200

    live_app = await app_client.put(
        "/test/result/live-app",
        json={
            "score": 84,
            "verdict": "GO",
            "analyses": [],
            "debates": [],
            "documents": [],
            "idea_summary": "Live app",
            "deployment": {
                "repoUrl": "https://github.com/Two-Weeks-Team/live-app",
                "liveUrl": "https://live-app.example.com",
                "status": "deployed",
            },
        },
    )
    assert live_app.status_code == 200

    deployments = (await app_client.get("/dashboard/deployments")).json()

    assert len(deployments) == 1
    assert deployments[0]["thread_id"] == "live-app"


@pytest.mark.asyncio
async def test_dashboard_reconcile_endpoint_prunes_store_to_supplied_showcase_apps(app_client, monkeypatch):
    import agent.server as srv

    _reset_dashboard_caches(srv)
    monkeypatch.setenv("VIBEDEPLOY_OPS_TOKEN", "ops-secret")

    records = [
        (
            "campaign7-demopilot-1773168264",
            {
                "score": 93,
                "verdict": "GO",
                "analyses": [],
                "debates": [],
                "documents": [],
                "idea_summary": "Ace your pitch with AI-powered rehearsal and feedback",
                "deployment": {
                    "repoUrl": "https://github.com/Two-Weeks-Team/demopilot-168642",
                    "liveUrl": "",
                    "status": "local_running",
                },
            },
        ),
        (
            "campaign6-trihabit-a66087b7",
            {
                "score": 88,
                "verdict": "GO",
                "analyses": [],
                "debates": [],
                "documents": [],
                "idea_summary": "Simplify habit tracking for busy professionals with AI-powered coaching.",
                "deployment": {
                    "repoUrl": "https://github.com/Two-Weeks-Team/trihabit-166567",
                    "liveUrl": "",
                    "status": "local_running",
                },
            },
        ),
        (
            "spendsense-final-08e95a5a",
            {
                "score": 91,
                "verdict": "GO",
                "analyses": [],
                "debates": [],
                "documents": [],
                "idea_summary": "Track. Analyze. Save.",
                "deployment": {
                    "repoUrl": "https://github.com/Two-Weeks-Team/smartspend-161898",
                    "liveUrl": "https://smartspend-161898-m59ar.ondigitalocean.app",
                    "status": "deployed",
                },
            },
        ),
        (
            "run4-e395a21f",
            {
                "score": 86,
                "verdict": "GO",
                "analyses": [],
                "debates": [],
                "documents": [],
                "idea_summary": "Ditch the wait, not the experience.",
                "deployment": {
                    "repoUrl": "https://github.com/Two-Weeks-Team/queueless-158639",
                    "liveUrl": "https://queueless-158639-44pch.ondigitalocean.app",
                    "status": "deployed",
                },
            },
        ),
        (
            "060111-studymate",
            {
                "score": 84,
                "verdict": "CONDITIONAL",
                "analyses": [],
                "debates": [],
                "documents": [],
                "idea_summary": "AI-powered flashcard generator from study notes with spaced repetition",
                "deployment": {
                    "repoUrl": "https://github.com/Two-Weeks-Team/studymate-lite-060111",
                    "liveUrl": "https://studymate-lite-060111-5pth7.ondigitalocean.app",
                    "status": "deployed",
                },
            },
        ),
        (
            "784480-queuebite",
            {
                "score": 80,
                "verdict": "GO",
                "analyses": [],
                "debates": [],
                "documents": [],
                "idea_summary": "Restaurant queue management with QR codes",
                "deployment": {
                    "repoUrl": "https://github.com/Two-Weeks-Team/queuebite-784480",
                    "liveUrl": "https://queuebite-784480-b4ioa.ondigitalocean.app",
                    "status": "deployed",
                },
            },
        ),
    ]

    for thread_id, body in records:
        response = await app_client.put(f"/test/result/{thread_id}", json=body)
        assert response.status_code == 200

    reconcile = await app_client.post(
        "/api/ops/dashboard/reconcile",
        headers={"x-vibedeploy-ops-token": "ops-secret"},
        json={
            "showcase_apps": [
                {
                    "name": "demopilot-168642",
                    "live_url": "https://demopilot-168642-xbwvx.ondigitalocean.app",
                    "repo_url": "https://github.com/Two-Weeks-Team/demopilot-168642",
                },
                {
                    "name": "trihabit-166567",
                    "live_url": "https://trihabit-166567-2fpe6.ondigitalocean.app",
                    "repo_url": "https://github.com/Two-Weeks-Team/trihabit-166567",
                },
                {
                    "name": "smartspend-161898",
                    "live_url": "https://smartspend-161898-m59ar.ondigitalocean.app",
                    "repo_url": "https://github.com/Two-Weeks-Team/smartspend-161898",
                },
                {
                    "name": "queueless-158639",
                    "live_url": "https://queueless-158639-44pch.ondigitalocean.app",
                    "repo_url": "https://github.com/Two-Weeks-Team/queueless-158639",
                },
                {
                    "name": "studymate-165585",
                    "live_url": "https://studymate-165585-2mqzt.ondigitalocean.app",
                    "repo_url": "https://github.com/Two-Weeks-Team/studymate-165585",
                },
            ]
        },
    )
    assert reconcile.status_code == 200
    assert reconcile.json()["stored"] == 5

    results = (await app_client.get("/dashboard/results")).json()
    deployments = (await app_client.get("/dashboard/deployments")).json()

    assert len(results) == 5
    assert len(deployments) == 5
    assert {item["thread_id"] for item in results} == {
        "campaign7-demopilot-1773168264",
        "campaign6-trihabit-a66087b7",
        "spendsense-final-08e95a5a",
        "run4-e395a21f",
        "060111-studymate",
    }
    assert {item["deployment"]["status"] for item in results} == {"deployed"}
    assert {item["deployment"]["liveUrl"] for item in deployments} == {
        "https://demopilot-168642-xbwvx.ondigitalocean.app",
        "https://trihabit-166567-2fpe6.ondigitalocean.app",
        "https://smartspend-161898-m59ar.ondigitalocean.app",
        "https://queueless-158639-44pch.ondigitalocean.app",
        "https://studymate-165585-2mqzt.ondigitalocean.app",
    }
