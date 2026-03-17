import uuid
from collections import deque
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from agent.zero_prompt.events import (
    brainstorm_complete_event,
    brainstorm_start_event,
    compete_complete_event,
    compete_start_event,
    insight_complete_event,
    insight_start_event,
    paper_found_event,
    paper_search_event,
    session_start_event,
    transcript_complete_event,
    transcript_start_event,
    verdict_go_event,
    verdict_nogo_event,
)
from agent.zero_prompt.queue_manager import BuildQueue
from agent.zero_prompt.schemas import ZPCard, ZPSession

VerdictFn = Callable[[str, str, str], Awaitable[tuple[str, int, str, str]]]


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, ZPSession] = {}

    def create_session(self, goal: int = 10) -> ZPSession:
        session_id = str(uuid.uuid4())
        session = ZPSession(
            session_id=session_id,
            status="exploring",
            cards=[],
            build_queue=[],
            active_build=None,
            goal_go_cards=goal,
            created_at=datetime.now(tz=timezone.utc).isoformat(),
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> ZPSession | None:
        return self._sessions.get(session_id)

    def add_card(self, session_id: str, video_id: str) -> ZPCard | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        card = ZPCard(
            card_id=str(uuid.uuid4()),
            video_id=video_id,
            status="analyzing",
            score=0,
            thread_id=None,
        )
        session.cards.append(card)
        return card

    def update_card_status(self, session_id: str, card_id: str, status: str, **kwargs: object) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False
        for card in session.cards:
            if card.card_id == card_id:
                card.status = status  # type: ignore[assignment]
                for key, value in kwargs.items():
                    if hasattr(card, key):
                        setattr(card, key, value)
                return True
        return False

    def queue_build(self, session_id: str, card_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False
        if card_id not in session.build_queue:
            session.build_queue.append(card_id)
        return True

    def get_next_build(self, session_id: str) -> str | None:
        session = self._sessions.get(session_id)
        if session is None or not session.build_queue:
            return None
        bq = deque(session.build_queue)
        card_id = bq.popleft()
        session.build_queue = list(bq)
        session.active_build = card_id
        return card_id

    def pause_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False
        session.status = "paused"
        return True

    def resume_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False
        session.status = "exploring"
        return True

    def should_continue_exploring(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False
        go_ready_count = sum(1 for card in session.cards if card.status == "go_ready")
        return go_ready_count < session.goal_go_cards


class StreamingOrchestrator:
    def __init__(self) -> None:
        self._sessions: dict[str, ZPSession] = {}
        self._build_queues: dict[str, BuildQueue] = {}

    def create_session(self, goal: int = 10) -> tuple[ZPSession, dict]:
        session_id = str(uuid.uuid4())
        session = ZPSession(
            session_id=session_id,
            status="exploring",
            cards=[],
            build_queue=[],
            active_build=None,
            goal_go_cards=goal,
            created_at=datetime.now(tz=timezone.utc).isoformat(),
        )
        self._sessions[session_id] = session
        self._build_queues[session_id] = BuildQueue()
        event = session_start_event(session_id, goal)
        return session, event

    def get_session(self, session_id: str) -> ZPSession | None:
        return self._sessions.get(session_id)

    def should_continue_exploring(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None or session.status != "exploring":
            return False
        go_ready_count = sum(1 for card in session.cards if card.status == "go_ready")
        return go_ready_count < session.goal_go_cards

    async def exploration_step(
        self,
        session_id: str,
        video_id: str,
        *,
        verdict_fn: VerdictFn | None = None,
    ) -> list[dict]:
        session = self._sessions.get(session_id)
        if session is None:
            return []

        card_id = str(uuid.uuid4())
        card = ZPCard(
            card_id=card_id,
            video_id=video_id,
            status="analyzing",
            score=0,
            thread_id=None,
        )
        session.cards.append(card)

        events: list[dict] = []

        events.append(transcript_start_event(video_id))
        events.append(transcript_complete_event(video_id, "auto", 0))

        events.append(insight_start_event(video_id))
        events.append(insight_complete_event("unknown", 0, 0.0))

        events.append(paper_search_event("", ["openalex"]))
        events.append(paper_found_event(0, "openalex"))

        events.append(brainstorm_start_event("", 0))
        events.append(brainstorm_complete_event(0, 0, 0.0))

        events.append(compete_start_event(""))
        events.append(compete_complete_event(0, "medium", "normal"))

        if verdict_fn is not None:
            try:
                decision, score, reason, reason_code = await verdict_fn(session_id, video_id, card_id)
            except Exception:
                card.status = "nogo"
                card.score = 0
                events.append(verdict_nogo_event(0, "analysis_error", "verdict_exception"))
                return events
        else:
            decision, score, reason, reason_code = "GO", 75, "stub verdict", "high_potential"

        if decision == "GO":
            card.status = "go_ready"
            card.score = score
            events.append(verdict_go_event(score, reason, reason_code))
        else:
            card.status = "nogo"
            card.score = score
            events.append(verdict_nogo_event(score, reason, reason_code))

        return events

    def queue_build(self, session_id: str, card_id: str) -> dict:
        session = self._sessions.get(session_id)
        if session is None:
            return {"type": "zp.action.error", "error": "session_not_found"}

        card = next((c for c in session.cards if c.card_id == card_id), None)
        if card is None:
            return {"type": "zp.action.error", "error": "card_not_found"}

        if card.status != "go_ready":
            return {"type": "zp.action.error", "error": "card_not_go_ready"}

        bq = self._build_queues[session_id]
        bq.enqueue(card_id)

        if card_id not in session.build_queue:
            session.build_queue.append(card_id)

        card.status = "build_queued"
        return {"type": "zp.action.queue_build", "card_id": card_id, "queue_length": len(session.build_queue)}

    def pass_card(self, session_id: str, card_id: str) -> dict:
        session = self._sessions.get(session_id)
        if session is None:
            return {"type": "zp.action.error", "error": "session_not_found"}

        card = next((c for c in session.cards if c.card_id == card_id), None)
        if card is None:
            return {"type": "zp.action.error", "error": "card_not_found"}

        if card.status not in ("go_ready", "build_queued"):
            return {"type": "zp.action.error", "error": "card_not_passable"}

        if card_id in session.build_queue:
            session.build_queue.remove(card_id)

        bq = self._build_queues.get(session_id)
        if bq:
            bq.remove(card_id)

        card.status = "passed"
        return {"type": "zp.action.pass_card", "card_id": card_id}

    def delete_card(self, session_id: str, card_id: str) -> dict:
        session = self._sessions.get(session_id)
        if session is None:
            return {"type": "zp.action.error", "error": "session_not_found"}

        card = next((c for c in session.cards if c.card_id == card_id), None)
        if card is None:
            return {"type": "zp.action.error", "error": "card_not_found"}

        if card.status != "go_ready":
            return {"type": "zp.action.error", "error": "card_not_deletable"}

        card.status = "deleted"
        return {"type": "zp.action.delete_card", "card_id": card_id}

    def pause(self, session_id: str) -> dict:
        session = self._sessions.get(session_id)
        if session is None:
            return {"type": "zp.action.error", "error": "session_not_found"}

        session.status = "paused"
        return {"type": "zp.action.pause", "session_id": session_id}

    def resume(self, session_id: str) -> dict:
        session = self._sessions.get(session_id)
        if session is None:
            return {"type": "zp.action.error", "error": "session_not_found"}

        if session.status != "paused":
            return {"type": "zp.action.error", "error": "session_not_paused"}

        session.status = "exploring"
        return {"type": "zp.action.resume", "session_id": session_id}

    def start_next_build(self, session_id: str) -> str | None:
        bq = self._build_queues.get(session_id)
        if bq is None:
            return None

        card_id = bq.dequeue()
        if card_id is None:
            return None

        session = self._sessions.get(session_id)
        if session is None:
            return card_id

        session.active_build = card_id

        if card_id in session.build_queue:
            session.build_queue.remove(card_id)

        for card in session.cards:
            if card.card_id == card_id:
                card.status = "building"
                break

        return card_id

    def finish_build(
        self, session_id: str, card_id: str, *, success: bool = True, thread_id: str | None = None
    ) -> dict:
        session = self._sessions.get(session_id)
        if session is None:
            return {"type": "zp.action.error", "error": "session_not_found"}

        bq = self._build_queues.get(session_id)
        if bq:
            bq.mark_complete(card_id)

        if session.active_build == card_id:
            session.active_build = None

        for card in session.cards:
            if card.card_id == card_id:
                card.status = "deployed" if success else "build_failed"
                if thread_id is not None:
                    card.thread_id = thread_id
                break

        return {"type": "zp.build.complete" if success else "zp.build.failed", "card_id": card_id}
