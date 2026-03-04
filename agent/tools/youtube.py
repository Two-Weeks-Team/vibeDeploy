"""YouTube transcript extraction tools for vibeDeploy."""

import re
from typing import Optional


def is_youtube_url(text: str) -> bool:
    """Check if text contains a YouTube URL."""
    patterns = [
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+",
        r"(?:https?://)?(?:www\.)?youtu\.be/[\w-]+",
        r"(?:https?://)?(?:www\.)?youtube\.com/embed/[\w-]+",
        r"(?:https?://)?(?:www\.)?youtube\.com/shorts/[\w-]+",
    ]
    return any(re.search(p, text) for p in patterns)


def extract_video_id(url: str) -> Optional[str]:
    """Extract video ID from various YouTube URL formats."""
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/shorts/)([\w-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


async def extract_youtube_transcript(
    url: str,
    languages: Optional[list[str]] = None,
) -> str:
    """Extract transcript text from a YouTube video.

    Args:
        url: YouTube URL or video ID
        languages: Priority list of language codes (default: ['en', 'ko'])

    Returns:
        Full transcript text, or error string starting with '['
    """
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        NoTranscriptFound,
        TranscriptsDisabled,
        VideoUnavailable,
    )

    video_id = extract_video_id(url) if "youtube" in url or "youtu.be" in url else url
    if not video_id:
        return "[Error: Could not extract video ID from URL]"

    langs = languages or ["en", "ko", "ja", "zh"]

    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id, languages=langs)

        full_text = " ".join(snippet.text for snippet in transcript)
        return full_text.strip()

    except TranscriptsDisabled:
        return "[Error: Transcripts are disabled for this video]"
    except NoTranscriptFound:
        return f"[Error: No transcript found in languages: {langs}]"
    except VideoUnavailable:
        return "[Error: Video is unavailable]"
    except Exception as e:
        return f"[Error: {str(e)[:200]}]"


async def get_transcript_with_timestamps(
    url: str,
    languages: Optional[list[str]] = None,
) -> list[dict]:
    """Get transcript with timestamp data for visual segment detection.

    Returns:
        List of dicts with 'text', 'start', 'duration' keys
    """
    from youtube_transcript_api import YouTubeTranscriptApi

    video_id = extract_video_id(url)
    if not video_id:
        return []

    langs = languages or ["en", "ko", "ja", "zh"]

    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id, languages=langs)
        return [{"text": s.text, "start": s.start, "duration": s.duration} for s in transcript]
    except Exception:
        return []


async def detect_visual_segments(transcript: str, llm=None) -> list[dict]:
    """Detect segments in transcript that reference visual content.

    Keywords: 'look at', 'see here', 'as shown', 'demo', 'screen',
    '여기 보시면', '화면', '데모'
    """
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
    """Extract frames at given timestamps.

    Note: Simplified for hackathon - returns timestamp metadata only.
    Full implementation would use yt-dlp + ffmpeg.
    """
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
