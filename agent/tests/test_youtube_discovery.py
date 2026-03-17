import pytest

from agent.zero_prompt.discovery import (
    YouTubeDiscovery,
    _apply_filters,
    _compute_engagement_rate,
    _deduplicate,
    _parse_video_item,
)
from agent.zero_prompt.events import (
    ZP_SEARCH_COMPLETE,
    ZP_SEARCH_ERROR,
    ZP_SEARCH_START,
    search_complete_event,
    search_error_event,
    search_start_event,
)
from agent.zero_prompt.schemas import VideoCandidate


def _make_candidate(**overrides) -> VideoCandidate:
    defaults = {
        "video_id": "abc123",
        "title": "Test Video",
        "channel_title": "Test Channel",
        "published_at": "2025-01-01T00:00:00Z",
        "view_count": 50000,
        "like_count": 1000,
        "comment_count": 200,
        "engagement_rate": 0.024,
        "category": "science_tech",
    }
    defaults.update(overrides)
    return VideoCandidate(**defaults)


def test_compute_engagement_rate():
    assert _compute_engagement_rate(100000, 2000, 500) == 0.025
    assert _compute_engagement_rate(0, 10, 5) == 0.0


def test_deduplicate_removes_duplicates():
    candidates = [
        _make_candidate(video_id="a"),
        _make_candidate(video_id="b"),
        _make_candidate(video_id="a"),
        _make_candidate(video_id="c"),
    ]
    result = _deduplicate(candidates)
    assert len(result) == 3
    assert [c.video_id for c in result] == ["a", "b", "c"]


def test_apply_filters_by_views():
    candidates = [
        _make_candidate(video_id="low", view_count=5000, like_count=500, engagement_rate=0.1),
        _make_candidate(video_id="high", view_count=50000, like_count=1000, engagement_rate=0.02),
    ]
    result = _apply_filters(candidates, min_views=10000, min_likes=200, min_engagement_rate=0.02)
    assert len(result) == 1
    assert result[0].video_id == "high"


def test_apply_filters_by_engagement_rate():
    candidates = [
        _make_candidate(
            video_id="low_eng", view_count=100000, like_count=100, comment_count=50, engagement_rate=0.0015
        ),
        _make_candidate(
            video_id="high_eng", view_count=100000, like_count=3000, comment_count=500, engagement_rate=0.035
        ),
    ]
    result = _apply_filters(candidates, min_views=1000, min_likes=50, min_engagement_rate=0.02)
    assert len(result) == 1
    assert result[0].video_id == "high_eng"


def test_parse_video_item_extracts_fields():
    item = {
        "id": "vid1",
        "snippet": {
            "title": "Cool Video",
            "channelTitle": "Cool Channel",
            "publishedAt": "2025-06-01T10:00:00Z",
            "description": "A cool video about coding",
            "thumbnails": {"high": {"url": "https://img.youtube.com/vi/vid1/hqdefault.jpg"}},
            "categoryId": "28",
        },
        "statistics": {
            "viewCount": "120000",
            "likeCount": "3000",
            "commentCount": "400",
        },
        "contentDetails": {
            "duration": "PT15M30S",
            "caption": "true",
        },
    }
    result = _parse_video_item(item, "science_tech")
    assert result is not None
    assert result.video_id == "vid1"
    assert result.title == "Cool Video"
    assert result.view_count == 120000
    assert result.like_count == 3000
    assert result.engagement_rate == pytest.approx(0.02833, abs=0.001)
    assert result.has_captions is True
    assert result.category == "science_tech"


@pytest.mark.asyncio
async def test_missing_api_key_raises_value_error():
    discovery = YouTubeDiscovery(api_key="")
    with pytest.raises(ValueError, match="YOUTUBE_DATA_API_KEY"):
        await discovery.fetch_candidate_pool()


def test_search_start_event_structure():
    event = search_start_event("test query", "science_tech")
    assert event["type"] == ZP_SEARCH_START
    assert event["query"] == "test query"
    assert event["category"] == "science_tech"


def test_search_complete_event_structure():
    event = search_complete_event(total=200, filtered=50)
    assert event["type"] == ZP_SEARCH_COMPLETE
    assert event["total_fetched"] == 200
    assert event["after_filter"] == 50


def test_search_error_event_structure():
    event = search_error_event("API quota exceeded")
    assert event["type"] == ZP_SEARCH_ERROR
    assert event["error"] == "API quota exceeded"


def test_video_candidate_model():
    candidate = VideoCandidate(
        video_id="test",
        title="Test",
        channel_title="Channel",
        published_at="2025-01-01",
    )
    assert candidate.view_count == 0
    assert candidate.engagement_rate == 0.0
    assert candidate.has_captions is False


@pytest.mark.asyncio
async def test_fetch_candidate_pool_uses_cache(monkeypatch):
    from agent.zero_prompt import discovery as disc_module

    call_count = 0

    async def fake_search(api_key, query_params, max_results=50):
        nonlocal call_count
        call_count += 1
        return ["vid1", "vid2"]

    async def fake_details(api_key, video_ids):
        return [
            {
                "id": vid,
                "snippet": {
                    "title": f"Video {vid}",
                    "channelTitle": "Ch",
                    "publishedAt": "2025-01-01",
                    "description": "",
                    "thumbnails": {},
                    "categoryId": "28",
                },
                "statistics": {"viewCount": "50000", "likeCount": "1000", "commentCount": "200"},
                "contentDetails": {"duration": "PT10M", "caption": "false"},
            }
            for vid in video_ids
        ]

    monkeypatch.setattr(disc_module, "_search_videos", fake_search)
    monkeypatch.setattr(disc_module, "_get_video_details", fake_details)
    disc_module._CACHE.clear()

    discovery = YouTubeDiscovery(api_key="fake-key")
    result1 = await discovery.fetch_candidate_pool(categories=["science_tech"])
    result2 = await discovery.fetch_candidate_pool(categories=["science_tech"])

    assert len(result1) == len(result2)
    assert call_count == 1
