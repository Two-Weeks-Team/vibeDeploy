import logging
import os
import time

import httpx

from .schemas import VideoCandidate

logger = logging.getLogger(__name__)

_YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
_YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

_CATEGORY_QUERIES = {
    "science_tech": {"q": "app development tutorial", "videoCategoryId": "28"},
    "education": {"q": "coding project ideas", "videoCategoryId": "27"},
    "howto": {"q": "build web app step by step", "videoCategoryId": "26"},
    "korean_market": {"q": "앱 개발 사이드 프로젝트", "relevanceLanguage": "ko"},
}

_CACHE: dict[str, tuple[float, list[VideoCandidate]]] = {}
_CACHE_TTL_SECONDS = 900

_REQUEST_TIMEOUT_SECONDS = 20
_MAX_RETRIES = 2


def _get_api_key() -> str:
    key = os.getenv("YOUTUBE_DATA_API_KEY", "").strip()
    if not key:
        key = os.getenv("YOUTUBE_API_KEY", "").strip()
    return key


def _cache_key(
    categories: tuple[str, ...], min_views: int, min_likes: int, min_engagement_rate: float, max_results: int
) -> str:
    return f"{','.join(sorted(categories))}|{min_views}|{min_likes}|{min_engagement_rate}|{max_results}"


def _is_cache_valid(key: str) -> bool:
    if key not in _CACHE:
        return False
    cached_at, _ = _CACHE[key]
    return (time.time() - cached_at) < _CACHE_TTL_SECONDS


def _compute_engagement_rate(views: int, likes: int, comments: int) -> float:
    if views <= 0:
        return 0.0
    return (likes + comments) / views


async def _http_get(url: str, params: dict) -> dict:
    last_exc: Exception | None = None
    async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
            except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError) as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES:
                    logger.warning(
                        "[YouTubeDiscovery] Retry %d/%d for %s: %s",
                        attempt + 1,
                        _MAX_RETRIES,
                        url,
                        str(exc)[:200],
                    )
    raise last_exc  # type: ignore[misc]


async def _search_videos(api_key: str, query_params: dict, max_results: int = 50) -> list[str]:
    params = {
        "part": "id",
        "type": "video",
        "order": "viewCount",
        "maxResults": min(max_results, 50),
        "key": api_key,
        **query_params,
    }
    data = await _http_get(_YOUTUBE_SEARCH_URL, params)
    items = data.get("items", [])
    return [item["id"]["videoId"] for item in items if item.get("id", {}).get("videoId")]


async def _get_video_details(api_key: str, video_ids: list[str]) -> list[dict]:
    if not video_ids:
        return []

    results: list[dict] = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        params = {
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(batch),
            "key": api_key,
        }
        data = await _http_get(_YOUTUBE_VIDEOS_URL, params)
        results.extend(data.get("items", []))
    return results


def _parse_video_item(item: dict, category_label: str) -> VideoCandidate | None:
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    content = item.get("contentDetails", {})

    view_count = int(stats.get("viewCount", 0))
    like_count = int(stats.get("likeCount", 0))
    comment_count = int(stats.get("commentCount", 0))

    thumbnails = snippet.get("thumbnails", {})
    thumb = thumbnails.get("high", thumbnails.get("medium", thumbnails.get("default", {})))

    return VideoCandidate(
        video_id=item.get("id", ""),
        title=snippet.get("title", ""),
        channel_title=snippet.get("channelTitle", ""),
        published_at=snippet.get("publishedAt", ""),
        view_count=view_count,
        like_count=like_count,
        comment_count=comment_count,
        engagement_rate=_compute_engagement_rate(view_count, like_count, comment_count),
        category=category_label,
        description=snippet.get("description", "")[:500],
        thumbnail_url=thumb.get("url", ""),
        duration=content.get("duration", ""),
        has_captions=content.get("caption", "false") == "true",
    )


def _apply_filters(
    candidates: list[VideoCandidate],
    *,
    min_views: int,
    min_likes: int,
    min_engagement_rate: float,
) -> list[VideoCandidate]:
    return [
        c
        for c in candidates
        if c.view_count >= min_views and c.like_count >= min_likes and c.engagement_rate >= min_engagement_rate
    ]


def _deduplicate(candidates: list[VideoCandidate]) -> list[VideoCandidate]:
    seen: set[str] = set()
    unique: list[VideoCandidate] = []
    for c in candidates:
        if c.video_id not in seen:
            seen.add(c.video_id)
            unique.append(c)
    return unique


class YouTubeDiscovery:
    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or _get_api_key()

    async def fetch_candidate_pool(
        self,
        categories: list[str] | None = None,
        *,
        min_views: int = 10_000,
        min_likes: int = 200,
        min_engagement_rate: float = 0.02,
        max_results: int = 60,
    ) -> list[VideoCandidate]:
        if not self._api_key:
            raise ValueError("YOUTUBE_DATA_API_KEY is not configured")

        if categories is None:
            categories = list(_CATEGORY_QUERIES.keys())

        cache_k = _cache_key(tuple(categories), min_views, min_likes, min_engagement_rate, max_results)
        if _is_cache_valid(cache_k):
            return _CACHE[cache_k][1]

        all_video_ids: list[str] = []
        for cat in categories:
            query_params = _CATEGORY_QUERIES.get(cat, {"q": cat})
            try:
                ids = await _search_videos(self._api_key, query_params, max_results=max_results)
                all_video_ids.extend(ids)
            except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError):
                logger.exception("[YouTubeDiscovery] Search failed for category=%s", cat)

        all_video_ids = list(dict.fromkeys(all_video_ids))

        raw_items = await _get_video_details(self._api_key, all_video_ids)
        total_fetched = len(raw_items)

        candidates: list[VideoCandidate] = []
        for item in raw_items:
            cat_label = ""
            for cat in categories:
                cat_params = _CATEGORY_QUERIES.get(cat, {})
                if cat_params.get("videoCategoryId") == item.get("snippet", {}).get("categoryId"):
                    cat_label = cat
                    break
            if not cat_label and categories:
                cat_label = categories[0]

            parsed = _parse_video_item(item, cat_label)
            if parsed:
                candidates.append(parsed)

        candidates = _deduplicate(candidates)
        filtered = _apply_filters(
            candidates,
            min_views=min_views,
            min_likes=min_likes,
            min_engagement_rate=min_engagement_rate,
        )

        logger.info(
            "[YouTubeDiscovery] Fetched %d videos, %d after filtering",
            total_fetched,
            len(filtered),
        )

        _CACHE[cache_k] = (time.time(), filtered)
        return filtered
