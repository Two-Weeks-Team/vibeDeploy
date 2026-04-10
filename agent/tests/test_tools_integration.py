"""Integration-style unit tests for tools/ and utils/ modules.

All external I/O is mocked — no real API calls are made.
Targets:
  utils/json_utils.py        22% → 70%+
  tools/youtube.py           17% → 70%+
  tools/function_tools.py     0% → 70%+
  tools/github.py             9% → 70%+
  tools/web_search.py        20% → 70%+
  tools/digitalocean.py      28% → 70%+
  tools/image_gen.py         33% → 70%+
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

# ─── utils/json_utils.py ─────────────────────────────────────────────────────


class TestParseJsonResponse:
    def test_valid_json(self):
        from agent.utils.json_utils import parse_json_response

        result = parse_json_response('{"key": "value"}', {})
        assert result == {"key": "value"}

    def test_markdown_wrapped_json(self):
        from agent.utils.json_utils import parse_json_response

        text = '```json\n{"foo": 42}\n```'
        result = parse_json_response(text, {})
        assert result == {"foo": 42}

    def test_markdown_no_lang_tag(self):
        from agent.utils.json_utils import parse_json_response

        text = '```\n{"bar": true}\n```'
        result = parse_json_response(text, {})
        assert result == {"bar": True}

    def test_json_embedded_in_text(self):
        from agent.utils.json_utils import parse_json_response

        text = 'Here is the result: {"key": "val"} extra text'
        result = parse_json_response(text, {})
        assert result == {"key": "val"}

    def test_broken_json_returns_default_with_raw(self):
        from agent.utils.json_utils import parse_json_response

        default = {"default_key": "default_val"}
        result = parse_json_response("not json", default)
        assert result["default_key"] == "default_val"
        assert "raw_response" in result
        assert result["raw_response"] == "not json"

    def test_empty_string_returns_default(self):
        from agent.utils.json_utils import parse_json_response

        result = parse_json_response("", {"fallback": 1})
        assert result["fallback"] == 1

    def test_nested_json(self):
        from agent.utils.json_utils import parse_json_response

        result = parse_json_response('{"a": {"b": [1, 2, 3]}}', {})
        assert result["a"]["b"] == [1, 2, 3]

    def test_long_broken_content_truncated_at_500(self):
        from agent.utils.json_utils import parse_json_response

        long_text = "x" * 1000
        result = parse_json_response(long_text, {})
        assert len(result["raw_response"]) <= 500


class TestSlugify:
    def test_simple_ascii(self):
        from agent.utils.json_utils import slugify

        assert slugify("Hello World") == "hello-world"

    def test_korean_chars_stripped_returns_fallback(self):
        from agent.utils.json_utils import slugify

        # Korean chars stripped → only spaces remain → empty → fallback
        assert slugify("앱 테스트") == "vibedeploy-app"

    def test_spaces_become_hyphens(self):
        from agent.utils.json_utils import slugify

        assert slugify("my app name") == "my-app-name"

    def test_special_chars_stripped(self):
        from agent.utils.json_utils import slugify

        assert slugify("hello@world!") == "helloworld"

    def test_consecutive_hyphens_collapsed(self):
        from agent.utils.json_utils import slugify

        assert slugify("foo   bar") == "foo-bar"

    def test_max_length_truncation(self):
        from agent.utils.json_utils import slugify

        result = slugify("hello world app", max_length=7)
        assert len(result) <= 7
        assert not result.endswith("-")

    def test_empty_string_returns_fallback(self):
        from agent.utils.json_utils import slugify

        assert slugify("") == "vibedeploy-app"

    def test_none_returns_fallback(self):
        from agent.utils.json_utils import slugify

        assert slugify(None) == "vibedeploy-app"

    def test_underscore_stripped(self):
        from agent.utils.json_utils import slugify

        assert slugify("foo_bar") == "foobar"

    def test_custom_fallback(self):
        from agent.utils.json_utils import slugify

        assert slugify("", fallback="my-fallback") == "my-fallback"

    def test_mixed_ascii_and_numbers(self):
        from agent.utils.json_utils import slugify

        assert slugify("App v2 Release") == "app-v2-release"

    def test_leading_trailing_spaces(self):
        from agent.utils.json_utils import slugify

        assert slugify("  hello  ") == "hello"


class TestIsSafeFilePath:
    def test_safe_regular_path(self):
        from agent.utils.json_utils import is_safe_file_path

        assert is_safe_file_path("src/main.py") is True

    def test_safe_readme(self):
        from agent.utils.json_utils import is_safe_file_path

        assert is_safe_file_path("README.md") is True

    def test_blocked_env_file(self):
        from agent.utils.json_utils import is_safe_file_path

        assert is_safe_file_path(".env") is False

    def test_blocked_env_production(self):
        from agent.utils.json_utils import is_safe_file_path

        assert is_safe_file_path(".env.production") is False

    def test_blocked_github_dir(self):
        from agent.utils.json_utils import is_safe_file_path

        assert is_safe_file_path(".github/workflows/ci.yml") is False

    def test_blocked_git_dir(self):
        from agent.utils.json_utils import is_safe_file_path

        assert is_safe_file_path(".git/config") is False

    def test_blocked_gradient_dir(self):
        from agent.utils.json_utils import is_safe_file_path

        assert is_safe_file_path(".gradient/agent.yml") is False

    def test_blocked_dockerfile(self):
        from agent.utils.json_utils import is_safe_file_path

        assert is_safe_file_path("Dockerfile") is False

    def test_blocked_gitignore(self):
        from agent.utils.json_utils import is_safe_file_path

        assert is_safe_file_path(".gitignore") is False

    def test_leading_slash_env_still_blocked(self):
        from agent.utils.json_utils import is_safe_file_path

        assert is_safe_file_path("/.env") is False

    def test_safe_nested_path(self):
        from agent.utils.json_utils import is_safe_file_path

        assert is_safe_file_path("backend/api/routes.py") is True

    def test_safe_frontend_path(self):
        from agent.utils.json_utils import is_safe_file_path

        assert is_safe_file_path("web/src/components/App.tsx") is True


# ─── tools/youtube.py ────────────────────────────────────────────────────────


class TestIsYoutubeUrl:
    def test_watch_url(self):
        from agent.tools.youtube import is_youtube_url

        assert is_youtube_url("https://www.youtube.com/watch?v=abc123") is True

    def test_youtu_be_url(self):
        from agent.tools.youtube import is_youtube_url

        assert is_youtube_url("https://youtu.be/abc123") is True

    def test_embed_url(self):
        from agent.tools.youtube import is_youtube_url

        assert is_youtube_url("https://www.youtube.com/embed/abc123") is True

    def test_shorts_url(self):
        from agent.tools.youtube import is_youtube_url

        assert is_youtube_url("https://www.youtube.com/shorts/abc123") is True

    def test_non_youtube_url(self):
        from agent.tools.youtube import is_youtube_url

        assert is_youtube_url("https://example.com/video") is False

    def test_empty_string(self):
        from agent.tools.youtube import is_youtube_url

        assert is_youtube_url("") is False

    def test_url_without_https_prefix(self):
        from agent.tools.youtube import is_youtube_url

        assert is_youtube_url("youtube.com/watch?v=xyz") is True


class TestExtractFirstYoutubeUrl:
    def test_finds_watch_url(self):
        from agent.tools.youtube import extract_first_youtube_url

        text = "Check out https://www.youtube.com/watch?v=abc123 for more info"
        result = extract_first_youtube_url(text)
        assert result is not None
        assert "abc123" in result

    def test_finds_youtu_be_url(self):
        from agent.tools.youtube import extract_first_youtube_url

        text = "See https://youtu.be/xyz456 now"
        result = extract_first_youtube_url(text)
        assert result is not None
        assert "xyz456" in result

    def test_returns_none_if_no_url(self):
        from agent.tools.youtube import extract_first_youtube_url

        assert extract_first_youtube_url("no youtube here") is None

    def test_finds_embed_url(self):
        from agent.tools.youtube import extract_first_youtube_url

        text = "Watch https://youtube.com/embed/vid789 today!"
        result = extract_first_youtube_url(text)
        assert result is not None
        assert "vid789" in result

    def test_finds_shorts_url(self):
        from agent.tools.youtube import extract_first_youtube_url

        text = "Here https://www.youtube.com/shorts/s123 is a short"
        result = extract_first_youtube_url(text)
        assert result is not None


class TestExtractVideoId:
    def test_watch_url(self):
        from agent.tools.youtube import extract_video_id

        assert extract_video_id("https://www.youtube.com/watch?v=abc123") == "abc123"

    def test_youtu_be_url(self):
        from agent.tools.youtube import extract_video_id

        assert extract_video_id("https://youtu.be/xyz456") == "xyz456"

    def test_embed_url(self):
        from agent.tools.youtube import extract_video_id

        assert extract_video_id("https://www.youtube.com/embed/vid789") == "vid789"

    def test_shorts_url(self):
        from agent.tools.youtube import extract_video_id

        assert extract_video_id("https://www.youtube.com/shorts/short123") == "short123"

    def test_no_match_returns_none(self):
        from agent.tools.youtube import extract_video_id

        assert extract_video_id("https://example.com/video") is None

    def test_plain_string_no_match(self):
        from agent.tools.youtube import extract_video_id

        assert extract_video_id("randomstring") is None


class TestParseJson3:
    def test_normal_segments(self):
        from agent.tools.youtube import _parse_json3

        data = {
            "events": [
                {"segs": [{"utf8": "Hello"}, {"utf8": " world"}]},
                {"segs": [{"utf8": "foo"}]},
            ]
        }
        result = _parse_json3(data)
        assert "Hello" in result
        assert "world" in result
        assert "foo" in result

    def test_newline_only_segments_skipped(self):
        from agent.tools.youtube import _parse_json3

        data = {
            "events": [
                {"segs": [{"utf8": "\n"}, {"utf8": "valid text"}]},
            ]
        }
        result = _parse_json3(data)
        assert "valid text" in result
        assert "\n" not in result

    def test_empty_events(self):
        from agent.tools.youtube import _parse_json3

        assert _parse_json3({"events": []}) == ""

    def test_missing_events_key(self):
        from agent.tools.youtube import _parse_json3

        assert _parse_json3({}) == ""


class TestParseVttOrPlain:
    def test_vtt_content_stripped(self):
        from agent.tools.youtube import _parse_vtt_or_plain

        content = (
            "WEBVTT\n\n1\n00:00:01.000 --> 00:00:02.000\nHello world\n\n2\n00:00:03.000 --> 00:00:04.000\nFoo bar\n"
        )
        result = _parse_vtt_or_plain(content)
        assert "Hello world" in result
        assert "Foo bar" in result

    def test_html_tags_removed(self):
        from agent.tools.youtube import _parse_vtt_or_plain

        content = "WEBVTT\n\n<c>Hello</c> <b>world</b>\n"
        result = _parse_vtt_or_plain(content)
        assert "<" not in result
        assert "Hello" in result

    def test_timestamp_lines_excluded(self):
        from agent.tools.youtube import _parse_vtt_or_plain

        content = "00:00:01.000 --> 00:00:02.000\nActual text\n"
        result = _parse_vtt_or_plain(content)
        assert "Actual text" in result
        assert "-->" not in result

    def test_empty_content(self):
        from agent.tools.youtube import _parse_vtt_or_plain

        assert _parse_vtt_or_plain("") == ""


class TestBuildMetadataContext:
    def test_full_info(self):
        from agent.tools.youtube import _build_metadata_context

        info = {
            "title": "My Video",
            "channel": "My Channel",
            "categories": ["Tech"],
            "tags": ["python", "AI"],
            "duration": 125,
            "description": "A great video",
        }
        result = _build_metadata_context(info)
        assert "My Video" in result
        assert "My Channel" in result
        assert "Tech" in result
        assert "2m 5s" in result

    def test_empty_info(self):
        from agent.tools.youtube import _build_metadata_context

        result = _build_metadata_context({})
        assert result == "[Error: No metadata available]"

    def test_uses_uploader_if_no_channel(self):
        from agent.tools.youtube import _build_metadata_context

        info = {"title": "Test", "uploader": "SomeUploader"}
        result = _build_metadata_context(info)
        assert "SomeUploader" in result

    def test_description_included(self):
        from agent.tools.youtube import _build_metadata_context

        info = {"title": "Video", "description": "Detailed description here"}
        result = _build_metadata_context(info)
        assert "Detailed description here" in result

    def test_tags_truncated_to_15(self):
        from agent.tools.youtube import _build_metadata_context

        info = {"title": "Video", "tags": [f"tag{i}" for i in range(20)]}
        result = _build_metadata_context(info)
        assert "tag14" in result
        assert "tag15" not in result


class TestFetchSubtitleText:
    def test_json3_success(self):
        from agent.tools.youtube import _fetch_subtitle_text

        json3_data = {"events": [{"segs": [{"utf8": "Hello world"}]}]}
        mock_resp = MagicMock()
        mock_resp.json.return_value = json3_data
        mock_resp.raise_for_status = MagicMock()

        subtitle_list = [{"ext": "json3", "url": "https://example.com/sub.json3"}]

        with patch("agent.tools.youtube.requests.get", return_value=mock_resp):
            result = _fetch_subtitle_text(subtitle_list)

        assert result is not None
        assert "Hello world" in result

    def test_vtt_success(self):
        from agent.tools.youtube import _fetch_subtitle_text

        mock_resp = MagicMock()
        mock_resp.text = "WEBVTT\n\nHello world\n"
        mock_resp.raise_for_status = MagicMock()

        subtitle_list = [{"ext": "vtt", "url": "https://example.com/sub.vtt"}]

        with patch("agent.tools.youtube.requests.get", return_value=mock_resp):
            result = _fetch_subtitle_text(subtitle_list)

        assert result is not None

    def test_fallback_subtitle_ext(self):
        from agent.tools.youtube import _fetch_subtitle_text

        mock_resp = MagicMock()
        mock_resp.text = "plain subtitle text"
        mock_resp.raise_for_status = MagicMock()

        subtitle_list = [{"ext": "srv3", "url": "https://example.com/sub.srv3"}]

        with patch("agent.tools.youtube.requests.get", return_value=mock_resp):
            result = _fetch_subtitle_text(subtitle_list)

        assert result is not None

    def test_no_url_returns_none(self):
        from agent.tools.youtube import _fetch_subtitle_text

        # No 'url' key in the entry
        result = _fetch_subtitle_text([{"ext": "json3"}])
        assert result is None

    def test_request_exception_continues_to_next(self):
        import requests as req_lib

        from agent.tools.youtube import _fetch_subtitle_text

        subtitle_list = [{"ext": "json3", "url": "https://example.com/sub.json3"}]

        with patch("agent.tools.youtube.requests.get", side_effect=req_lib.RequestException("timeout")):
            result = _fetch_subtitle_text(subtitle_list)

        assert result is None

    def test_empty_list(self):
        from agent.tools.youtube import _fetch_subtitle_text

        assert _fetch_subtitle_text([]) is None


async def test_extract_youtube_transcript_success():
    from agent.tools.youtube import extract_youtube_transcript

    json3_data = {"events": [{"segs": [{"utf8": "Great video content"}]}]}
    mock_resp = MagicMock()
    mock_resp.json.return_value = json3_data
    mock_resp.raise_for_status = MagicMock()

    mock_info = {
        "subtitles": {"en": [{"ext": "json3", "url": "https://example.com/sub.json3"}]},
        "automatic_captions": {},
    }

    mock_ydl = MagicMock()
    mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl.__exit__ = MagicMock(return_value=False)
    mock_ydl.extract_info.return_value = mock_info

    with (
        patch("yt_dlp.YoutubeDL", return_value=mock_ydl),
        patch("agent.tools.youtube.requests.get", return_value=mock_resp),
    ):
        result = await extract_youtube_transcript("https://www.youtube.com/watch?v=abc123")

    assert "Great video content" in result


async def test_extract_youtube_transcript_auto_captions():
    from agent.tools.youtube import extract_youtube_transcript

    json3_data = {"events": [{"segs": [{"utf8": "Auto caption text"}]}]}
    mock_resp = MagicMock()
    mock_resp.json.return_value = json3_data
    mock_resp.raise_for_status = MagicMock()

    mock_info = {
        "subtitles": {},
        "automatic_captions": {"en": [{"ext": "json3", "url": "https://example.com/auto.json3"}]},
    }

    mock_ydl = MagicMock()
    mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl.__exit__ = MagicMock(return_value=False)
    mock_ydl.extract_info.return_value = mock_info

    with (
        patch("yt_dlp.YoutubeDL", return_value=mock_ydl),
        patch("agent.tools.youtube.requests.get", return_value=mock_resp),
    ):
        result = await extract_youtube_transcript("https://www.youtube.com/watch?v=abc123")

    assert "Auto caption text" in result


async def test_extract_youtube_transcript_fallback_to_metadata():
    from agent.tools.youtube import extract_youtube_transcript

    mock_info = {
        "subtitles": {},
        "automatic_captions": {},
        "title": "Test Video Title",
        "channel": "Test Channel",
        "description": "Great description",
        "tags": [],
        "categories": [],
        "duration": 120,
    }

    mock_ydl = MagicMock()
    mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl.__exit__ = MagicMock(return_value=False)
    mock_ydl.extract_info.return_value = mock_info

    with patch("yt_dlp.YoutubeDL", return_value=mock_ydl):
        result = await extract_youtube_transcript("https://www.youtube.com/watch?v=abc123")

    assert "Test Video Title" in result


async def test_extract_youtube_transcript_ydlp_exception():
    from agent.tools.youtube import extract_youtube_transcript

    mock_ydl = MagicMock()
    mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl.__exit__ = MagicMock(return_value=False)
    mock_ydl.extract_info.side_effect = Exception("Network error")

    with patch("yt_dlp.YoutubeDL", return_value=mock_ydl):
        result = await extract_youtube_transcript("https://www.youtube.com/watch?v=abc123")

    assert result.startswith("[Error:")


async def test_extract_youtube_transcript_invalid_url():
    from agent.tools.youtube import extract_youtube_transcript

    # URL that doesn't contain youtube/youtu.be and can't yield a video_id
    result = await extract_youtube_transcript("not-a-url-at-all")
    assert "Error" in result


async def test_detect_visual_segments_with_keywords():
    from agent.tools.youtube import detect_visual_segments

    transcript = "Look at this demo. Here is another sentence. Watch this screen carefully."
    result = await detect_visual_segments(transcript)
    assert isinstance(result, list)
    assert len(result) > 0
    for seg in result:
        assert "text" in seg
        assert "keywords_found" in seg
        assert "index" in seg


async def test_detect_visual_segments_no_keywords():
    from agent.tools.youtube import detect_visual_segments

    transcript = "The cat sat on the mat. It rained today."
    result = await detect_visual_segments(transcript)
    assert result == []


async def test_detect_visual_segments_empty():
    from agent.tools.youtube import detect_visual_segments

    result = await detect_visual_segments("")
    assert result == []


async def test_extract_video_frames_valid():
    from agent.tools.youtube import extract_video_frames

    result = await extract_video_frames("https://www.youtube.com/watch?v=abc123", [10.0, 20.0, 30.0])
    assert len(result) == 3
    for frame in result:
        assert frame["video_id"] == "abc123"
        assert "thumbnail_url" in frame
        assert "timestamp" in frame


async def test_extract_video_frames_invalid_url():
    from agent.tools.youtube import extract_video_frames

    result = await extract_video_frames("https://example.com/video", [10.0])
    assert result == []


async def test_extract_video_frames_empty_timestamps():
    from agent.tools.youtube import extract_video_frames

    result = await extract_video_frames("https://www.youtube.com/watch?v=abc123", [])
    assert result == []


# ─── tools/function_tools.py ─────────────────────────────────────────────────


class TestFunctionToolsAttributes:
    def test_search_competitors_has_name(self):
        from agent.tools.function_tools import search_competitors

        assert hasattr(search_competitors, "name")
        assert search_competitors.name is not None

    def test_search_competitors_has_description(self):
        from agent.tools.function_tools import search_competitors

        assert hasattr(search_competitors, "description")
        assert len(search_competitors.description) > 10

    def test_search_tech_stack_has_name(self):
        from agent.tools.function_tools import search_tech_stack

        assert hasattr(search_tech_stack, "name")
        assert search_tech_stack.name is not None

    def test_search_tech_stack_has_description(self):
        from agent.tools.function_tools import search_tech_stack

        assert hasattr(search_tech_stack, "description")
        assert len(search_tech_stack.description) > 10

    def test_query_platform_docs_has_name(self):
        from agent.tools.function_tools import query_platform_docs

        assert hasattr(query_platform_docs, "name")

    def test_query_framework_best_practices_has_name(self):
        from agent.tools.function_tools import query_framework_best_practices

        assert hasattr(query_framework_best_practices, "name")

    def test_scout_tools_list(self):
        from agent.tools.function_tools import SCOUT_TOOLS

        assert len(SCOUT_TOOLS) == 2

    def test_architect_tools_list(self):
        from agent.tools.function_tools import ARCHITECT_TOOLS

        assert len(ARCHITECT_TOOLS) == 3


async def test_function_tools_search_competitors_returns_json():
    from agent.tools.function_tools import search_competitors

    mock_result = {"results": [{"name": "Competitor1", "description": "A competitor"}]}

    with patch("agent.tools.web_search.web_search", new_callable=AsyncMock) as mock_ws:
        mock_ws.return_value = mock_result
        result = await search_competitors.ainvoke({"query": "todo app"})

    assert isinstance(result, str)
    data = json.loads(result)
    assert "results" in data


async def test_function_tools_search_tech_stack_returns_json():
    from agent.tools.function_tools import search_tech_stack

    mock_result = {"results": [{"framework": "Next.js"}]}

    with patch("agent.tools.web_search.web_search", new_callable=AsyncMock) as mock_ws:
        mock_ws.return_value = mock_result
        result = await search_tech_stack.ainvoke({"query": "web app"})

    assert isinstance(result, str)
    data = json.loads(result)
    assert "results" in data


async def test_function_tools_query_platform_docs_returns_json():
    from agent.tools.function_tools import query_platform_docs

    # knowledge_base returns error-dict without API key — function still returns JSON
    result = await query_platform_docs.ainvoke({"query": "app platform"})
    assert isinstance(result, str)
    data = json.loads(result)
    assert isinstance(data, dict)


async def test_function_tools_query_framework_best_practices_returns_json():
    from agent.tools.function_tools import query_framework_best_practices

    result = await query_framework_best_practices.ainvoke({"framework": "Next.js", "pattern_type": "auth"})
    assert isinstance(result, str)
    data = json.loads(result)
    assert isinstance(data, dict)


# ─── tools/github.py ─────────────────────────────────────────────────────────


async def test_wait_for_ci_no_token(monkeypatch):
    from agent.tools.github import wait_for_ci

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    result = await wait_for_ci("owner/repo", "abc123")
    assert result["status"] == "skipped"
    assert result["reason"] == "no_token"


async def test_wait_for_ci_passed(monkeypatch):
    from agent.tools.github import wait_for_ci

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")

    check_runs_data = {
        "check_runs": [
            {"status": "completed", "conclusion": "success", "name": "CI", "details_url": "https://gh.com/run/1"}
        ]
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(check_runs_data).encode()
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("agent.tools.github.request.urlopen", return_value=mock_resp):
        result = await wait_for_ci("owner/repo", "abc123", timeout=30)

    assert result["status"] == "passed"
    assert result["total"] == 1


async def test_wait_for_ci_failed(monkeypatch):
    from agent.tools.github import wait_for_ci

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")

    check_runs_data = {
        "check_runs": [
            {"status": "completed", "conclusion": "failure", "name": "lint", "details_url": "https://gh.com/run/2"}
        ]
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(check_runs_data).encode()
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("agent.tools.github.request.urlopen", return_value=mock_resp):
        result = await wait_for_ci("owner/repo", "abc123", timeout=30)

    assert result["status"] == "failed"
    assert "lint" in result["failed_jobs"]


async def test_wait_for_ci_all_skipped(monkeypatch):
    """Check-runs with 'skipped' conclusion should count as passed."""
    from agent.tools.github import wait_for_ci

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")

    check_runs_data = {
        "check_runs": [
            {"status": "completed", "conclusion": "skipped", "name": "optional-job", "details_url": ""},
            {"status": "completed", "conclusion": "neutral", "name": "neutral-job", "details_url": ""},
        ]
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(check_runs_data).encode()
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("agent.tools.github.request.urlopen", return_value=mock_resp):
        result = await wait_for_ci("owner/repo", "abc123", timeout=30)

    assert result["status"] == "passed"


async def test_wait_for_ci_timeout(monkeypatch):
    from agent.tools.github import wait_for_ci

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")

    no_checks_data = {"check_runs": []}
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(no_checks_data).encode()
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with (
        patch("agent.tools.github.request.urlopen", return_value=mock_resp),
        patch("agent.tools.github.asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await wait_for_ci("owner/repo", "abc123", timeout=5)

    assert result["status"] == "timeout"


async def test_wait_for_ci_incomplete_runs_then_complete(monkeypatch):
    """Simulate incomplete runs on first call then complete on second."""
    from agent.tools.github import wait_for_ci

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")

    incomplete = json.dumps(
        {"check_runs": [{"status": "in_progress", "conclusion": None, "name": "CI", "details_url": ""}]}
    ).encode()
    complete = json.dumps(
        {
            "check_runs": [
                {"status": "completed", "conclusion": "success", "name": "CI", "details_url": "https://gh.com"}
            ]
        }
    ).encode()

    mock_resp_1 = MagicMock()
    mock_resp_1.read.return_value = incomplete
    mock_resp_1.__enter__ = MagicMock(return_value=mock_resp_1)
    mock_resp_1.__exit__ = MagicMock(return_value=False)

    mock_resp_2 = MagicMock()
    mock_resp_2.read.return_value = complete
    mock_resp_2.__enter__ = MagicMock(return_value=mock_resp_2)
    mock_resp_2.__exit__ = MagicMock(return_value=False)

    with (
        patch("agent.tools.github.request.urlopen", side_effect=[mock_resp_1, mock_resp_2]),
        patch("agent.tools.github.asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await wait_for_ci("owner/repo", "abc123", timeout=60)

    assert result["status"] == "passed"


async def test_wait_for_ci_http_error(monkeypatch):
    from urllib import error

    from agent.tools.github import wait_for_ci

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")

    with (
        patch(
            "agent.tools.github.request.urlopen",
            side_effect=error.HTTPError(url="https://api.github.com", code=403, msg="Forbidden", hdrs=None, fp=None),
        ),
        patch("agent.tools.github.asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await wait_for_ci("owner/repo", "abc123", timeout=5)

    assert result["status"] == "timeout"


def test_github_api_get_success():
    from agent.tools.github import _github_api_get

    data = {"some": "data", "items": [1, 2, 3]}
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(data).encode()
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("agent.tools.github.request.urlopen", return_value=mock_resp):
        result = _github_api_get("/repos/owner/repo", "fake-token")

    assert result == data


def test_github_api_get_http_error():
    from urllib import error

    from agent.tools.github import _github_api_get

    with patch("agent.tools.github.request.urlopen", side_effect=error.URLError("connection refused")):
        result = _github_api_get("/repos/owner/repo", "fake-token")

    assert result is None


async def test_get_ci_failure_logs_no_token(monkeypatch):
    from agent.tools.github import get_ci_failure_logs

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    result = await get_ci_failure_logs("owner/repo", "abc123")
    assert result == ""


async def test_get_ci_failure_logs_no_workflow_runs(monkeypatch):
    from agent.tools.github import get_ci_failure_logs

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")

    with patch("agent.tools.github._github_api_get", return_value={"workflow_runs": []}):
        result = await get_ci_failure_logs("owner/repo", "abc123")

    assert result == ""


async def test_get_ci_failure_logs_api_returns_none(monkeypatch):
    from agent.tools.github import get_ci_failure_logs

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")

    with patch("agent.tools.github._github_api_get", return_value=None):
        result = await get_ci_failure_logs("owner/repo", "abc123")

    assert result == ""


async def test_get_ci_failure_logs_with_failure(monkeypatch):
    from agent.tools.github import get_ci_failure_logs

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")

    def mock_api_get(path, token):
        if "runs?" in path:
            return {"workflow_runs": [{"id": 123}]}
        elif "runs/123/jobs" in path:
            return {
                "jobs": [
                    {
                        "name": "test-job",
                        "conclusion": "failure",
                        "id": 456,
                        "steps": [{"name": "Run tests", "conclusion": "failure"}],
                    }
                ]
            }
        return None

    with (
        patch("agent.tools.github._github_api_get", side_effect=mock_api_get),
        patch("agent.tools.github._get_job_log", return_value="Error: test failed"),
    ):
        result = await get_ci_failure_logs("owner/repo", "abc123")

    assert "test-job" in result
    assert "FAILED" in result


async def test_get_ci_failure_logs_skips_non_failure_jobs(monkeypatch):
    from agent.tools.github import get_ci_failure_logs

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")

    def mock_api_get(path, token):
        if "runs?" in path:
            return {"workflow_runs": [{"id": 123}]}
        elif "runs/123/jobs" in path:
            return {
                "jobs": [
                    {"name": "passing-job", "conclusion": "success", "id": 789, "steps": []},
                ]
            }
        return None

    with patch("agent.tools.github._github_api_get", side_effect=mock_api_get):
        result = await get_ci_failure_logs("owner/repo", "abc123")

    assert result == ""


async def test_create_github_repo_no_token(monkeypatch):
    from agent.tools.github import create_github_repo

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    result = await create_github_repo("myapp", {})
    assert result["status"] == "error"
    assert "GITHUB_TOKEN" in result["error"]


async def test_create_github_repo_success(monkeypatch):
    from agent.tools.github import create_github_repo

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")

    mock_repo = MagicMock()
    mock_repo.full_name = "testuser/myapp"
    mock_repo.html_url = "https://github.com/testuser/myapp"
    mock_repo.clone_url = "https://github.com/testuser/myapp.git"
    mock_repo.default_branch = "main"

    mock_owner = MagicMock()
    mock_owner.create_repo.return_value = mock_repo

    mock_gh = MagicMock()
    mock_gh.get_user.return_value = mock_owner

    with (
        patch("agent.tools.github._get_client", return_value=mock_gh),
        patch("agent.tools.github.push_files", new_callable=AsyncMock) as mock_push,
    ):
        mock_push.return_value = {"status": "pushed", "commit_sha": "deadbeef"}
        result = await create_github_repo("myapp", {"README.md": "# Test"})

    assert result["status"] == "created"
    assert result["full_name"] == "testuser/myapp"
    assert result["initial_commit_sha"] == "deadbeef"


async def test_create_github_repo_with_org(monkeypatch):
    from agent.tools.github import create_github_repo

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")

    mock_repo = MagicMock()
    mock_repo.full_name = "myorg/orgapp"
    mock_repo.html_url = "https://github.com/myorg/orgapp"
    mock_repo.clone_url = "https://github.com/myorg/orgapp.git"
    mock_repo.default_branch = "main"

    mock_org = MagicMock()
    mock_org.create_repo.return_value = mock_repo

    mock_gh = MagicMock()
    mock_gh.get_organization.return_value = mock_org

    with (
        patch("agent.tools.github._get_client", return_value=mock_gh),
        patch("agent.tools.github.push_files", new_callable=AsyncMock) as mock_push,
    ):
        mock_push.return_value = {"status": "pushed", "commit_sha": "abc"}
        result = await create_github_repo("orgapp", {"main.py": "code"}, org="myorg")

    assert result["status"] == "created"
    mock_gh.get_organization.assert_called_once_with("myorg")


async def test_create_github_repo_no_files(monkeypatch):
    from agent.tools.github import create_github_repo

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")

    mock_repo = MagicMock()
    mock_repo.full_name = "testuser/emptyapp"
    mock_repo.html_url = "https://github.com/testuser/emptyapp"
    mock_repo.clone_url = "https://github.com/testuser/emptyapp.git"
    mock_repo.default_branch = "main"

    mock_owner = MagicMock()
    mock_owner.create_repo.return_value = mock_repo

    mock_gh = MagicMock()
    mock_gh.get_user.return_value = mock_owner

    with patch("agent.tools.github._get_client", return_value=mock_gh):
        result = await create_github_repo("emptyapp", {})

    assert result["status"] == "created"


async def test_create_github_repo_push_fails(monkeypatch):
    from agent.tools.github import create_github_repo

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")

    mock_repo = MagicMock()
    mock_repo.full_name = "testuser/failapp"
    mock_repo.html_url = "https://github.com/testuser/failapp"
    mock_repo.clone_url = "https://github.com/testuser/failapp.git"
    mock_repo.default_branch = "main"

    mock_owner = MagicMock()
    mock_owner.create_repo.return_value = mock_repo

    mock_gh = MagicMock()
    mock_gh.get_user.return_value = mock_owner

    with (
        patch("agent.tools.github._get_client", return_value=mock_gh),
        patch("agent.tools.github.push_files", new_callable=AsyncMock) as mock_push,
    ):
        mock_push.return_value = {"status": "error", "error": "push failed"}
        result = await create_github_repo("failapp", {"app.py": "code"})

    assert result["status"] == "error"


async def test_push_files_success(monkeypatch):
    from agent.tools.github import push_files

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")

    mock_ref = MagicMock()
    mock_ref.object.sha = "base_sha"

    mock_commit = MagicMock()
    mock_commit.sha = "new_commit_sha"

    mock_gh_repo = MagicMock()
    mock_gh_repo.default_branch = "main"
    mock_gh_repo.get_git_ref.return_value = mock_ref
    mock_gh_repo.get_git_tree.return_value = MagicMock()
    mock_gh_repo.create_git_blob.return_value.sha = "blob_sha"
    mock_gh_repo.create_git_tree.return_value = MagicMock()
    mock_gh_repo.create_git_commit.return_value = mock_commit
    mock_gh_repo.get_git_commit.return_value = MagicMock()

    mock_gh = MagicMock()
    mock_gh.get_repo.return_value = mock_gh_repo

    with patch("agent.tools.github._get_client", return_value=mock_gh):
        result = await push_files(
            {"full_name": "owner/repo"},
            {"app.py": "print('hello')", "README.md": "# App"},
            commit_message="Initial commit",
        )

    assert result["status"] == "pushed"
    assert result["commit_sha"] == "new_commit_sha"
    assert result["files_count"] == 2


async def test_push_files_no_token(monkeypatch):
    from agent.tools.github import push_files

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    result = await push_files({"full_name": "owner/repo"}, {"file.py": "content"})
    assert result["status"] == "error"


async def test_push_files_with_explicit_branch(monkeypatch):
    from agent.tools.github import push_files

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")

    mock_ref = MagicMock()
    mock_ref.object.sha = "base_sha"

    mock_commit = MagicMock()
    mock_commit.sha = "commit_sha_on_branch"

    mock_gh_repo = MagicMock()
    mock_gh_repo.get_git_ref.return_value = mock_ref
    mock_gh_repo.get_git_tree.return_value = MagicMock()
    mock_gh_repo.create_git_blob.return_value.sha = "blob_sha"
    mock_gh_repo.create_git_tree.return_value = MagicMock()
    mock_gh_repo.create_git_commit.return_value = mock_commit
    mock_gh_repo.get_git_commit.return_value = MagicMock()

    mock_gh = MagicMock()
    mock_gh.get_repo.return_value = mock_gh_repo

    with patch("agent.tools.github._get_client", return_value=mock_gh):
        result = await push_files(
            {"full_name": "owner/repo"},
            {"main.py": "code"},
            branch="feature-branch",
        )

    assert result["status"] == "pushed"
    mock_gh_repo.get_git_ref.assert_called_once_with("heads/feature-branch")


# ─── tools/web_search.py ─────────────────────────────────────────────────────


class TestResponsesOutputText:
    def test_output_text_present(self):
        from agent.tools.web_search import _responses_output_text

        payload = {"output_text": "hello world"}
        assert _responses_output_text(payload) == "hello world"

    def test_output_array_with_content_block(self):
        from agent.tools.web_search import _responses_output_text

        payload = {"output": [{"content": [{"text": "extracted text"}]}]}
        assert _responses_output_text(payload) == "extracted text"

    def test_output_array_with_output_text_block(self):
        from agent.tools.web_search import _responses_output_text

        payload = {"output": [{"content": [{"output_text": "from block"}]}]}
        assert _responses_output_text(payload) == "from block"

    def test_whitespace_only_output_text_falls_through(self):
        from agent.tools.web_search import _responses_output_text

        payload = {"output_text": "   ", "output": []}
        result = _responses_output_text(payload)
        assert result == ""

    def test_empty_payload(self):
        from agent.tools.web_search import _responses_output_text

        assert _responses_output_text({}) == ""

    def test_output_array_empty(self):
        from agent.tools.web_search import _responses_output_text

        assert _responses_output_text({"output": []}) == ""


async def test_web_search_no_api_key(monkeypatch):
    from agent.tools.web_search import web_search

    monkeypatch.delenv("GRADIENT_MODEL_ACCESS_KEY", raising=False)
    monkeypatch.delenv("DIGITALOCEAN_INFERENCE_KEY", raising=False)
    result = await web_search("test query")
    assert "error" in result
    assert result["results"] == []


async def test_web_search_chat_endpoint_success(monkeypatch):
    from agent.tools.web_search import web_search

    monkeypatch.setenv("GRADIENT_MODEL_ACCESS_KEY", "fake-key")

    response_data = {
        "choices": [{"message": {"content": '{"results": [{"title": "Result 1", "url": "https://example.com"}]}'}}]
    }

    mock_resp = MagicMock()
    mock_resp.json.return_value = response_data
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with (
        patch("agent.tools.web_search.httpx.AsyncClient", return_value=mock_client),
        patch("agent.tools.web_search.model_endpoint_type", return_value="chat"),
    ):
        result = await web_search("test query")

    assert "results" in result
    assert len(result["results"]) == 1


async def test_web_search_responses_endpoint_success(monkeypatch):
    from agent.tools.web_search import web_search

    monkeypatch.setenv("GRADIENT_MODEL_ACCESS_KEY", "fake-key")

    response_data = {"output_text": '{"results": [{"title": "Result 2"}]}'}

    mock_resp = MagicMock()
    mock_resp.json.return_value = response_data
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with (
        patch("agent.tools.web_search.httpx.AsyncClient", return_value=mock_client),
        patch("agent.tools.web_search.model_endpoint_type", return_value="responses"),
    ):
        result = await web_search("test query")

    assert "results" in result


async def test_web_search_json_decode_error(monkeypatch):
    from agent.tools.web_search import web_search

    monkeypatch.setenv("GRADIENT_MODEL_ACCESS_KEY", "fake-key")

    response_data = {"choices": [{"message": {"content": "not valid json at all"}}]}

    mock_resp = MagicMock()
    mock_resp.json.return_value = response_data
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with (
        patch("agent.tools.web_search.httpx.AsyncClient", return_value=mock_client),
        patch("agent.tools.web_search.model_endpoint_type", return_value="chat"),
    ):
        result = await web_search("test query")

    assert result["results"] == []
    assert "raw_response" in result


async def test_web_search_http_status_error(monkeypatch):
    from agent.tools.web_search import web_search

    monkeypatch.setenv("GRADIENT_MODEL_ACCESS_KEY", "fake-key")

    mock_error_resp = MagicMock()
    mock_error_resp.status_code = 429
    http_error = httpx.HTTPStatusError("rate limited", request=MagicMock(), response=mock_error_resp)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=http_error)

    with (
        patch("agent.tools.web_search.httpx.AsyncClient", return_value=mock_client),
        patch("agent.tools.web_search.model_endpoint_type", return_value="chat"),
    ):
        result = await web_search("test query")

    assert "error" in result
    assert "429" in result["error"]


async def test_web_search_timeout(monkeypatch):
    from agent.tools.web_search import web_search

    monkeypatch.setenv("GRADIENT_MODEL_ACCESS_KEY", "fake-key")

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

    with (
        patch("agent.tools.web_search.httpx.AsyncClient", return_value=mock_client),
        patch("agent.tools.web_search.model_endpoint_type", return_value="chat"),
    ):
        result = await web_search("test query")

    assert "error" in result
    assert "timed out" in result["error"].lower()


async def test_web_search_general_exception(monkeypatch):
    from agent.tools.web_search import web_search

    monkeypatch.setenv("GRADIENT_MODEL_ACCESS_KEY", "fake-key")

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=RuntimeError("unexpected"))

    with (
        patch("agent.tools.web_search.httpx.AsyncClient", return_value=mock_client),
        patch("agent.tools.web_search.model_endpoint_type", return_value="chat"),
    ):
        result = await web_search("test query")

    assert "error" in result


async def test_search_competitors_wraps_web_search(monkeypatch):
    from agent.tools.web_search import search_competitors

    monkeypatch.setenv("GRADIENT_MODEL_ACCESS_KEY", "fake-key")

    with patch("agent.tools.web_search.web_search", new_callable=AsyncMock) as mock_ws:
        mock_ws.return_value = {"results": [{"name": "Competitor"}]}
        result = await search_competitors("todo app")

    assert "results" in result
    call_args = mock_ws.call_args[0][0]
    assert "todo app" in call_args


async def test_search_tech_stack_wraps_web_search(monkeypatch):
    from agent.tools.web_search import search_tech_stack

    monkeypatch.setenv("GRADIENT_MODEL_ACCESS_KEY", "fake-key")

    with patch("agent.tools.web_search.web_search", new_callable=AsyncMock) as mock_ws:
        mock_ws.return_value = {"results": [{"framework": "Next.js"}]}
        result = await search_tech_stack("web app")

    assert "results" in result
    call_args = mock_ws.call_args[0][0]
    assert "web app" in call_args


# ─── tools/digitalocean.py ───────────────────────────────────────────────────


class TestBuildAppSpec:
    def test_basic_structure(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("GRADIENT_MODEL_ACCESS_KEY", raising=False)
        monkeypatch.delenv("DIGITALOCEAN_INFERENCE_KEY", raising=False)
        from agent.tools.digitalocean import build_app_spec

        spec = build_app_spec("myapp", "https://github.com/user/myapp")
        assert spec["name"] == "myapp"
        assert spec["region"] == "nyc"
        assert len(spec["services"]) == 1
        assert spec["services"][0]["name"] == "myapp-api"

    def test_with_frontend(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("GRADIENT_MODEL_ACCESS_KEY", raising=False)
        monkeypatch.delenv("DIGITALOCEAN_INFERENCE_KEY", raising=False)
        from agent.tools.digitalocean import build_app_spec

        spec = build_app_spec("myapp", "https://github.com/user/myapp", has_frontend=True)
        assert len(spec["services"]) == 2
        assert "ingress" in spec
        service_names = [s["name"] for s in spec["services"]]
        assert "myapp-api" in service_names
        assert "myapp-web" in service_names

    def test_repo_url_parsed(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("GRADIENT_MODEL_ACCESS_KEY", raising=False)
        monkeypatch.delenv("DIGITALOCEAN_INFERENCE_KEY", raising=False)
        from agent.tools.digitalocean import build_app_spec

        spec = build_app_spec("app", "https://github.com/myorg/myrepo.git")
        assert spec["services"][0]["github"]["repo"] == "myorg/myrepo"

    def test_with_database_url(self, monkeypatch):
        monkeypatch.setenv("GENERATED_APP_DATABASE_URL", "postgresql://user:pass@host:5432/db")
        monkeypatch.delenv("GENERATED_APP_INFERENCE_KEY", raising=False)
        monkeypatch.delenv("GRADIENT_MODEL_ACCESS_KEY", raising=False)
        monkeypatch.delenv("DIGITALOCEAN_INFERENCE_KEY", raising=False)
        from agent.tools.digitalocean import build_app_spec

        spec = build_app_spec("app", "https://github.com/user/app")
        env_keys = [e["key"] for e in spec["services"][0].get("envs", [])]
        assert "DATABASE_URL" in env_keys
        assert "POSTGRES_URL" in env_keys

    def test_with_inference_key(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("GENERATED_APP_DATABASE_URL", raising=False)
        monkeypatch.setenv("GENERATED_APP_INFERENCE_KEY", "test-inference-key")
        monkeypatch.delenv("DIGITALOCEAN_INFERENCE_KEY", raising=False)
        from agent.tools.digitalocean import build_app_spec

        spec = build_app_spec("app", "https://github.com/user/app")
        env_keys = [e["key"] for e in spec["services"][0].get("envs", [])]
        assert "GRADIENT_MODEL_ACCESS_KEY" in env_keys

    def test_name_truncated_to_32(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("GRADIENT_MODEL_ACCESS_KEY", raising=False)
        monkeypatch.delenv("DIGITALOCEAN_INFERENCE_KEY", raising=False)
        from agent.tools.digitalocean import build_app_spec

        long_name = "a" * 50
        spec = build_app_spec(long_name, "https://github.com/user/repo")
        assert len(spec["name"]) <= 32

    def test_asyncpg_url_converted_to_psycopg(self, monkeypatch):
        monkeypatch.setenv("GENERATED_APP_DATABASE_URL", "postgresql+asyncpg://user:pass@host/db")
        monkeypatch.delenv("GENERATED_APP_INFERENCE_KEY", raising=False)
        monkeypatch.delenv("GRADIENT_MODEL_ACCESS_KEY", raising=False)
        monkeypatch.delenv("DIGITALOCEAN_INFERENCE_KEY", raising=False)
        from agent.tools.digitalocean import build_app_spec

        spec = build_app_spec("app", "https://github.com/user/app")
        db_env = next(e for e in spec["services"][0]["envs"] if e["key"] == "DATABASE_URL")
        assert "psycopg" in db_env["value"]
        assert "asyncpg" not in db_env["value"]

    def test_postgres_url_converted(self, monkeypatch):
        monkeypatch.setenv("GENERATED_APP_DATABASE_URL", "postgres://user:pass@host/db")
        monkeypatch.delenv("GENERATED_APP_INFERENCE_KEY", raising=False)
        monkeypatch.delenv("GRADIENT_MODEL_ACCESS_KEY", raising=False)
        monkeypatch.delenv("DIGITALOCEAN_INFERENCE_KEY", raising=False)
        from agent.tools.digitalocean import build_app_spec

        spec = build_app_spec("app", "https://github.com/user/app")
        db_env = next(e for e in spec["services"][0]["envs"] if e["key"] == "DATABASE_URL")
        assert "psycopg" in db_env["value"]

    def test_deploy_on_push_enabled(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("GRADIENT_MODEL_ACCESS_KEY", raising=False)
        monkeypatch.delenv("DIGITALOCEAN_INFERENCE_KEY", raising=False)
        from agent.tools.digitalocean import build_app_spec

        spec = build_app_spec("app", "https://github.com/user/repo")
        assert spec["services"][0]["github"]["deploy_on_push"] is True

    def test_always_includes_do_inference_model_env(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("GRADIENT_MODEL_ACCESS_KEY", raising=False)
        monkeypatch.delenv("DIGITALOCEAN_INFERENCE_KEY", raising=False)
        from agent.tools.digitalocean import build_app_spec

        spec = build_app_spec("app", "https://github.com/user/repo")
        env_keys = [e["key"] for e in spec["services"][0].get("envs", [])]
        assert "DO_INFERENCE_MODEL" in env_keys


async def test_list_apps_success(monkeypatch):
    from agent.tools.digitalocean import list_apps

    monkeypatch.setenv("DIGITALOCEAN_API_TOKEN", "fake-token")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"apps": [{"id": "app-1", "name": "myapp"}, {"id": "app-2", "name": "otherapp"}]}
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("agent.tools.digitalocean.httpx.AsyncClient", return_value=mock_client):
        result = await list_apps()

    assert len(result) == 2
    assert result[0]["id"] == "app-1"


async def test_list_apps_no_token_returns_empty(monkeypatch):
    from agent.tools.digitalocean import list_apps

    monkeypatch.delenv("DIGITALOCEAN_API_TOKEN", raising=False)
    result = await list_apps()
    assert result == []


async def test_get_app_status_success(monkeypatch):
    from agent.tools.digitalocean import get_app_status

    monkeypatch.setenv("DIGITALOCEAN_API_TOKEN", "fake-token")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "app": {
            "id": "app-123",
            "active_deployment": {"phase": "ACTIVE"},
            "live_url": "https://myapp.ondigitalocean.app",
            "default_ingress": "https://myapp.ondigitalocean.app",
            "updated_at": "2024-01-01T00:00:00Z",
        }
    }
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("agent.tools.digitalocean.httpx.AsyncClient", return_value=mock_client):
        result = await get_app_status("app-123")

    assert result["app_id"] == "app-123"
    assert result["phase"] == "ACTIVE"
    assert result["live_url"] == "https://myapp.ondigitalocean.app"


async def test_get_app_status_no_token(monkeypatch):
    from agent.tools.digitalocean import get_app_status

    monkeypatch.delenv("DIGITALOCEAN_API_TOKEN", raising=False)
    result = await get_app_status("app-123")
    assert result["phase"] == "ERROR"


async def test_deploy_to_digitalocean_success(monkeypatch):
    from agent.tools.digitalocean import deploy_to_digitalocean

    monkeypatch.setenv("DIGITALOCEAN_API_TOKEN", "fake-token")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "app": {
            "id": "new-app-456",
            "default_ingress": "https://new-app.ondigitalocean.app",
        }
    }
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("agent.tools.digitalocean.httpx.AsyncClient", return_value=mock_client):
        result = await deploy_to_digitalocean("https://github.com/user/app", {"name": "testapp"})

    assert result["app_id"] == "new-app-456"
    assert result["status"] == "deploying"


async def test_deploy_to_digitalocean_no_token(monkeypatch):
    from agent.tools.digitalocean import deploy_to_digitalocean

    monkeypatch.delenv("DIGITALOCEAN_API_TOKEN", raising=False)
    result = await deploy_to_digitalocean("https://github.com/user/app", {})
    assert result["status"] == "error"
    assert "DIGITALOCEAN_API_TOKEN" in result["error"]


async def test_deploy_to_digitalocean_http_error(monkeypatch):
    from agent.tools.digitalocean import deploy_to_digitalocean

    monkeypatch.setenv("DIGITALOCEAN_API_TOKEN", "fake-token")

    mock_error_resp = MagicMock()
    mock_error_resp.status_code = 422
    mock_error_resp.text = "Unprocessable Entity"
    http_error = httpx.HTTPStatusError("422 error", request=MagicMock(), response=mock_error_resp)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=http_error)

    with patch("agent.tools.digitalocean.httpx.AsyncClient", return_value=mock_client):
        result = await deploy_to_digitalocean("https://github.com/user/app", {"name": "test"})

    assert result["status"] == "error"
    assert "422" in result["error"]


async def test_get_deploy_error_logs_no_token(monkeypatch):
    from agent.tools.digitalocean import get_deploy_error_logs

    monkeypatch.delenv("DIGITALOCEAN_API_TOKEN", raising=False)
    result = await get_deploy_error_logs("app-123")
    assert result == ""


async def test_get_deploy_error_logs_empty_deployments(monkeypatch):
    from agent.tools.digitalocean import get_deploy_error_logs

    monkeypatch.setenv("DIGITALOCEAN_API_TOKEN", "fake-token")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"deployments": []}
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("agent.tools.digitalocean.httpx.AsyncClient", return_value=mock_client):
        result = await get_deploy_error_logs("app-123")

    assert result == ""


async def test_get_deploy_error_logs_non_error_phase(monkeypatch):
    from agent.tools.digitalocean import get_deploy_error_logs

    monkeypatch.setenv("DIGITALOCEAN_API_TOKEN", "fake-token")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"deployments": [{"id": "dep-1", "phase": "ACTIVE", "spec": {"services": []}}]}
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("agent.tools.digitalocean.httpx.AsyncClient", return_value=mock_client):
        result = await get_deploy_error_logs("app-123")

    assert result == ""


async def test_get_deploy_error_logs_with_deployment_id(monkeypatch):
    from agent.tools.digitalocean import get_deploy_error_logs

    monkeypatch.setenv("DIGITALOCEAN_API_TOKEN", "fake-token")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"deployment": {"id": "dep-xyz", "phase": "ACTIVE", "spec": {}}}
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("agent.tools.digitalocean.httpx.AsyncClient", return_value=mock_client):
        result = await get_deploy_error_logs("app-123", deployment_id="dep-xyz")

    assert result == ""


async def test_wait_for_deployment_empty_app_id():
    from agent.tools.digitalocean import wait_for_deployment

    result = await wait_for_deployment("")
    assert result == ""


async def test_wait_for_deployment_active(monkeypatch):
    from agent.tools.digitalocean import wait_for_deployment

    monkeypatch.setenv("DIGITALOCEAN_API_TOKEN", "fake-token")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "app": {
            "active_deployment": {"phase": "ACTIVE"},
            "live_url": "https://myapp.ondigitalocean.app",
        }
    }
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("agent.tools.digitalocean.httpx.AsyncClient", return_value=mock_client):
        result = await wait_for_deployment("app-123", timeout_seconds=10, poll_interval=1)

    assert result == "https://myapp.ondigitalocean.app"


async def test_wait_for_deployment_error_phase(monkeypatch):
    from agent.tools.digitalocean import wait_for_deployment

    monkeypatch.setenv("DIGITALOCEAN_API_TOKEN", "fake-token")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "app": {
            "active_deployment": {"phase": "ERROR"},
            "live_url": "",
        }
    }
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("agent.tools.digitalocean.httpx.AsyncClient", return_value=mock_client):
        result = await wait_for_deployment("app-123", timeout_seconds=10)

    assert result == ""


async def test_wait_for_deployment_with_phase_change_callback(monkeypatch):
    from agent.tools.digitalocean import wait_for_deployment

    monkeypatch.setenv("DIGITALOCEAN_API_TOKEN", "fake-token")

    phases_seen = []

    async def on_phase(phase):
        phases_seen.append(phase)

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "app": {
            "active_deployment": {"phase": "ACTIVE"},
            "live_url": "https://myapp.ondigitalocean.app",
        }
    }
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("agent.tools.digitalocean.httpx.AsyncClient", return_value=mock_client):
        result = await wait_for_deployment("app-123", timeout_seconds=10, poll_interval=1, on_phase_change=on_phase)

    assert result == "https://myapp.ondigitalocean.app"
    assert "ACTIVE" in phases_seen


async def test_delete_app_success(monkeypatch):
    from agent.tools.digitalocean import delete_app

    monkeypatch.setenv("DIGITALOCEAN_API_TOKEN", "fake-token")

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.delete = AsyncMock(return_value=mock_resp)

    with patch("agent.tools.digitalocean.httpx.AsyncClient", return_value=mock_client):
        result = await delete_app("app-123")

    assert result["status"] == "deleted"
    assert result["app_id"] == "app-123"


async def test_delete_app_http_error(monkeypatch):
    from agent.tools.digitalocean import delete_app

    monkeypatch.setenv("DIGITALOCEAN_API_TOKEN", "fake-token")

    mock_error_resp = MagicMock()
    mock_error_resp.status_code = 404
    mock_error_resp.text = "Not Found"
    http_error = httpx.HTTPStatusError("not found", request=MagicMock(), response=mock_error_resp)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.delete = AsyncMock(side_effect=http_error)

    with patch("agent.tools.digitalocean.httpx.AsyncClient", return_value=mock_client):
        result = await delete_app("app-123")

    assert result["status"] == "error"


async def test_redeploy_app_success(monkeypatch):
    from agent.tools.digitalocean import redeploy_app

    monkeypatch.setenv("DIGITALOCEAN_API_TOKEN", "fake-token")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"deployment": {"id": "dep-789"}}
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("agent.tools.digitalocean.httpx.AsyncClient", return_value=mock_client):
        result = await redeploy_app("app-123")

    assert result["deployment_id"] == "dep-789"
    assert result["status"] == "deploying"


async def test_redeploy_app_http_error(monkeypatch):
    from agent.tools.digitalocean import redeploy_app

    monkeypatch.setenv("DIGITALOCEAN_API_TOKEN", "fake-token")

    mock_error_resp = MagicMock()
    mock_error_resp.status_code = 503
    mock_error_resp.text = "Service Unavailable"
    http_error = httpx.HTTPStatusError("service error", request=MagicMock(), response=mock_error_resp)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=http_error)

    with patch("agent.tools.digitalocean.httpx.AsyncClient", return_value=mock_client):
        result = await redeploy_app("app-123")

    assert result["status"] == "error"


# ─── tools/image_gen.py ──────────────────────────────────────────────────────


async def test_generate_image_no_api_key(monkeypatch):
    from agent.tools.image_gen import _generate_image

    monkeypatch.delenv("GRADIENT_MODEL_ACCESS_KEY", raising=False)
    monkeypatch.delenv("DIGITALOCEAN_INFERENCE_KEY", raising=False)
    result = await _generate_image("test prompt")
    assert result["image_url"] == ""
    assert "error" in result


async def test_generate_image_success(monkeypatch):
    from agent.tools.image_gen import _generate_image

    monkeypatch.setenv("GRADIENT_MODEL_ACCESS_KEY", "fake-key")

    invoke_resp = MagicMock()
    invoke_resp.json.return_value = {"request_id": "req-123"}
    invoke_resp.raise_for_status = MagicMock()

    status_resp = MagicMock()
    status_resp.json.return_value = {
        "status": "COMPLETED",
        "output": {"images": [{"url": "https://example.com/image.png"}]},
    }
    status_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=invoke_resp)
    mock_client.get = AsyncMock(return_value=status_resp)

    with (
        patch("agent.tools.image_gen.httpx.AsyncClient", return_value=mock_client),
        patch("agent.tools.image_gen.asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await _generate_image("test prompt", size="1024x1024", purpose="logo")

    assert result["image_url"] == "https://example.com/image.png"
    assert result["purpose"] == "logo"
    assert "prompt_used" in result


async def test_generate_image_status_has_error(monkeypatch):
    from agent.tools.image_gen import _generate_image

    monkeypatch.setenv("GRADIENT_MODEL_ACCESS_KEY", "fake-key")

    invoke_resp = MagicMock()
    invoke_resp.json.return_value = {"request_id": "req-456"}
    invoke_resp.raise_for_status = MagicMock()

    status_resp = MagicMock()
    status_resp.json.return_value = {"status": "FAILED", "error": "Generation failed due to NSFW content"}
    status_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=invoke_resp)
    mock_client.get = AsyncMock(return_value=status_resp)

    with (
        patch("agent.tools.image_gen.httpx.AsyncClient", return_value=mock_client),
        patch("agent.tools.image_gen.asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await _generate_image("test prompt")

    assert result["image_url"] == ""
    assert "error" in result


async def test_generate_image_http_error(monkeypatch):
    from agent.tools.image_gen import _generate_image

    monkeypatch.setenv("GRADIENT_MODEL_ACCESS_KEY", "fake-key")

    mock_error_resp = MagicMock()
    mock_error_resp.status_code = 401
    http_error = httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=mock_error_resp)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=http_error)

    with patch("agent.tools.image_gen.httpx.AsyncClient", return_value=mock_client):
        result = await _generate_image("test prompt")

    assert result["image_url"] == ""
    assert "401" in result["error"]


async def test_generate_image_timeout_exception(monkeypatch):
    from agent.tools.image_gen import _generate_image

    monkeypatch.setenv("GRADIENT_MODEL_ACCESS_KEY", "fake-key")

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

    with patch("agent.tools.image_gen.httpx.AsyncClient", return_value=mock_client):
        result = await _generate_image("test prompt")

    assert result["image_url"] == ""
    assert "timed out" in result["error"].lower()


async def test_generate_image_general_exception(monkeypatch):
    from agent.tools.image_gen import _generate_image

    monkeypatch.setenv("GRADIENT_MODEL_ACCESS_KEY", "fake-key")

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=RuntimeError("unexpected error"))

    with patch("agent.tools.image_gen.httpx.AsyncClient", return_value=mock_client):
        result = await _generate_image("test prompt")

    assert result["image_url"] == ""
    assert "error" in result


async def test_generate_image_landscape_size(monkeypatch):
    """Test that 1792x1024 maps to the correct FAL size."""
    from agent.tools.image_gen import _generate_image

    monkeypatch.setenv("GRADIENT_MODEL_ACCESS_KEY", "fake-key")

    invoke_resp = MagicMock()
    invoke_resp.json.return_value = {"request_id": "req-landscape"}
    invoke_resp.raise_for_status = MagicMock()

    status_resp = MagicMock()
    status_resp.json.return_value = {
        "status": "COMPLETED",
        "output": {"images": [{"url": "https://example.com/landscape.png"}]},
    }
    status_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=invoke_resp)
    mock_client.get = AsyncMock(return_value=status_resp)

    with (
        patch("agent.tools.image_gen.httpx.AsyncClient", return_value=mock_client),
        patch("agent.tools.image_gen.asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await _generate_image("test prompt", size="1792x1024", purpose="mockup")

    assert result["image_url"] == "https://example.com/landscape.png"
    # Verify the payload used landscape_16_9
    call_kwargs = mock_client.post.call_args.kwargs
    assert call_kwargs["json"]["input"]["image_size"] == "landscape_16_9"


async def test_generate_app_logo_delegates(monkeypatch):
    from agent.tools.image_gen import generate_app_logo

    monkeypatch.setenv("GRADIENT_MODEL_ACCESS_KEY", "fake-key")

    invoke_resp = MagicMock()
    invoke_resp.json.return_value = {"request_id": "req-logo"}
    invoke_resp.raise_for_status = MagicMock()

    status_resp = MagicMock()
    status_resp.json.return_value = {
        "status": "COMPLETED",
        "output": {"images": [{"url": "https://example.com/logo.png"}]},
    }
    status_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=invoke_resp)
    mock_client.get = AsyncMock(return_value=status_resp)

    with (
        patch("agent.tools.image_gen.httpx.AsyncClient", return_value=mock_client),
        patch("agent.tools.image_gen.asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await generate_app_logo("MyApp", "A task management app")

    assert result["image_url"] == "https://example.com/logo.png"
    assert result["purpose"] == "logo"
    # Prompt should include app name
    call_kwargs = mock_client.post.call_args.kwargs
    assert "MyApp" in call_kwargs["json"]["input"]["prompt"]


async def test_generate_placeholder_image_delegates(monkeypatch):
    from agent.tools.image_gen import generate_placeholder_image

    monkeypatch.setenv("GRADIENT_MODEL_ACCESS_KEY", "fake-key")

    invoke_resp = MagicMock()
    invoke_resp.json.return_value = {"request_id": "req-ph"}
    invoke_resp.raise_for_status = MagicMock()

    status_resp = MagicMock()
    status_resp.json.return_value = {
        "status": "COMPLETED",
        "output": {"images": [{"url": "https://example.com/placeholder.png"}]},
    }
    status_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=invoke_resp)
    mock_client.get = AsyncMock(return_value=status_resp)

    with (
        patch("agent.tools.image_gen.httpx.AsyncClient", return_value=mock_client),
        patch("agent.tools.image_gen.asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await generate_placeholder_image("a hero section image")

    assert result["image_url"] == "https://example.com/placeholder.png"
    assert result["purpose"] == "placeholder"


async def test_generate_app_logo_no_api_key(monkeypatch):
    from agent.tools.image_gen import generate_app_logo

    monkeypatch.delenv("GRADIENT_MODEL_ACCESS_KEY", raising=False)
    monkeypatch.delenv("DIGITALOCEAN_INFERENCE_KEY", raising=False)
    result = await generate_app_logo("MyApp", "desc")
    assert result["image_url"] == ""
    assert "error" in result


async def test_generate_ui_mockup_delegates(monkeypatch):
    from agent.tools.image_gen import generate_ui_mockup

    monkeypatch.setenv("GRADIENT_MODEL_ACCESS_KEY", "fake-key")

    invoke_resp = MagicMock()
    invoke_resp.json.return_value = {"request_id": "req-ui"}
    invoke_resp.raise_for_status = MagicMock()

    status_resp = MagicMock()
    status_resp.json.return_value = {
        "status": "COMPLETED",
        "output": {"images": [{"url": "https://example.com/mockup.png"}]},
    }
    status_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=invoke_resp)
    mock_client.get = AsyncMock(return_value=status_resp)

    with (
        patch("agent.tools.image_gen.httpx.AsyncClient", return_value=mock_client),
        patch("agent.tools.image_gen.asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await generate_ui_mockup("a task management dashboard")

    assert result["image_url"] == "https://example.com/mockup.png"
    assert result["purpose"] == "mockup"
