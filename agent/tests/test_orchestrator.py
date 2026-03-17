from agent.zero_prompt.orchestrator import SessionManager
from agent.zero_prompt.queue_manager import BuildQueue


class TestSessionManagerCreate:
    def test_create_session_returns_session(self):
        mgr = SessionManager()
        session = mgr.create_session()
        assert session.session_id
        assert session.status == "exploring"
        assert session.cards == []
        assert session.build_queue == []
        assert session.active_build is None
        assert session.goal_go_cards == 10
        assert session.created_at

    def test_create_session_custom_goal(self):
        mgr = SessionManager()
        session = mgr.create_session(goal=5)
        assert session.goal_go_cards == 5

    def test_create_session_unique_ids(self):
        mgr = SessionManager()
        s1 = mgr.create_session()
        s2 = mgr.create_session()
        assert s1.session_id != s2.session_id


class TestSessionManagerGet:
    def test_get_session_returns_existing(self):
        mgr = SessionManager()
        session = mgr.create_session()
        found = mgr.get_session(session.session_id)
        assert found is not None
        assert found.session_id == session.session_id

    def test_get_session_returns_none_for_unknown(self):
        mgr = SessionManager()
        assert mgr.get_session("nonexistent-id") is None


class TestSessionManagerCards:
    def test_add_card_returns_card(self):
        mgr = SessionManager()
        session = mgr.create_session()
        card = mgr.add_card(session.session_id, "vid_001")
        assert card.card_id
        assert card.video_id == "vid_001"
        assert card.status == "processing"
        assert card.score == 0
        assert card.thread_id is None

    def test_add_card_appended_to_session(self):
        mgr = SessionManager()
        session = mgr.create_session()
        mgr.add_card(session.session_id, "vid_002")
        updated = mgr.get_session(session.session_id)
        assert updated is not None
        assert len(updated.cards) == 1

    def test_update_card_status_returns_true(self):
        mgr = SessionManager()
        session = mgr.create_session()
        card = mgr.add_card(session.session_id, "vid_003")
        result = mgr.update_card_status(session.session_id, card.card_id, "go_ready")
        assert result is True

    def test_update_card_status_persists(self):
        mgr = SessionManager()
        session = mgr.create_session()
        card = mgr.add_card(session.session_id, "vid_004")
        mgr.update_card_status(session.session_id, card.card_id, "nogo", score=20)
        updated = mgr.get_session(session.session_id)
        assert updated is not None
        c = updated.cards[0]
        assert c.status == "nogo"
        assert c.score == 20

    def test_update_card_status_unknown_card_returns_false(self):
        mgr = SessionManager()
        session = mgr.create_session()
        result = mgr.update_card_status(session.session_id, "bad-card-id", "go_ready")
        assert result is False

    def test_update_card_status_unknown_session_returns_false(self):
        mgr = SessionManager()
        result = mgr.update_card_status("bad-session", "any-card", "go_ready")
        assert result is False

    def test_update_card_sets_thread_id(self):
        mgr = SessionManager()
        session = mgr.create_session()
        card = mgr.add_card(session.session_id, "vid_005")
        mgr.update_card_status(session.session_id, card.card_id, "building", thread_id="thread-xyz")
        updated = mgr.get_session(session.session_id)
        assert updated is not None
        assert updated.cards[0].thread_id == "thread-xyz"

    def test_delete_card_status(self):
        mgr = SessionManager()
        session = mgr.create_session()
        card = mgr.add_card(session.session_id, "vid_006")
        mgr.update_card_status(session.session_id, card.card_id, "deleted")
        updated = mgr.get_session(session.session_id)
        assert updated is not None
        assert updated.cards[0].status == "deleted"


class TestSessionManagerBuildQueue:
    def test_queue_build_returns_true(self):
        mgr = SessionManager()
        session = mgr.create_session()
        card = mgr.add_card(session.session_id, "vid_007")
        result = mgr.queue_build(session.session_id, card.card_id)
        assert result is True

    def test_queue_build_fifo_order(self):
        mgr = SessionManager()
        session = mgr.create_session()
        c1 = mgr.add_card(session.session_id, "vid_a")
        c2 = mgr.add_card(session.session_id, "vid_b")
        mgr.queue_build(session.session_id, c1.card_id)
        mgr.queue_build(session.session_id, c2.card_id)
        first = mgr.get_next_build(session.session_id)
        second = mgr.get_next_build(session.session_id)
        assert first == c1.card_id
        assert second == c2.card_id

    def test_get_next_build_empty_returns_none(self):
        mgr = SessionManager()
        session = mgr.create_session()
        assert mgr.get_next_build(session.session_id) is None

    def test_get_next_build_unknown_session_returns_none(self):
        mgr = SessionManager()
        assert mgr.get_next_build("no-such-session") is None

    def test_queue_build_unknown_session_returns_false(self):
        mgr = SessionManager()
        result = mgr.queue_build("bad-session", "any-card")
        assert result is False


class TestSessionManagerPauseResume:
    def test_pause_sets_paused(self):
        mgr = SessionManager()
        session = mgr.create_session()
        mgr.pause_session(session.session_id)
        updated = mgr.get_session(session.session_id)
        assert updated is not None
        assert updated.status == "paused"

    def test_resume_sets_exploring(self):
        mgr = SessionManager()
        session = mgr.create_session()
        mgr.pause_session(session.session_id)
        mgr.resume_session(session.session_id)
        updated = mgr.get_session(session.session_id)
        assert updated is not None
        assert updated.status == "exploring"

    def test_pause_unknown_session_returns_false(self):
        mgr = SessionManager()
        assert mgr.pause_session("no-such-session") is False

    def test_resume_unknown_session_returns_false(self):
        mgr = SessionManager()
        assert mgr.resume_session("no-such-session") is False


class TestShouldContinueExploring:
    def test_continue_when_no_go_ready(self):
        mgr = SessionManager()
        session = mgr.create_session(goal=3)
        assert mgr.should_continue_exploring(session.session_id) is True

    def test_stop_when_goal_reached(self):
        mgr = SessionManager()
        session = mgr.create_session(goal=2)
        for _ in range(2):
            card = mgr.add_card(session.session_id, "vid_x")
            mgr.update_card_status(session.session_id, card.card_id, "go_ready")
        assert mgr.should_continue_exploring(session.session_id) is False

    def test_continue_when_below_goal(self):
        mgr = SessionManager()
        session = mgr.create_session(goal=3)
        card = mgr.add_card(session.session_id, "vid_y")
        mgr.update_card_status(session.session_id, card.card_id, "go_ready")
        assert mgr.should_continue_exploring(session.session_id) is True

    def test_unknown_session_returns_false(self):
        mgr = SessionManager()
        assert mgr.should_continue_exploring("no-such-session") is False


class TestBuildQueue:
    def test_enqueue_and_dequeue(self):
        q = BuildQueue()
        q.enqueue("card-1")
        result = q.dequeue()
        assert result == "card-1"

    def test_dequeue_empty_returns_none(self):
        q = BuildQueue()
        assert q.dequeue() is None

    def test_single_concurrent_build(self):
        q = BuildQueue()
        q.enqueue("card-1")
        q.enqueue("card-2")
        first = q.dequeue()
        second = q.dequeue()
        assert first == "card-1"
        assert second is None

    def test_is_building_false_initially(self):
        q = BuildQueue()
        assert q.is_building() is False

    def test_is_building_true_after_dequeue(self):
        q = BuildQueue()
        q.enqueue("card-1")
        q.dequeue()
        assert q.is_building() is True

    def test_mark_complete_releases_slot(self):
        q = BuildQueue()
        q.enqueue("card-1")
        q.enqueue("card-2")
        q.dequeue()
        q.mark_complete("card-1")
        assert q.is_building() is False
        next_card = q.dequeue()
        assert next_card == "card-2"

    def test_fifo_order_preserved(self):
        q = BuildQueue()
        for i in range(3):
            q.enqueue(f"card-{i}")
        results = []
        for _ in range(3):
            item = q.dequeue()
            results.append(item)
            if item:
                q.mark_complete(item)
        assert results == ["card-0", "card-1", "card-2"]
