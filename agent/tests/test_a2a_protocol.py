import pytest

from agent.gradient.a2a import clear_message_log, get_message_log, send_message, validate_handoff
from agent.gradient.a2a_schemas import A2AMessage, A2AResponse


def _make_message(
    message_type: str = "idea_handoff",
    payload: dict | None = None,
    sender: str = "strategist",
    receiver: str = "architect",
    timestamp: str = "2026-03-17T00:00:00Z",
) -> A2AMessage:
    return A2AMessage(
        sender_agent=sender,
        receiver_agent=receiver,
        payload=payload if payload is not None else {"idea_name": "TestApp", "score": 78.5},
        message_type=message_type,
        timestamp=timestamp,
    )


@pytest.fixture(autouse=True)
def reset_log():
    clear_message_log()
    yield
    clear_message_log()


def test_valid_idea_handoff_accepted():
    msg = _make_message(message_type="idea_handoff", payload={"idea_name": "QueueBite", "score": 78.5})
    resp = send_message(msg)
    assert resp.status == "accepted"
    assert resp.receiver_agent == "architect"


def test_idea_handoff_missing_score_rejected():
    msg = _make_message(message_type="idea_handoff", payload={"idea_name": "OnlyName"})
    resp = send_message(msg)
    assert resp.status == "rejected"
    assert "score" in resp.details


def test_idea_handoff_missing_idea_name_rejected():
    msg = _make_message(message_type="idea_handoff", payload={"score": 55.0})
    resp = send_message(msg)
    assert resp.status == "rejected"
    assert "idea_name" in resp.details


def test_idea_handoff_empty_payload_rejected():
    msg = _make_message(message_type="idea_handoff", payload={})
    resp = send_message(msg)
    assert resp.status == "rejected"


def test_build_request_accepted_without_handoff_validation():
    msg = _make_message(message_type="build_request", payload={"spec": "v1"}, receiver="architect")
    resp = send_message(msg)
    assert resp.status == "accepted"


def test_status_update_accepted():
    msg = _make_message(message_type="status_update", payload={"stage": "deploying"}, receiver="scout")
    resp = send_message(msg)
    assert resp.status == "accepted"


def test_unknown_receiver_returns_error():
    msg = _make_message(receiver="nonexistent_agent")
    resp = send_message(msg)
    assert resp.status == "error"
    assert "nonexistent_agent" in resp.details


def test_message_log_tracks_accepted_messages():
    assert get_message_log() == []
    send_message(_make_message(message_type="build_request", payload={"task": "scaffold"}, receiver="architect"))
    send_message(_make_message(message_type="status_update", payload={"status": "done"}, receiver="scout"))
    log = get_message_log()
    assert len(log) == 2
    assert log[0].message_type == "build_request"
    assert log[1].message_type == "status_update"


def test_message_log_not_updated_on_rejection():
    send_message(_make_message(message_type="idea_handoff", payload={}))
    assert get_message_log() == []


def test_message_log_not_updated_on_error():
    send_message(_make_message(receiver="unknown_bot"))
    assert get_message_log() == []


def test_validate_handoff_true_with_required_fields():
    assert validate_handoff({"idea_name": "App", "score": 90, "extra": "value"}) is True


def test_validate_handoff_false_missing_fields():
    assert validate_handoff({"idea_name": "App"}) is False
    assert validate_handoff({"score": 70}) is False
    assert validate_handoff({}) is False


def test_response_is_a2a_response_instance():
    resp = send_message(_make_message())
    assert isinstance(resp, A2AResponse)


def test_get_message_log_returns_copy():
    send_message(_make_message(message_type="build_request", payload={"x": 1}, receiver="architect"))
    log1 = get_message_log()
    log1.clear()
    assert len(get_message_log()) == 1
