import pytest

from agent.nodes.deployer import _is_do_app_limit_error, _reclaim_do_app_capacity


@pytest.mark.asyncio
async def test_reclaim_do_app_capacity_deletes_oldest_failed_app(monkeypatch):
    deleted_ids = []

    async def fake_list_apps():
        return [
            {
                "id": "keep-live",
                "spec": {"name": "queuebite"},
                "live_url": "https://queuebite.example.com",
                "created_at": "2026-03-06T00:00:00Z",
                "active_deployment": {"phase": "ACTIVE"},
            },
            {
                "id": "keep-prod",
                "spec": {"name": "vibedeploy"},
                "live_url": "https://vibedeploy.example.com",
                "created_at": "2026-03-06T00:00:00Z",
                "active_deployment": {"phase": "ACTIVE"},
            },
            {
                "id": "old-failed",
                "spec": {"name": "recipe-box-lite"},
                "live_url": "",
                "created_at": "2026-03-10T04:14:41Z",
                "active_deployment": {"phase": "UNKNOWN"},
            },
            {
                "id": "new-failed",
                "spec": {"name": "bookmark-buddy-lite"},
                "live_url": "",
                "created_at": "2026-03-10T09:57:16Z",
                "active_deployment": {"phase": "UNKNOWN"},
            },
        ]

    async def fake_delete_app(app_id: str):
        deleted_ids.append(app_id)
        return {"status": "deleted", "app_id": app_id}

    async def fake_sleep(_seconds: float):
        return None

    monkeypatch.setattr("agent.nodes.deployer.list_apps", fake_list_apps)
    monkeypatch.setattr("agent.nodes.deployer.delete_app", fake_delete_app)
    monkeypatch.setattr("agent.nodes.deployer.asyncio.sleep", fake_sleep)

    result = await _reclaim_do_app_capacity("bookmarkbrain")

    assert result["status"] == "deleted"
    assert deleted_ids == ["old-failed"]


def test_is_do_app_limit_error_matches_expected_message():
    assert _is_do_app_limit_error({"status": "error", "error": "HTTP 429: App count of 11 exceeds limit of 10"})
    assert not _is_do_app_limit_error({"status": "error", "error": "something else"})
