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
