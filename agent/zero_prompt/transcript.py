"""Transcript extraction for the zero-prompt pipeline."""

import logging

from agent.tools.youtube import extract_youtube_transcript
from agent.zero_prompt.schemas import TranscriptArtifact

logger = logging.getLogger(__name__)

# Markers that appear in yt-dlp metadata fallback output (_build_metadata_context)
_METADATA_MARKERS = ("Video Title:", "Channel:", "Description:\n", "Tags:", "Duration:")


async def fetch_transcript_artifact(video_id: str) -> TranscriptArtifact:
    """Fetch a YouTube transcript and return a structured TranscriptArtifact.

    Source mapping:
    - "auto"              — transcript extracted from auto-generated or manual captions
    - "metadata_fallback" — no captions available; metadata (title/description) used instead
    - "error"             — extraction failed or returned an error string
    """
    url = f"https://youtube.com/watch?v={video_id}"

    try:
        text = await extract_youtube_transcript(url)
    except Exception as exc:
        logger.warning("Transcript extraction raised for %s: %s", video_id, str(exc)[:200])
        return TranscriptArtifact(
            video_id=video_id,
            text="",
            source="error",
            language=None,
            token_count=0,
        )

    if text.startswith("[Error:"):
        return TranscriptArtifact(
            video_id=video_id,
            text="",
            source="error",
            language=None,
            token_count=0,
        )

    if any(marker in text for marker in _METADATA_MARKERS):
        source = "metadata_fallback"
    else:
        source = "auto"

    token_count = len(text.split())

    return TranscriptArtifact(
        video_id=video_id,
        text=text,
        source=source,
        language=None,
        token_count=token_count,
    )
