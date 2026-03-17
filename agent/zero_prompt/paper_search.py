import asyncio
import logging
import os
import random
import time
import xml.etree.ElementTree as ET
from collections import OrderedDict

import httpx

from .schemas import PaperMetadata

logger = logging.getLogger(__name__)

_OPENALEX_WORKS_URL = "https://api.openalex.org/works"
_ARXIV_API_URL = "http://export.arxiv.org/api/query"

_REQUEST_TIMEOUT_SECONDS = 10
_OPENALEX_MAX_RETRIES = 2
_ARXIV_MAX_RETRIES = 1

_CACHE_MAX_SIZE = 128
_CACHE: OrderedDict[str, tuple[float, list[PaperMetadata]]] = OrderedDict()
_CACHE_TTL_SECONDS = 86400

_ARXIV_LAST_REQUEST: float = 0.0
_ARXIV_THROTTLE_SECONDS = 3.0
_ARXIV_LOCK = asyncio.Lock()


def _cache_key(query: str, max_results: int) -> str:
    return f"{query.strip().lower()}:{max_results}"


def _is_cache_valid(key: str) -> bool:
    if key not in _CACHE:
        return False
    cached_at, _ = _CACHE[key]
    if (time.time() - cached_at) >= _CACHE_TTL_SECONDS:
        del _CACHE[key]
        return False
    _CACHE.move_to_end(key)
    return True


def _cache_put(key: str, value: list[PaperMetadata]) -> None:
    _CACHE[key] = (time.time(), value)
    _CACHE.move_to_end(key)
    while len(_CACHE) > _CACHE_MAX_SIZE:
        _CACHE.popitem(last=False)


async def _openalex_search(query: str, max_results: int = 5) -> list[PaperMetadata]:
    params = {
        "search": query,
        "per_page": max_results,
        "sort": "cited_by_count:desc",
        "mailto": os.environ.get("OPENALEX_MAILTO", "vibedeploy@example.com"),
    }

    last_exc: Exception | None = None
    for attempt in range(_OPENALEX_MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
                resp = await client.get(_OPENALEX_WORKS_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError) as exc:
            last_exc = exc
            if attempt < _OPENALEX_MAX_RETRIES:
                wait = (2**attempt) + random.uniform(0, 1)
                logger.warning("[PaperSearch] OpenAlex retry %d in %.1fs: %s", attempt + 1, wait, str(exc)[:200])
                await asyncio.sleep(wait)
            continue
        else:
            last_exc = None
            break

    if last_exc is not None:
        raise last_exc

    results: list[PaperMetadata] = []
    for work in data.get("results", []):
        title = work.get("title", "")
        if not title:
            continue

        abstract_inv = work.get("abstract_inverted_index") or {}
        abstract = _reconstruct_abstract(abstract_inv) if abstract_inv else ""

        authorships = work.get("authorships", []) or []
        authors = [
            a.get("author", {}).get("display_name", "")
            for a in authorships[:5]
            if a.get("author", {}).get("display_name")
        ]

        year = work.get("publication_year", 0) or 0
        citations = work.get("cited_by_count", 0) or 0
        doi = work.get("doi", "") or ""
        url = doi if doi else (work.get("id", "") or "")

        results.append(
            PaperMetadata(
                title=title,
                abstract=abstract[:1000],
                citations=citations,
                year=year,
                url=url,
                source="openalex",
                authors=authors,
                doi=doi.replace("https://doi.org/", "") if doi else "",
            )
        )

    return results


def _reconstruct_abstract(inverted_index: dict) -> str:
    if not inverted_index:
        return ""
    word_positions: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in word_positions)


async def _arxiv_search(query: str, max_results: int = 5) -> list[PaperMetadata]:
    global _ARXIV_LAST_REQUEST

    async with _ARXIV_LOCK:
        now = time.time()
        wait_time = _ARXIV_THROTTLE_SECONDS - (now - _ARXIV_LAST_REQUEST)
        if wait_time > 0:
            await asyncio.sleep(wait_time)

        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        last_exc: Exception | None = None
        for attempt in range(_ARXIV_MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
                    resp = await client.get(_ARXIV_API_URL, params=params)
                    resp.raise_for_status()
                    _ARXIV_LAST_REQUEST = time.time()
                    xml_text = resp.text
            except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError) as exc:
                last_exc = exc
                if attempt < _ARXIV_MAX_RETRIES:
                    wait = (2**attempt) + random.uniform(0, 1)
                    logger.warning("[PaperSearch] arXiv retry %d in %.1fs: %s", attempt + 1, wait, str(exc)[:200])
                    await asyncio.sleep(wait)
                continue
            else:
                last_exc = None
                break

        if last_exc is not None:
            raise last_exc

    return _parse_arxiv_xml(xml_text)


def _parse_arxiv_xml(xml_text: str) -> list[PaperMetadata]:
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    results: list[PaperMetadata] = []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        logger.warning("[PaperSearch] Failed to parse arXiv XML response")
        return []

    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        title = (title_el.text or "").strip().replace("\n", " ") if title_el is not None else ""
        if not title:
            continue

        summary_el = entry.find("atom:summary", ns)
        abstract = (summary_el.text or "").strip().replace("\n", " ") if summary_el is not None else ""

        authors = []
        for author_el in entry.findall("atom:author", ns):
            name_el = author_el.find("atom:name", ns)
            if name_el is not None and name_el.text:
                authors.append(name_el.text.strip())

        published_el = entry.find("atom:published", ns)
        year = 0
        if published_el is not None and published_el.text:
            try:
                year = int(published_el.text[:4])
            except (ValueError, IndexError):
                pass

        link_el = entry.find("atom:id", ns)
        url = (link_el.text or "").strip() if link_el is not None else ""

        results.append(
            PaperMetadata(
                title=title,
                abstract=abstract[:1000],
                citations=0,
                year=year,
                url=url,
                source="arxiv",
                authors=authors[:5],
            )
        )

    return results


async def search_papers(query: str, *, max_results: int = 5) -> list[PaperMetadata]:
    cache_k = _cache_key(query, max_results)
    if _is_cache_valid(cache_k):
        return _CACHE[cache_k][1]

    all_papers: list[PaperMetadata] = []

    openalex_ok = True
    try:
        openalex_results = await _openalex_search(query, max_results=max_results)
        all_papers.extend(openalex_results)
    except Exception:
        logger.exception("[PaperSearch] OpenAlex search failed, falling back to arXiv-only")
        openalex_ok = False

    try:
        arxiv_results = await _arxiv_search(query, max_results=max_results)
        all_papers.extend(arxiv_results)
    except Exception:
        logger.exception("[PaperSearch] arXiv search also failed")

    seen_titles: set[str] = set()
    unique: list[PaperMetadata] = []
    for paper in all_papers:
        normalized = paper.title.strip().lower()
        if normalized not in seen_titles:
            seen_titles.add(normalized)
            unique.append(paper)

    unique.sort(key=lambda p: p.citations, reverse=True)
    result = unique[:max_results]

    if not openalex_ok:
        logger.info("[PaperSearch] Degraded mode: arXiv-only, returned %d papers", len(result))

    _cache_put(cache_k, result)
    return result
