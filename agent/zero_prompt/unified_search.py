import asyncio
import logging
import os
import re
from collections import defaultdict

import httpx

from .schemas import SearchResult

logger = logging.getLogger(__name__)

_BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
_EXA_TOKEN_URL = "https://exa.ai/api/token/issue"
_EXA_SEARCH_URL = "https://exa.ai/api/search"
_REQUEST_TIMEOUT = 15.0


def _normalize_url(url: str) -> str:
    return re.sub(r"https?://(www\.)?", "", url).rstrip("/").lower()


async def _search_brave(query: str, limit: int = 5) -> list[SearchResult]:
    api_key = os.getenv("BRAVE_API_KEY", "").strip()
    if not api_key:
        return []

    async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
        resp = await client.get(
            _BRAVE_SEARCH_URL,
            headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
            params={"q": query, "count": limit},
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("description"),
                source="brave",
            )
            for r in data.get("web", {}).get("results", [])[:limit]
        ]


async def _search_exa(query: str, limit: int = 5) -> list[SearchResult]:
    api_key = os.getenv("EXA_API_KEY", "").strip()

    async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
        if api_key:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        else:
            token_resp = await client.post(_EXA_TOKEN_URL, headers={"Content-Type": "application/json"}, json={})
            token_resp.raise_for_status()
            token = token_resp.json().get("token")
            if not token:
                return []
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        resp = await client.post(
            _EXA_SEARCH_URL,
            headers=headers,
            json={"query": query, "numResults": limit},
        )
        resp.raise_for_status()
        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("text"),
                source="exa",
            )
            for r in resp.json().get("results", [])[:limit]
        ]


def _merge_and_score(results: list[SearchResult]) -> list[SearchResult]:
    groups: dict[str, list[SearchResult]] = defaultdict(list)
    for r in results:
        if not r.url:
            continue
        groups[_normalize_url(r.url)].append(r)

    merged: list[SearchResult] = []
    for group in groups.values():
        sources = {r.source for r in group}
        best = group[0]
        for r in group:
            if r.snippet:
                best = r
                break
        merged.append(
            SearchResult(
                title=best.title,
                url=best.url,
                snippet=best.snippet,
                source=",".join(sorted(sources)),
                confidence="high" if len(sources) > 1 else "normal",
            )
        )

    return sorted(merged, key=lambda r: 0 if r.confidence == "high" else 1)


async def unified_search(query: str, limit: int = 5) -> list[SearchResult]:
    brave_task = asyncio.create_task(_search_brave(query, limit))
    exa_task = asyncio.create_task(_search_exa(query, limit))

    brave_results, exa_results = await asyncio.gather(brave_task, exa_task, return_exceptions=True)

    if isinstance(brave_results, Exception):
        logger.warning("[UnifiedSearch] Brave failed: %s", str(brave_results)[:200])
        brave_results = []
    if isinstance(exa_results, Exception):
        logger.warning("[UnifiedSearch] Exa failed: %s", str(exa_results)[:200])
        exa_results = []

    all_results = brave_results + exa_results
    return _merge_and_score(all_results)
