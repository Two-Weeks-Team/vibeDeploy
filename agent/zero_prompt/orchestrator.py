import uuid
from collections import deque
from datetime import datetime, timezone

from agent.zero_prompt.schemas import ZPCard, ZPSession


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
            status="processing",
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
