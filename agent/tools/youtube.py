"""YouTube transcript extraction using yt-dlp."""

import logging
import os
import re
from typing import Optional

import requests

try:
    from gradient_adk.tracing import trace_tool
except ImportError:

    def trace_tool(name):
        def _noop(fn):
            return fn

        return _noop


logger = logging.getLogger(__name__)


def _build_metadata_context_from_snippet(snippet: dict) -> str:
    title = snippet.get("title", "") or ""
    description = (snippet.get("description", "") or "")[:2000]
    channel = snippet.get("channelTitle", "") or ""
    tags = snippet.get("tags", []) or []

    parts = []
    if title:
        parts.append(f"Video Title: {title}")
    if channel:
        parts.append(f"Channel: {channel}")
    if tags:
        parts.append(f"Tags: {', '.join(tags[:15])}")
    if description:
        parts.append(f"Description:\n{description}")
    return "\n".join(parts) if parts else ""


def _fetch_video_metadata_fallback(video_id: str) -> str:
    api_key = ""
    for key_name in ("YOUTUBE_DATA_API_KEY", "YOUTUBE_API_KEY"):
        api_key = api_key or os.environ.get(key_name, "").strip()

    if api_key:
        try:
            resp = requests.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={"part": "snippet", "id": video_id, "key": api_key},
                timeout=15,
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
            if items:
                snippet = items[0].get("snippet", {}) or {}
                context = _build_metadata_context_from_snippet(snippet)
                if context:
                    return context
        except requests.RequestException as exc:
            logger.debug("YouTube Data API metadata fallback failed: %s", exc)

    try:
        resp = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return _build_metadata_context_from_snippet(
            {"title": data.get("title", ""), "channelTitle": data.get("author_name", "")}
        )
    except requests.RequestException as exc:
        logger.debug("YouTube oEmbed fallback failed: %s", exc)

    return ""


def is_youtube_url(text: str) -> bool:
    patterns = [
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+",
        r"(?:https?://)?(?:www\.)?youtu\.be/[\w-]+",
        r"(?:https?://)?(?:www\.)?youtube\.com/embed/[\w-]+",
        r"(?:https?://)?(?:www\.)?youtube\.com/shorts/[\w-]+",
    ]
    return any(re.search(p, text) for p in patterns)


def extract_first_youtube_url(text: str) -> Optional[str]:
    patterns = [
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+(?:[^\s)]*)?",
        r"(?:https?://)?(?:www\.)?youtu\.be/[\w-]+(?:[^\s)]*)?",
        r"(?:https?://)?(?:www\.)?youtube\.com/embed/[\w-]+(?:[^\s)]*)?",
        r"(?:https?://)?(?:www\.)?youtube\.com/shorts/[\w-]+(?:[^\s)]*)?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return None


def extract_video_id(url: str) -> Optional[str]:
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/shorts/)([\w-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


@trace_tool("extract_youtube_transcript")
async def extract_youtube_transcript(
    url: str,
    languages: Optional[list[str]] = None,
) -> str:
    """Extract transcript from YouTube video using yt-dlp.

    Tries subtitle extraction first. If IP-blocked (429), falls back to
    video metadata (title + description + tags) as context for the AI pipeline.
    """
    import yt_dlp

    video_id = extract_video_id(url) if ("youtube" in url or "youtu.be" in url) else url
    if not video_id:
        return "[Error: Could not extract video ID from URL]"

    langs = languages or ["en", "ko", "ja", "zh"]

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False, process=False)

        subtitles = info.get("subtitles", {})
        automatic_captions = info.get("automatic_captions", {})

        for lang in langs:
            subtitle_list = subtitles.get(lang, []) or automatic_captions.get(lang, [])
            if not subtitle_list:
                continue

            text = _fetch_subtitle_text(subtitle_list)
            if text:
                source = "manual" if lang in subtitles else "auto-generated"
                logger.info("Extracted %s %s transcript (%d chars)", source, lang, len(text))
                return text

        logger.info("Subtitle fetch failed (likely IP-blocked), using video metadata fallback")
        metadata_context = _build_metadata_context(info)
        if metadata_context:
            return metadata_context
        return _fetch_video_metadata_fallback(video_id)

    except Exception as e:
        error_msg = str(e)[:200]
        logger.warning("yt-dlp extraction failed: %s", error_msg)
        metadata_context = _fetch_video_metadata_fallback(video_id)
        if metadata_context:
            return metadata_context
        return f"[Error: {error_msg}]"


def _build_metadata_context(info: dict) -> str:
    title = info.get("title", "")
    description = (info.get("description", "") or "")[:2000]
    channel = info.get("channel", "") or info.get("uploader", "")
    tags = info.get("tags", []) or []
    categories = info.get("categories", []) or []
    duration = info.get("duration", 0)

    parts = []
    if title:
        parts.append(f"Video Title: {title}")
    if channel:
        parts.append(f"Channel: {channel}")
    if categories:
        parts.append(f"Category: {', '.join(categories)}")
    if tags:
        parts.append(f"Tags: {', '.join(tags[:15])}")
    if duration:
        mins = duration // 60
        secs = duration % 60
        parts.append(f"Duration: {mins}m {secs}s")
    if description:
        parts.append(f"Description:\n{description}")

    return "\n".join(parts) if parts else "[Error: No metadata available]"


def _fetch_subtitle_text(subtitle_list: list[dict]) -> Optional[str]:
    json3_entries = [s for s in subtitle_list if s.get("ext") == "json3"]
    vtt_entries = [s for s in subtitle_list if s.get("ext") == "vtt"]
    fallback = subtitle_list[:1]

    for entry in json3_entries + vtt_entries + fallback:
        sub_url = entry.get("url")
        if not sub_url:
            continue

        try:
            resp = requests.get(sub_url, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.debug("Failed to fetch subtitle URL: %s", e)
            continue

        if entry.get("ext") == "json3":
            return _parse_json3(resp.json())

        return _parse_vtt_or_plain(resp.text)

    return None


def _parse_json3(data: dict) -> str:
    """Parse YouTube json3 subtitle format: {events: [{segs: [{utf8: "text"}]}]}"""
    parts = []
    for event in data.get("events", []):
        for seg in event.get("segs", []):
            text = seg.get("utf8", "")
            if text and text.strip() != "\n":
                parts.append(text)
    return " ".join(parts).strip() if parts else ""


def _parse_vtt_or_plain(content: str) -> str:
    lines = content.split("\n")
    parts = []
    for line in lines:
        line = line.strip()
        if not line or line.isdigit() or "-->" in line or line.startswith("WEBVTT"):
            continue
        clean = re.sub(r"<[^>]+>", "", line)
        if clean:
            parts.append(clean)
    return " ".join(parts).strip() if parts else ""


async def get_transcript_with_timestamps(
    url: str,
    languages: Optional[list[str]] = None,
) -> list[dict]:
    import yt_dlp

    video_id = extract_video_id(url)
    if not video_id:
        return []

    langs = languages or ["en", "ko", "ja", "zh"]

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": langs,
        "skip_download": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        subtitles = info.get("subtitles", {})
        automatic_captions = info.get("automatic_captions", {})

        for lang in langs:
            subtitle_list = subtitles.get(lang, []) or automatic_captions.get(lang, [])
            json3_entries = [s for s in subtitle_list if s.get("ext") == "json3"]
            if not json3_entries:
                continue

            resp = requests.get(json3_entries[0]["url"], timeout=15)
            resp.raise_for_status()
            data = resp.json()

            return [
                {
                    "text": " ".join(seg.get("utf8", "") for seg in event.get("segs", [])),
                    "start": event.get("tStartMs", 0) / 1000.0,
                    "duration": event.get("dDurationMs", 0) / 1000.0,
                }
                for event in data.get("events", [])
                if event.get("segs")
            ]

    except Exception:
        return []

    return []


@trace_tool("detect_visual_segments")
async def detect_visual_segments(transcript: str, llm=None) -> list[dict]:
    if not transcript:
        return []

    visual_keywords = [
        "look at",
        "see here",
        "as shown",
        "demo",
        "screen",
        "watch",
        "visual",
        "display",
        "interface",
        "UI",
        "여기 보시면",
        "화면",
        "보여드",
        "데모",
    ]

    segments = []
    sentences = re.split(r"[.!?\n]+", transcript)
    for i, sentence in enumerate(sentences):
        sentence_lower = sentence.lower().strip()
        if any(kw.lower() in sentence_lower for kw in visual_keywords):
            segments.append(
                {
                    "index": i,
                    "text": sentence.strip(),
                    "keywords_found": [kw for kw in visual_keywords if kw.lower() in sentence_lower],
                }
            )

    return segments


async def extract_video_frames(url: str, timestamps: list[float]) -> list[dict]:
    video_id = extract_video_id(url)
    if not video_id:
        return []

    return [
        {
            "timestamp": ts,
            "video_id": video_id,
            "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/0.jpg",
        }
        for ts in timestamps
    ]
