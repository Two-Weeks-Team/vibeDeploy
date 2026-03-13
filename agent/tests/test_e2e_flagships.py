import pytest

from agent.flagships import build_flagship_payload, load_flagship_registry


@pytest.mark.asyncio
async def test_all_flagship_payloads_run_through_evaluate_endpoint(app_client, mock_eval_graph):
    registry = load_flagship_registry()

    for entry in registry:
        thread_id = f"flagship-{entry['slug']}"
        payload = build_flagship_payload(entry, thread_id=thread_id)

        response = await app_client.post("/run", json=payload)
        assert response.status_code == 200, entry["slug"]

        result_response = await app_client.get(f"/result/{thread_id}")
        assert result_response.status_code == 200, entry["slug"]
        result = result_response.json()
        assert result["verdict"] == "GO", entry["slug"]
        assert result["selected_flagship"] == entry["slug"], entry["slug"]
