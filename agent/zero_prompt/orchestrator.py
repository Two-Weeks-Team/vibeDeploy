import asyncio
import logging
import uuid
from collections import deque
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from agent.zero_prompt.event_bus import push_zp_event
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

logger = logging.getLogger(__name__)

VerdictFn = Callable[[str, str, str], Awaitable[tuple[str, int, str, str]]]


def _fire(coro: object) -> None:
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)  # type: ignore[arg-type]
    except RuntimeError:
        if hasattr(coro, "close"):
            coro.close()  # type: ignore[union-attr]
    except Exception:
        if hasattr(coro, "close"):
            coro.close()  # type: ignore[union-attr]


async def _db_update_card_safe(card_id: str, **fields: object) -> None:
    try:
        from agent.db import zp_store

        await zp_store.update_card(card_id, **fields)
    except Exception:
        logger.exception("[ZP] DB update failed for card %s fields=%s", card_id, list(fields.keys()))


async def _db_update_session_safe(session_id: str, status: str) -> None:
    try:
        from agent.db import zp_store

        await zp_store.update_session_status(session_id, status)
    except Exception:
        pass


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
        _fire(self._db_create_session(session_id, goal))
        return session, event

    async def _db_create_session(self, session_id: str, goal: int) -> None:
        try:
            from agent.db import zp_store

            await zp_store.ensure_session(session_id, goal)
        except Exception:
            pass

    def get_session(self, session_id: str) -> ZPSession | None:
        return self._sessions.get(session_id)

    def should_continue_exploring(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None or session.status != "exploring":
            return False
        go_ready_count = sum(1 for card in session.cards if card.status == "go_ready")
        return go_ready_count < session.goal_go_cards

    async def register_card(self, session_id: str, video_id: str, title: str = "") -> str:
        card_id = str(uuid.uuid4())
        card = ZPCard(card_id=card_id, video_id=video_id, status="analyzing", score=0, title=title or video_id)
        session = self._sessions.get(session_id)
        if session:
            session.cards.append(card)
        try:
            from agent.db import zp_store

            await zp_store.add_card(session_id, card_id, video_id, title or video_id)
        except Exception:
            logger.exception("[ZP] Failed to add card %s to DB", card_id)
        return card_id

    async def exploration_step(
        self,
        session_id: str,
        video_id: str,
        *,
        video_title: str = "",
        video_description: str = "",
        verdict_fn: VerdictFn | None = None,
    ) -> list[dict]:
        session = self._sessions.get(session_id)
        if session is None:
            return []

        card = next((c for c in session.cards if c.video_id == video_id and c.status == "analyzing"), None)
        if card is None:
            card_id = str(uuid.uuid4())
            card = ZPCard(
                card_id=card_id, video_id=video_id, status="analyzing", score=0, title=video_title or video_id
            )
            session.cards.append(card)
        card_id = card.card_id
        events: list[dict] = []

        try:
            from agent.db import zp_store

            await zp_store.add_card(session_id, card_id, video_id, video_title or video_id)
        except Exception:
            pass
        card.analysis_step = "transcript"
        push_zp_event(
            {
                "type": "card.update",
                "card_id": card_id,
                "status": "analyzing",
                "analysis_step": "transcript",
                "session_id": session_id,
            }
        )
        await _db_update_card_safe(card_id, analysis_step="transcript")

        events.append(transcript_start_event(video_id))
        try:
            from agent.zero_prompt.transcript import fetch_transcript_artifact

            transcript = await fetch_transcript_artifact(video_id)
            transcript_text = transcript.text
            events.append(transcript_complete_event(video_id, transcript.source, transcript.token_count))
        except Exception:
            transcript_text = video_description or video_title or ""
            events.append(transcript_complete_event(video_id, "error", 0))

        card.analysis_step = "insight"
        await _db_update_card_safe(card_id, analysis_step="insight")
        push_zp_event(
            {
                "type": "card.update",
                "card_id": card_id,
                "status": "analyzing",
                "analysis_step": "insight",
                "title": card.title,
                "session_id": session_id,
            }
        )
        events.append(insight_start_event(video_id))
        try:
            from agent.zero_prompt.insight_extractor import extract_insight_from_transcript, extract_with_gemini

            idea = await extract_with_gemini(transcript_text)
            if idea is None:
                idea = extract_insight_from_transcript(transcript_text, video_title)
            events.append(insight_complete_event(idea.domain, len(idea.key_features), idea.confidence_score))
        except Exception:
            from agent.zero_prompt.schemas import AppIdea

            idea = AppIdea(name=video_title or video_id, domain="unknown", description="", target_audience="")
            events.append(insight_complete_event("unknown", 0, 0.0))

        try:
            await _db_update_card_safe(card_id, domain=idea.domain if idea else "unknown")
        except Exception:
            pass

        card.analysis_step = "papers"
        await _db_update_card_safe(card_id, analysis_step="papers")
        push_zp_event(
            {
                "type": "card.update",
                "card_id": card_id,
                "status": "analyzing",
                "analysis_step": "papers",
                "title": card.title,
                "session_id": session_id,
            }
        )
        idea_query = f"{idea.name} {idea.domain}" if idea.name else video_title
        events.append(paper_search_event(idea_query, ["openalex", "arxiv"]))
        try:
            from agent.zero_prompt.paper_search import search_papers

            papers = await search_papers(idea_query, max_results=3)
            events.append(paper_found_event(len(papers), "openalex+arxiv"))
        except Exception:
            papers = []
            events.append(paper_found_event(0, "error"))

        try:
            await _db_update_card_safe(card_id, papers_found=len(papers) if papers else 0)
        except Exception:
            pass

        card.analysis_step = "brainstorm"
        await _db_update_card_safe(card_id, analysis_step="brainstorm")
        push_zp_event(
            {
                "type": "card.update",
                "card_id": card_id,
                "status": "analyzing",
                "analysis_step": "brainstorm",
                "title": card.title,
                "session_id": session_id,
            }
        )
        events.append(brainstorm_start_event(idea.name or video_title, len(papers)))
        try:
            from agent.zero_prompt.paper_brainstorm import enhance_idea_with_papers

            enhanced = enhance_idea_with_papers(idea.description or idea.name, papers)
            novelty_boost = enhanced.novelty_boost
            events.append(
                brainstorm_complete_event(len(enhanced.novel_features), len(enhanced.unexplored_angles), novelty_boost)
            )
        except Exception:
            novelty_boost = 0.0
            events.append(brainstorm_complete_event(0, 0, 0.0))

        try:
            await _db_update_card_safe(card_id, novelty_boost=novelty_boost)
        except Exception:
            pass

        card.analysis_step = "compete"
        await _db_update_card_safe(card_id, analysis_step="compete")
        push_zp_event(
            {
                "type": "card.update",
                "card_id": card_id,
                "status": "analyzing",
                "analysis_step": "compete",
                "title": card.title,
                "session_id": session_id,
            }
        )
        events.append(compete_start_event(idea.name or video_title))
        market = None
        try:
            from agent.zero_prompt.competitive_analysis import analyze_competition

            market = await analyze_competition(idea.name or video_title)
            market_opportunity = market.market_opportunity_score
            events.append(
                compete_complete_event(len(market.competitors), market.saturation_level, market.search_confidence)
            )
        except Exception:
            market_opportunity = 50
            events.append(compete_complete_event(0, "medium", "llm_only"))

        try:
            await _db_update_card_safe(
                card_id,
                competitors_found=str(len(market.competitors)) if market else "0",
                saturation=market.saturation_level if market else "",
            )
        except Exception:
            pass

        card.analysis_step = "verdict"
        await _db_update_card_safe(card_id, analysis_step="verdict")
        push_zp_event(
            {
                "type": "card.update",
                "card_id": card_id,
                "status": "analyzing",
                "analysis_step": "verdict",
                "title": card.title,
                "session_id": session_id,
            }
        )

        if verdict_fn is not None:
            try:
                decision, score, reason, reason_code = await verdict_fn(session_id, video_id, card_id)
            except Exception:
                card.status = "nogo"
                events.append(verdict_nogo_event(0, "analysis_error", "verdict_exception"))
                _fire(_db_update_card_safe(card_id, status="nogo"))
                push_zp_event({"type": "card.update", "card_id": card_id, "status": "nogo", "session_id": session_id})
                return events
        else:
            try:
                from agent.zero_prompt.verdict import compute_verdict_score, determine_verdict

                raw_confidence = idea.confidence_score if idea else 0.5
                confidence = max(raw_confidence, 0.65)
                engagement = max(0.55, min(1.0, len(papers) * 0.2 + 0.35)) if papers else 0.55
                differentiation = max(50, 100 - (market_opportunity if market_opportunity > 60 else 20))
                score = compute_verdict_score(
                    confidence, engagement, market_opportunity, novelty_boost, differentiation
                )
                verdict = determine_verdict(score, market_opportunity, novelty_boost, differentiation)
                decision = verdict.decision
                reason = verdict.reason
                reason_code = verdict.reason_code
                score = verdict.score
            except Exception:
                decision, score, reason, reason_code = "GO", 70, "default verdict", "high_potential"

        card.title = idea.name or video_title or video_id
        card.score = score
        card.reason = reason
        card.reason_code = reason_code
        card.domain = idea.domain if idea else ""
        card.papers_found = len(papers) if papers else 0
        card.competitors_found = str(len(market.competitors)) if market else "0"
        card.saturation = market.saturation_level if market else ""
        card.novelty_boost = novelty_boost

        if decision == "GO":
            card.status = "go_ready"
            events.append(verdict_go_event(score, reason, reason_code))

            try:
                await _db_update_card_safe(
                    card_id,
                    title=card.title,
                    status="go_ready",
                    score=score,
                    reason=reason,
                    reason_code=reason_code,
                    domain=card.domain,
                    papers_found=card.papers_found,
                    competitors_found=card.competitors_found,
                    saturation=card.saturation,
                    novelty_boost=novelty_boost,
                )
                push_zp_event(
                    {"type": "card.update", "card_id": card_id, "status": "go_ready", "session_id": session_id}
                )
            except Exception:
                pass

            try:
                from agent.zero_prompt.card_enrichment import enrich_card_with_gemini

                enrichment = await enrich_card_with_gemini(
                    video_title=video_title,
                    transcript_text=transcript_text,
                    idea_name=idea.name if idea else "",
                    idea_domain=idea.domain if idea else "",
                    idea_features=idea.key_features if idea else [],
                    paper_titles=[p.title for p in papers[:3]] if papers else [],
                    market_gaps=market.gaps if market else [],
                    competitors_count=len(market.competitors) if market else 0,
                )
                card.video_summary = enrichment.get("video_summary", "")
                card.insights = enrichment.get("insights", [])
                card.mvp_proposal = enrichment.get("mvp_proposal", {})
                try:
                    await _db_update_card_safe(
                        card_id,
                        video_summary=card.video_summary,
                        insights=card.insights,
                        mvp_proposal=card.mvp_proposal,
                    )
                    push_zp_event(
                        {"type": "card.enriched", "card_id": card_id, "status": "go_ready", "session_id": session_id}
                    )
                except Exception:
                    pass
            except Exception:
                logger.exception("[ZP] Card enrichment failed for %s", card_id)
        else:
            card.status = "nogo"
            events.append(verdict_nogo_event(score, reason, reason_code))
            try:
                await _db_update_card_safe(
                    card_id,
                    title=card.title,
                    status="nogo",
                    score=score,
                    reason=reason,
                    reason_code=reason_code,
                    domain=card.domain,
                    papers_found=card.papers_found,
                    competitors_found=card.competitors_found,
                    saturation=card.saturation,
                    novelty_boost=novelty_boost,
                )
                push_zp_event({"type": "card.update", "card_id": card_id, "status": "nogo", "session_id": session_id})
            except Exception:
                pass

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
        _fire(_db_update_card_safe(card_id, status="build_queued"))
        push_zp_event({"type": "card.update", "card_id": card_id, "status": "build_queued", "session_id": session_id})
        return {"type": "zp.action.queue_build", "card_id": card_id, "queue_length": len(session.build_queue)}

    def pass_card(self, session_id: str, card_id: str) -> dict:
        session = self._sessions.get(session_id)
        card = None
        if session:
            card = next((c for c in session.cards if c.card_id == card_id), None)
            if card and card_id in session.build_queue:
                session.build_queue.remove(card_id)
            bq = self._build_queues.get(session_id)
            if bq:
                bq.remove(card_id)

        if card:
            card.status = "passed"
        _fire(_db_update_card_safe(card_id, status="passed"))
        push_zp_event({"type": "card.update", "card_id": card_id, "status": "passed", "session_id": session_id})
        return {"type": "zp.action.pass_card", "card_id": card_id}

    def delete_card(self, session_id: str, card_id: str) -> dict:
        session = self._sessions.get(session_id)
        card = None
        if session:
            card = next((c for c in session.cards if c.card_id == card_id), None)

        if card:
            card.status = "deleted"
        _fire(_db_update_card_safe(card_id, status="deleted"))
        push_zp_event(
            {
                "type": "card.update",
                "card_id": card_id,
                "status": "deleted",
                "title": card.title if card else "",
                "session_id": session_id,
            }
        )
        return {"type": "zp.action.delete_card", "card_id": card_id}

    def pause(self, session_id: str) -> dict:
        session = self._sessions.get(session_id)
        if session is None:
            return {"type": "zp.action.error", "error": "session_not_found"}

        session.status = "paused"
        _fire(_db_update_session_safe(session_id, "paused"))
        return {"type": "zp.action.pause", "session_id": session_id}

    def resume(self, session_id: str) -> dict:
        session = self._sessions.get(session_id)
        if session is None:
            return {"type": "zp.action.error", "error": "session_not_found"}

        if session.status != "paused":
            return {"type": "zp.action.error", "error": "session_not_paused"}

        session.status = "exploring"
        _fire(_db_update_session_safe(session_id, "exploring"))
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

        _fire(_db_update_card_safe(card_id, status="building"))
        push_zp_event({"type": "card.update", "card_id": card_id, "status": "building", "session_id": session_id})
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

        final_status = "deployed" if success else "build_failed"
        for card in session.cards:
            if card.card_id == card_id:
                card.status = final_status  # type: ignore[assignment]
                if thread_id is not None:
                    card.thread_id = thread_id
                break

        db_fields: dict[str, object] = {"status": final_status}
        if thread_id is not None:
            db_fields["thread_id"] = thread_id
        _fire(_db_update_card_safe(card_id, **db_fields))
        push_zp_event({"type": "card.update", "card_id": card_id, "status": final_status, "session_id": session_id})

        return {"type": "zp.build.complete" if success else "zp.build.failed", "card_id": card_id}
