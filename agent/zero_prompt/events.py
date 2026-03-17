ZP_SESSION_START = "zp.session.start"

ZP_SEARCH_START = "zp.search.start"
ZP_SEARCH_COMPLETE = "zp.search.complete"
ZP_SEARCH_ERROR = "zp.search.error"

ZP_PAPER_SEARCH = "zp.paper.search"
ZP_PAPER_FOUND = "zp.paper.found"
ZP_PAPER_ERROR = "zp.paper.error"

ZP_COMPETE_START = "zp.compete.start"
ZP_COMPETE_COMPLETE = "zp.compete.complete"
ZP_COMPETE_ERROR = "zp.compete.error"

ZP_BRAINSTORM_START = "zp.brainstorm.start"
ZP_BRAINSTORM_COMPLETE = "zp.brainstorm.complete"

ZP_GO = "zp.verdict.go"
ZP_NOGO = "zp.verdict.nogo"

ZP_TRANSCRIPT_START = "zp.transcript.start"
ZP_TRANSCRIPT_COMPLETE = "zp.transcript.complete"

ZP_INSIGHT_START = "zp.insight.start"
ZP_INSIGHT_COMPLETE = "zp.insight.complete"


def session_start_event(session_id: str, goal_go_cards: int) -> dict:
    return {
        "type": ZP_SESSION_START,
        "session_id": session_id,
        "goal_go_cards": goal_go_cards,
    }


def search_start_event(query: str, category: str) -> dict:
    return {
        "type": ZP_SEARCH_START,
        "query": query,
        "category": category,
    }


def search_complete_event(total: int, filtered: int) -> dict:
    return {
        "type": ZP_SEARCH_COMPLETE,
        "total_fetched": total,
        "after_filter": filtered,
    }


def search_error_event(error: str) -> dict:
    return {
        "type": ZP_SEARCH_ERROR,
        "error": error,
    }


def paper_search_event(query: str, sources: list[str]) -> dict:
    return {
        "type": ZP_PAPER_SEARCH,
        "query": query,
        "sources": sources,
    }


def paper_found_event(total: int, source: str) -> dict:
    return {
        "type": ZP_PAPER_FOUND,
        "total": total,
        "source": source,
    }


def paper_error_event(source: str, error: str) -> dict:
    return {
        "type": ZP_PAPER_ERROR,
        "source": source,
        "error": error,
    }


def compete_start_event(query: str) -> dict:
    return {
        "type": ZP_COMPETE_START,
        "query": query,
    }


def compete_complete_event(competitors: int, saturation: str, confidence: str) -> dict:
    return {
        "type": ZP_COMPETE_COMPLETE,
        "competitors_found": competitors,
        "saturation_level": saturation,
        "search_confidence": confidence,
    }


def compete_error_event(error: str) -> dict:
    return {
        "type": ZP_COMPETE_ERROR,
        "error": error,
    }


def verdict_go_event(score: int, reason: str, reason_code: str) -> dict:
    return {
        "type": ZP_GO,
        "score": score,
        "reason": reason,
        "reason_code": reason_code,
    }


def verdict_nogo_event(score: int, reason: str, reason_code: str) -> dict:
    return {
        "type": ZP_NOGO,
        "score": score,
        "reason": reason,
        "reason_code": reason_code,
    }


def brainstorm_start_event(idea: str, paper_count: int) -> dict:
    return {
        "type": ZP_BRAINSTORM_START,
        "idea": idea,
        "paper_count": paper_count,
    }


def brainstorm_complete_event(novel_features: int, unexplored_angles: int, novelty_boost: float) -> dict:
    return {
        "type": ZP_BRAINSTORM_COMPLETE,
        "novel_features": novel_features,
        "unexplored_angles": unexplored_angles,
        "novelty_boost": novelty_boost,
    }


def insight_start_event(video_title: str) -> dict:
    return {
        "type": ZP_INSIGHT_START,
        "video_title": video_title,
    }


def insight_complete_event(domain: str, features_found: int, confidence: float) -> dict:
    return {
        "type": ZP_INSIGHT_COMPLETE,
        "domain": domain,
        "features_found": features_found,
        "confidence_score": confidence,
    }


def transcript_start_event(video_id: str) -> dict:
    return {
        "type": ZP_TRANSCRIPT_START,
        "video_id": video_id,
    }


def transcript_complete_event(video_id: str, source: str, token_count: int) -> dict:
    return {
        "type": ZP_TRANSCRIPT_COMPLETE,
        "video_id": video_id,
        "source": source,
        "token_count": token_count,
    }
