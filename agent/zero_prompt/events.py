ZP_SEARCH_START = "zp.search.start"
ZP_SEARCH_COMPLETE = "zp.search.complete"
ZP_SEARCH_ERROR = "zp.search.error"

ZP_PAPER_SEARCH = "zp.paper.search"
ZP_PAPER_FOUND = "zp.paper.found"
ZP_PAPER_ERROR = "zp.paper.error"


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
