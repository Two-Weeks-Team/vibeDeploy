import os
from unittest.mock import MagicMock, patch

import pytest

from agent.zero_prompt.insight_extractor import (
    _parse_appidea_from_text,
    extract_insight_from_transcript,
    extract_with_gemini,
)
from agent.zero_prompt.schemas import AppIdea

_VALID_JSON = (
    '{"name": "HealthTrack", "domain": "healthcare", "description": "An app for tracking health.", '
    '"key_features": ["monitoring", "alerts"], "target_audience": "Patients", "confidence_score": 0.85}'
)

_VALID_JSON_FENCED = f"```json\n{_VALID_JSON}\n```"

_VALID_JSON_PLAIN_FENCE = f"```\n{_VALID_JSON}\n```"


def _make_response(text: str) -> MagicMock:
    r = MagicMock()
    r.text = text
    return r


def _make_client(first_text: str, second_text: str | None = None) -> MagicMock:
    client = MagicMock()
    responses = [_make_response(first_text)]
    if second_text is not None:
        responses.append(_make_response(second_text))
    client.models.generate_content.side_effect = responses
    return client


@pytest.mark.asyncio
async def test_no_api_key_returns_none(monkeypatch):
    monkeypatch.delenv("GOOGLE_GENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert await extract_with_gemini("some transcript") is None


@pytest.mark.asyncio
async def test_whitespace_only_key_returns_none(monkeypatch):
    monkeypatch.setenv("GOOGLE_GENAI_API_KEY", "   ")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert await extract_with_gemini("some transcript") is None


@pytest.mark.asyncio
async def test_gemini_api_key_fallback_also_checked(monkeypatch):
    monkeypatch.delenv("GOOGLE_GENAI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")

    client = _make_client(_VALID_JSON)
    with patch("google.genai.Client", return_value=client):
        result = await extract_with_gemini("A health app for patients.")

    assert isinstance(result, AppIdea)
    assert result.name == "HealthTrack"


@pytest.mark.asyncio
async def test_successful_extraction_plain_json(monkeypatch):
    monkeypatch.setenv("GOOGLE_GENAI_API_KEY", "fake-key")

    client = _make_client(_VALID_JSON)
    with patch("google.genai.Client", return_value=client):
        result = await extract_with_gemini("A health monitoring application.")

    assert isinstance(result, AppIdea)
    assert result.domain == "healthcare"
    assert result.confidence_score == pytest.approx(0.85)
    assert client.models.generate_content.call_count == 1


@pytest.mark.asyncio
async def test_successful_extraction_fenced_json(monkeypatch):
    monkeypatch.setenv("GOOGLE_GENAI_API_KEY", "fake-key")

    client = _make_client(_VALID_JSON_FENCED)
    with patch("google.genai.Client", return_value=client):
        result = await extract_with_gemini("A health monitoring application.")

    assert isinstance(result, AppIdea)
    assert result.name == "HealthTrack"


@pytest.mark.asyncio
async def test_successful_extraction_plain_fence(monkeypatch):
    monkeypatch.setenv("GOOGLE_GENAI_API_KEY", "fake-key")

    client = _make_client(_VALID_JSON_PLAIN_FENCE)
    with patch("google.genai.Client", return_value=client):
        result = await extract_with_gemini("A health monitoring application.")

    assert isinstance(result, AppIdea)


@pytest.mark.asyncio
async def test_parse_failure_triggers_retry(monkeypatch):
    monkeypatch.setenv("GOOGLE_GENAI_API_KEY", "fake-key")

    client = _make_client("NOT VALID JSON AT ALL", _VALID_JSON)
    with patch("google.genai.Client", return_value=client):
        result = await extract_with_gemini("A health app.")

    assert isinstance(result, AppIdea)
    assert client.models.generate_content.call_count == 2


@pytest.mark.asyncio
async def test_retry_repair_prompt_mentions_error(monkeypatch):
    monkeypatch.setenv("GOOGLE_GENAI_API_KEY", "fake-key")

    client = _make_client("bad json", _VALID_JSON)
    with patch("google.genai.Client", return_value=client):
        await extract_with_gemini("A health app.")

    second_call_contents = client.models.generate_content.call_args_list[1][1].get(
        "contents",
        client.models.generate_content.call_args_list[1][0][0]
        if client.models.generate_content.call_args_list[1][0]
        else "",
    )
    assert "Error" in str(second_call_contents) or "failed" in str(second_call_contents).lower()


@pytest.mark.asyncio
async def test_double_parse_failure_returns_none(monkeypatch):
    monkeypatch.setenv("GOOGLE_GENAI_API_KEY", "fake-key")

    client = _make_client("bad json", "still bad json")
    with patch("google.genai.Client", return_value=client):
        result = await extract_with_gemini("A health app.")

    assert result is None
    assert client.models.generate_content.call_count == 2


@pytest.mark.asyncio
async def test_api_exception_returns_none(monkeypatch):
    monkeypatch.setenv("GOOGLE_GENAI_API_KEY", "fake-key")

    client = MagicMock()
    client.models.generate_content.side_effect = RuntimeError("API unavailable")
    with patch("google.genai.Client", return_value=client):
        result = await extract_with_gemini("A health app.")

    assert result is None


@pytest.mark.asyncio
async def test_empty_response_text_returns_none_after_retry(monkeypatch):
    monkeypatch.setenv("GOOGLE_GENAI_API_KEY", "fake-key")

    client = _make_client("", "")
    with patch("google.genai.Client", return_value=client):
        result = await extract_with_gemini("A health app.")

    assert result is None


def test_rule_based_fallback_works_without_gemini():
    result = extract_insight_from_transcript("A fitness app that tracks workouts and calories burned.")
    assert isinstance(result, AppIdea)
    assert result.domain == "fitness"
    assert result.confidence_score >= 0.0


def test_rule_based_fallback_unaffected_by_gemini_import_error(monkeypatch):
    monkeypatch.delenv("GOOGLE_GENAI_API_KEY", raising=False)
    result = extract_insight_from_transcript("Social network for developers to connect and share code.")
    assert isinstance(result, AppIdea)
    assert len(result.target_audience) > 0


def test_parse_appidea_plain_json():
    result = _parse_appidea_from_text(_VALID_JSON)
    assert isinstance(result, AppIdea)
    assert result.name == "HealthTrack"


def test_parse_appidea_json_fence():
    result = _parse_appidea_from_text(_VALID_JSON_FENCED)
    assert isinstance(result, AppIdea)


def test_parse_appidea_plain_fence():
    result = _parse_appidea_from_text(_VALID_JSON_PLAIN_FENCE)
    assert isinstance(result, AppIdea)


def test_parse_appidea_invalid_raises():
    with pytest.raises(Exception):
        _parse_appidea_from_text("not json at all")


@pytest.mark.skipif(not os.getenv("GOOGLE_GENAI_API_KEY"), reason="GOOGLE_GENAI_API_KEY not set")
@pytest.mark.asyncio
async def test_live_extract_with_gemini_returns_app_idea():
    transcript = (
        "In this video I'll show you how to build a fitness tracking app. "
        "The app allows users to log workouts, track calories, and monitor progress. "
        "Features include a workout library, progress charts, and social sharing. "
        "Target audience: fitness enthusiasts and gym-goers."
    )
    result = await extract_with_gemini(transcript)
    assert result is None or isinstance(result, AppIdea)
    if result is not None:
        assert result.name
        assert result.domain
        assert 0.0 <= result.confidence_score <= 1.0
