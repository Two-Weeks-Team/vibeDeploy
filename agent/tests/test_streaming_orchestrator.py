import pytest

from agent.zero_prompt.events import ZP_GO, ZP_NOGO, ZP_SESSION_START
from agent.zero_prompt.orchestrator import StreamingOrchestrator
from agent.zero_prompt.schemas import ZPCard, ZPSession


async def _go_verdict(session_id: str, video_id: str, card_id: str) -> tuple[str, int, str, str]:
    return "GO", 80, "high potential", "high_potential"


async def _nogo_verdict(session_id: str, video_id: str, card_id: str) -> tuple[str, int, str, str]:
    return "NO_GO", 30, "saturated market", "market_saturated"


class TestCreateSession:
    def test_create_session_returns_session_and_event(self):
        orch = StreamingOrchestrator()
        session, event = orch.create_session(goal=5)
        assert isinstance(session, ZPSession)
        assert session.goal_go_cards == 5
        assert session.status == "exploring"
        assert event["type"] == ZP_SESSION_START
        assert event["session_id"] == session.session_id
        assert event["goal_go_cards"] == 5

    def test_create_session_emits_session_start(self):
        orch = StreamingOrchestrator()
        _session, event = orch.create_session()
        assert event["type"] == ZP_SESSION_START

    def test_unique_session_ids(self):
        orch = StreamingOrchestrator()
        s1, _ = orch.create_session()
        s2, _ = orch.create_session()
        assert s1.session_id != s2.session_id

    def test_get_session_returns_created(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session()
        found = orch.get_session(session.session_id)
        assert found is not None
        assert found.session_id == session.session_id

    def test_get_session_unknown_returns_none(self):
        orch = StreamingOrchestrator()
        assert orch.get_session("no-such-id") is None


class TestShouldContinueExploring:
    def test_continues_when_no_go_ready(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session(goal=3)
        assert orch.should_continue_exploring(session.session_id) is True

    def test_stops_when_goal_reached(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session(goal=2)
        for i in range(2):
            import uuid

            from agent.zero_prompt.schemas import ZPCard

            card = ZPCard(card_id=str(uuid.uuid4()), video_id=f"v{i}", status="go_ready", score=80)
            session.cards.append(card)
        assert orch.should_continue_exploring(session.session_id) is False

    def test_continues_when_below_goal(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session(goal=3)
        import uuid

        from agent.zero_prompt.schemas import ZPCard

        card = ZPCard(card_id=str(uuid.uuid4()), video_id="v1", status="go_ready", score=80)
        session.cards.append(card)
        assert orch.should_continue_exploring(session.session_id) is True

    def test_paused_session_does_not_continue(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session(goal=5)
        orch.pause(session.session_id)
        assert orch.should_continue_exploring(session.session_id) is False

    def test_unknown_session_returns_false(self):
        orch = StreamingOrchestrator()
        assert orch.should_continue_exploring("no-such") is False


class TestExplorationStep:
    @pytest.mark.asyncio
    async def test_step_creates_card(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session()
        await orch.exploration_step(session.session_id, "vid_001")
        assert len(session.cards) == 1
        assert session.cards[0].video_id == "vid_001"

    @pytest.mark.asyncio
    async def test_step_go_verdict_sets_go_ready(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session()
        await orch.exploration_step(session.session_id, "vid_001", verdict_fn=_go_verdict)
        assert session.cards[0].status == "go_ready"
        assert session.cards[0].score == 80

    @pytest.mark.asyncio
    async def test_step_nogo_verdict_sets_nogo(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session()
        await orch.exploration_step(session.session_id, "vid_001", verdict_fn=_nogo_verdict)
        assert session.cards[0].status == "nogo"
        assert session.cards[0].score == 30

    @pytest.mark.asyncio
    async def test_step_emits_go_verdict_event(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session()
        events = await orch.exploration_step(session.session_id, "vid_001", verdict_fn=_go_verdict)
        verdict_events = [e for e in events if e["type"] == ZP_GO]
        assert len(verdict_events) == 1

    @pytest.mark.asyncio
    async def test_step_emits_nogo_verdict_event(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session()
        events = await orch.exploration_step(session.session_id, "vid_001", verdict_fn=_nogo_verdict)
        verdict_events = [e for e in events if e["type"] == ZP_NOGO]
        assert len(verdict_events) == 1

    @pytest.mark.asyncio
    async def test_step_returns_empty_for_unknown_session(self):
        orch = StreamingOrchestrator()
        events = await orch.exploration_step("no-such-session", "vid_x")
        assert events == []

    @pytest.mark.asyncio
    async def test_step_pipeline_order_transcript_first(self):
        from agent.zero_prompt.events import ZP_TRANSCRIPT_START

        orch = StreamingOrchestrator()
        session, _ = orch.create_session()
        events = await orch.exploration_step(session.session_id, "vid_001", verdict_fn=_go_verdict)
        assert events[0]["type"] == ZP_TRANSCRIPT_START

    @pytest.mark.asyncio
    async def test_step_pipeline_order_verdict_last(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session()
        events = await orch.exploration_step(session.session_id, "vid_001", verdict_fn=_go_verdict)
        assert events[-1]["type"] == ZP_GO

    @pytest.mark.asyncio
    async def test_discovery_pauses_at_goal_slots(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session(goal=2)
        await orch.exploration_step(session.session_id, "v1", verdict_fn=_go_verdict)
        await orch.exploration_step(session.session_id, "v2", verdict_fn=_go_verdict)
        assert orch.should_continue_exploring(session.session_id) is False


class TestQueueBuild:
    @pytest.mark.asyncio
    async def test_queue_build_transitions_to_build_queued(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session()
        await orch.exploration_step(session.session_id, "v1", verdict_fn=_go_verdict)
        card = session.cards[0]
        result = orch.queue_build(session.session_id, card.card_id)
        assert result["type"] == "zp.action.queue_build"
        assert card.status == "build_queued"

    @pytest.mark.asyncio
    async def test_queue_build_adds_to_build_queue(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session()
        await orch.exploration_step(session.session_id, "v1", verdict_fn=_go_verdict)
        card = session.cards[0]
        orch.queue_build(session.session_id, card.card_id)
        assert card.card_id in session.build_queue

    @pytest.mark.asyncio
    async def test_queue_build_fifo_order(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session(goal=10)
        await orch.exploration_step(session.session_id, "v1", verdict_fn=_go_verdict)
        await orch.exploration_step(session.session_id, "v2", verdict_fn=_go_verdict)
        c1 = session.cards[0]
        c2 = session.cards[1]
        orch.queue_build(session.session_id, c1.card_id)
        orch.queue_build(session.session_id, c2.card_id)
        first = orch.start_next_build(session.session_id)
        second = orch.start_next_build(session.session_id)
        assert first == c1.card_id
        assert second is None

    def test_queue_build_unknown_session_returns_error(self):
        orch = StreamingOrchestrator()
        result = orch.queue_build("no-such", "some-card")
        assert result["type"] == "zp.action.error"

    @pytest.mark.asyncio
    async def test_queue_build_non_go_ready_returns_error(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session()
        await orch.exploration_step(session.session_id, "v1", verdict_fn=_nogo_verdict)
        card = session.cards[0]
        result = orch.queue_build(session.session_id, card.card_id)
        assert result["type"] == "zp.action.error"
        assert result["error"] == "card_not_go_ready"


class TestPassCard:
    @pytest.mark.asyncio
    async def test_pass_go_ready_card(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session()
        await orch.exploration_step(session.session_id, "v1", verdict_fn=_go_verdict)
        card = session.cards[0]
        result = orch.pass_card(session.session_id, card.card_id)
        assert result["type"] == "zp.action.pass_card"
        assert card.status == "passed"

    @pytest.mark.asyncio
    async def test_pass_build_queued_card_removes_from_queue(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session()
        await orch.exploration_step(session.session_id, "v1", verdict_fn=_go_verdict)
        card = session.cards[0]
        orch.queue_build(session.session_id, card.card_id)
        assert card.card_id in session.build_queue
        orch.pass_card(session.session_id, card.card_id)
        assert card.card_id not in session.build_queue
        assert card.status == "passed"

    @pytest.mark.asyncio
    async def test_pass_card_frees_slot_and_discovery_resumes(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session(goal=1)
        await orch.exploration_step(session.session_id, "v1", verdict_fn=_go_verdict)
        assert orch.should_continue_exploring(session.session_id) is False
        card = session.cards[0]
        orch.pass_card(session.session_id, card.card_id)
        assert orch.should_continue_exploring(session.session_id) is True

    def test_pass_unknown_session_returns_error(self):
        orch = StreamingOrchestrator()
        result = orch.pass_card("no-such", "card-1")
        assert result["type"] == "zp.action.pass_card"


class TestDeleteCard:
    @pytest.mark.asyncio
    async def test_delete_go_ready_card(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session()
        await orch.exploration_step(session.session_id, "v1", verdict_fn=_go_verdict)
        card = session.cards[0]
        result = orch.delete_card(session.session_id, card.card_id)
        assert result["type"] == "zp.action.delete_card"
        assert card.status == "deleted"

    @pytest.mark.asyncio
    async def test_delete_nogo_card_succeeds(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session()
        await orch.exploration_step(session.session_id, "v1", verdict_fn=_nogo_verdict)
        card = session.cards[0]
        result = orch.delete_card(session.session_id, card.card_id)
        assert result["type"] == "zp.action.delete_card"
        assert card.status == "deleted"

    def test_delete_building_card_returns_error(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session()
        card = ZPCard(card_id="c1", video_id="v1", status="building", score=70)
        session.cards.append(card)
        result = orch.delete_card(session.session_id, "c1")
        assert result["type"] == "zp.action.delete_card"


class TestPauseResume:
    def test_pause_sets_paused(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session()
        result = orch.pause(session.session_id)
        assert result["type"] == "zp.action.pause"
        assert session.status == "paused"

    def test_resume_sets_exploring(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session()
        orch.pause(session.session_id)
        result = orch.resume(session.session_id)
        assert result["type"] == "zp.action.resume"
        assert session.status == "exploring"

    def test_resume_non_paused_returns_error(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session()
        result = orch.resume(session.session_id)
        assert result["type"] == "zp.action.error"
        assert result["error"] == "session_not_paused"

    def test_pause_unknown_session_returns_error(self):
        orch = StreamingOrchestrator()
        result = orch.pause("no-such")
        assert result["type"] == "zp.action.error"


class TestStartNextBuild:
    @pytest.mark.asyncio
    async def test_start_next_build_dequeues_card(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session(goal=10)
        await orch.exploration_step(session.session_id, "v1", verdict_fn=_go_verdict)
        card = session.cards[0]
        orch.queue_build(session.session_id, card.card_id)
        result = orch.start_next_build(session.session_id)
        assert result == card.card_id
        assert card.status == "building"
        assert session.active_build == card.card_id

    @pytest.mark.asyncio
    async def test_start_next_build_max_one_concurrent(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session(goal=10)
        await orch.exploration_step(session.session_id, "v1", verdict_fn=_go_verdict)
        await orch.exploration_step(session.session_id, "v2", verdict_fn=_go_verdict)
        c1, c2 = session.cards[0], session.cards[1]
        orch.queue_build(session.session_id, c1.card_id)
        orch.queue_build(session.session_id, c2.card_id)
        first = orch.start_next_build(session.session_id)
        second = orch.start_next_build(session.session_id)
        assert first == c1.card_id
        assert second is None

    def test_start_next_build_empty_queue_returns_none(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session()
        assert orch.start_next_build(session.session_id) is None

    def test_start_next_build_unknown_session_returns_none(self):
        orch = StreamingOrchestrator()
        assert orch.start_next_build("no-such") is None


class TestFinishBuild:
    @pytest.mark.asyncio
    async def test_finish_build_success_sets_built(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session(goal=10)
        await orch.exploration_step(session.session_id, "v1", verdict_fn=_go_verdict)
        card = session.cards[0]
        orch.queue_build(session.session_id, card.card_id)
        orch.start_next_build(session.session_id)
        result = orch.finish_build(session.session_id, card.card_id, success=True, thread_id="thread-123")
        assert result["type"] == "zp.build.complete"
        assert card.status == "deployed"
        assert card.thread_id == "thread-123"
        assert session.active_build is None

    @pytest.mark.asyncio
    async def test_finish_build_failure_marks_build_failed(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session(goal=10)
        await orch.exploration_step(session.session_id, "v1", verdict_fn=_go_verdict)
        card = session.cards[0]
        orch.queue_build(session.session_id, card.card_id)
        orch.start_next_build(session.session_id)
        result = orch.finish_build(session.session_id, card.card_id, success=False)
        assert result["type"] == "zp.build.failed"
        assert card.status == "build_failed"

    @pytest.mark.asyncio
    async def test_finish_build_releases_slot_for_next(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session(goal=10)
        await orch.exploration_step(session.session_id, "v1", verdict_fn=_go_verdict)
        await orch.exploration_step(session.session_id, "v2", verdict_fn=_go_verdict)
        c1, c2 = session.cards[0], session.cards[1]
        orch.queue_build(session.session_id, c1.card_id)
        orch.queue_build(session.session_id, c2.card_id)
        orch.start_next_build(session.session_id)
        orch.finish_build(session.session_id, c1.card_id)
        next_build = orch.start_next_build(session.session_id)
        assert next_build == c2.card_id

    def test_finish_build_unknown_session_returns_error(self):
        orch = StreamingOrchestrator()
        result = orch.finish_build("no-such", "card-1")
        assert result["type"] == "zp.action.error"


class TestSessionSnapshot:
    @pytest.mark.asyncio
    async def test_session_snapshot_recoverable(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session(goal=5)
        await orch.exploration_step(session.session_id, "v1", verdict_fn=_go_verdict)
        await orch.exploration_step(session.session_id, "v2", verdict_fn=_nogo_verdict)
        recovered = orch.get_session(session.session_id)
        assert recovered is not None
        assert len(recovered.cards) == 2
        statuses = {c.status for c in recovered.cards}
        assert "go_ready" in statuses
        assert "nogo" in statuses

    @pytest.mark.asyncio
    async def test_build_handoff_uses_thread_id_link(self):
        orch = StreamingOrchestrator()
        session, _ = orch.create_session(goal=10)
        await orch.exploration_step(session.session_id, "v1", verdict_fn=_go_verdict)
        card = session.cards[0]
        orch.queue_build(session.session_id, card.card_id)
        orch.start_next_build(session.session_id)
        orch.finish_build(session.session_id, card.card_id, thread_id="build-thread-abc")
        recovered = orch.get_session(session.session_id)
        assert recovered is not None
        linked_card = next(c for c in recovered.cards if c.card_id == card.card_id)
        assert linked_card.thread_id == "build-thread-abc"
