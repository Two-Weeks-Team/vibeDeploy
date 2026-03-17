from unittest.mock import AsyncMock, patch

import pytest

from agent.zero_prompt.events import (
    ZP_TRANSCRIPT_COMPLETE,
    ZP_TRANSCRIPT_START,
    transcript_complete_event,
    transcript_start_event,
)
from agent.zero_prompt.schemas import TranscriptArtifact
from agent.zero_prompt.transcript import fetch_transcript_artifact

_TRANSCRIPT_MODULE = "agent.zero_prompt.transcript.extract_youtube_transcript"


@pytest.mark.asyncio
async def test_successful_transcript_returns_auto_source():
    transcript_text = "Hello world this is the video transcript content here"
    with patch(_TRANSCRIPT_MODULE, new=AsyncMock(return_value=transcript_text)):
        artifact = await fetch_transcript_artifact("abc123")

    assert artifact.video_id == "abc123"
    assert artifact.text == transcript_text
    assert artifact.source == "auto"


@pytest.mark.asyncio
async def test_metadata_fallback_when_transcript_missing():
    metadata_text = "Video Title: My Tutorial\nChannel: TestChan\nDescription:\nThis is a great video"
    with patch(_TRANSCRIPT_MODULE, new=AsyncMock(return_value=metadata_text)):
        artifact = await fetch_transcript_artifact("xyz789")

    assert artifact.video_id == "xyz789"
    assert artifact.source == "metadata_fallback"
    assert artifact.text == metadata_text


@pytest.mark.asyncio
async def test_token_count_is_calculated_from_text():
    transcript_text = "one two three four five"
    with patch(_TRANSCRIPT_MODULE, new=AsyncMock(return_value=transcript_text)):
        artifact = await fetch_transcript_artifact("vid001")

    assert artifact.token_count == 5


@pytest.mark.asyncio
async def test_error_string_returns_error_source():
    with patch(_TRANSCRIPT_MODULE, new=AsyncMock(return_value="[Error: HTTP 429 Too Many Requests]")):
        artifact = await fetch_transcript_artifact("vid002")

    assert artifact.source == "error"
    assert artifact.text == ""
    assert artifact.token_count == 0


@pytest.mark.asyncio
async def test_exception_during_extraction_returns_error_source():
    with patch(_TRANSCRIPT_MODULE, new=AsyncMock(side_effect=RuntimeError("network failure"))):
        artifact = await fetch_transcript_artifact("vid003")

    assert artifact.source == "error"
    assert artifact.text == ""
    assert artifact.token_count == 0
    assert artifact.video_id == "vid003"


@pytest.mark.asyncio
async def test_video_id_is_preserved_in_artifact():
    with patch(_TRANSCRIPT_MODULE, new=AsyncMock(return_value="some transcript")):
        artifact = await fetch_transcript_artifact("myVideoId42")

    assert artifact.video_id == "myVideoId42"


def test_transcript_artifact_model_defaults():
    artifact = TranscriptArtifact(
        video_id="test",
        text="hello world",
        source="auto",
        token_count=2,
    )
    assert artifact.language is None
    assert artifact.token_count == 2
    assert artifact.source == "auto"


def test_transcript_artifact_accepts_all_source_values():
    for src in ("manual", "auto", "metadata_fallback", "error"):
        a = TranscriptArtifact(video_id="v", text="", source=src, token_count=0)
        assert a.source == src


def test_transcript_start_event_structure():
    event = transcript_start_event("vid123")
    assert event["type"] == ZP_TRANSCRIPT_START
    assert event["video_id"] == "vid123"


def test_transcript_complete_event_structure():
    event = transcript_complete_event("vid456", "auto", 42)
    assert event["type"] == ZP_TRANSCRIPT_COMPLETE
    assert event["video_id"] == "vid456"
    assert event["source"] == "auto"
    assert event["token_count"] == 42


@pytest.mark.asyncio
async def test_metadata_fallback_uses_channel_marker():
    metadata_text = "Channel: SomeChan\nTags: ai, ml"
    with patch(_TRANSCRIPT_MODULE, new=AsyncMock(return_value=metadata_text)):
        artifact = await fetch_transcript_artifact("vid004")

    assert artifact.source == "metadata_fallback"


@pytest.mark.asyncio
async def test_token_count_zero_for_error():
    with patch(_TRANSCRIPT_MODULE, new=AsyncMock(return_value="[Error: unavailable]")):
        artifact = await fetch_transcript_artifact("vid005")

    assert artifact.token_count == 0
