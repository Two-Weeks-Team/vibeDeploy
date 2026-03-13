from agent.flagships import build_flagship_payload, load_flagship_registry
from agent.pipeline_runtime import compose_raw_input


def test_flagship_registry_contains_five_entries():
    registry = load_flagship_registry()

    assert len(registry) == 5
    assert {item["slug"] for item in registry} == {
        "creator-batch-studio",
        "weekender-route-postcards",
        "runway-reset-ledger",
        "interview-sprint-forge",
        "meal-prep-atlas",
    }


def test_build_flagship_payload_includes_youtube_and_acceptance_constraints():
    item = load_flagship_registry()[0]

    payload = build_flagship_payload(item, thread_id="flagship-1")
    raw_input = compose_raw_input(payload)

    assert payload["action"] == "evaluate"
    assert payload["thread_id"] == "flagship-1"
    assert payload["selected_flagship"] == item["slug"]
    assert payload["flagship_contract"]["slug"] == item["slug"]
    assert payload["flagship_contract"]["required_objects"]
    assert payload["youtube_url"].startswith("https://www.youtube.com/watch?v=")
    assert "Acceptance checks:" in payload["constraints"]
    assert f"Flagship lane: {item['slug']}" in raw_input
    assert "Use this YouTube as inspiration:" in raw_input
    assert "Forbidden patterns:" in raw_input
