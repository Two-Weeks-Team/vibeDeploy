from agent.graph import route_after_enrich
from agent.pipeline_runtime import normalize_action_payload


def test_route_after_enrich_skip_council_returns_doc_generator():
    state = {"skip_council": True, "idea": {"name": "Test"}, "idea_summary": "test"}
    result = route_after_enrich(state)
    assert result == "doc_generator"


def test_route_after_enrich_no_skip_fans_out_to_council():
    state = {"skip_council": False, "idea": {"name": "Test"}, "idea_summary": "test"}
    result = route_after_enrich(state)
    assert isinstance(result, list)
    assert all(send.node == "run_council_agent" for send in result)
    assert len(result) == 5


def test_route_after_enrich_missing_flag_fans_out_to_council():
    state = {"idea": {"name": "Test"}, "idea_summary": "test"}
    result = route_after_enrich(state)
    assert isinstance(result, list)
    assert len(result) == 5


def test_normalize_action_payload_passes_skip_council():
    payload = {"action": "evaluate", "prompt": "test idea", "skip_council": True}
    normalized = normalize_action_payload(payload)
    assert normalized["skip_council"] is True


def test_normalize_action_payload_defaults_skip_council_false():
    payload = {"action": "evaluate", "prompt": "test idea"}
    normalized = normalize_action_payload(payload)
    assert normalized["skip_council"] is False


def test_skip_council_preserves_fan_out_behavior(monkeypatch):
    monkeypatch.setenv("VIBEDEPLOY_SERIALIZE_AGENT_FANOUT", "1")
    state = {"skip_council": False, "idea": {"name": "Test"}, "idea_summary": "test"}
    result = route_after_enrich(state)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].node == "run_council_agent"
    assert result[0].arg["serial_run"] is True
