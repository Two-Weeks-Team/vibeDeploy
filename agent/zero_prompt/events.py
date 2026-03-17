ZP_SEARCH_START = "zp.search.start"
ZP_SEARCH_COMPLETE = "zp.search.complete"
ZP_SEARCH_ERROR = "zp.search.error"


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
