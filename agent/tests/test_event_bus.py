"""Tests for zero_prompt/event_bus.py — event fan-out to SSE clients."""

import asyncio

import pytest

from agent.zero_prompt.event_bus import (
    _client_sessions,
    _event_queues,
    push_zp_event,
    register_zp_client,
    unregister_zp_client,
)


@pytest.fixture(autouse=True)
def _clean_bus():
    _event_queues.clear()
    _client_sessions.clear()
    yield
    _event_queues.clear()
    _client_sessions.clear()


class TestRegisterUnregister:
    def test_register_creates_queue(self):
        q = register_zp_client("c1", "s1")
        assert isinstance(q, asyncio.Queue)
        assert "c1" in _event_queues

    def test_unregister_removes_client(self):
        register_zp_client("c1", "s1")
        unregister_zp_client("c1")
        assert "c1" not in _event_queues
        assert "c1" not in _client_sessions

    def test_unregister_nonexistent_is_safe(self):
        unregister_zp_client("nonexistent")


class TestPushEvent:
    def test_event_reaches_subscribed_client(self):
        q = register_zp_client("c1", "s1")
        push_zp_event({"session_id": "s1", "type": "card.update"})
        assert q.qsize() == 1
        event = q.get_nowait()
        assert event["type"] == "card.update"

    def test_event_skips_different_session(self):
        q = register_zp_client("c1", "s1")
        push_zp_event({"session_id": "s2", "type": "card.update"})
        assert q.qsize() == 0

    def test_event_without_session_reaches_all(self):
        q1 = register_zp_client("c1", "s1")
        q2 = register_zp_client("c2", "s2")
        push_zp_event({"type": "global_event"})
        assert q1.qsize() == 1
        assert q2.qsize() == 1

    def test_client_without_session_receives_all(self):
        q = register_zp_client("c1", None)
        push_zp_event({"session_id": "any-session", "type": "card.update"})
        assert q.qsize() == 1

    def test_queue_full_event_dropped_silently(self):
        q = register_zp_client("c1", "s1")
        # Fill the queue to max
        for i in range(300):
            push_zp_event({"session_id": "s1", "type": f"event_{i}"})
        assert q.qsize() == 300
        # This should not raise
        push_zp_event({"session_id": "s1", "type": "overflow"})
        assert q.qsize() == 300

    def test_multiple_clients_same_session(self):
        q1 = register_zp_client("c1", "s1")
        q2 = register_zp_client("c2", "s1")
        push_zp_event({"session_id": "s1", "type": "test"})
        assert q1.qsize() == 1
        assert q2.qsize() == 1
