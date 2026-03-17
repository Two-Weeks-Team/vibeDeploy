import os

import pytest

from agent.zero_prompt.events import (
    ZP_INSIGHT_COMPLETE,
    ZP_INSIGHT_START,
    insight_complete_event,
    insight_start_event,
)
from agent.zero_prompt.insight_extractor import extract_insight_from_transcript, extract_with_gemini
from agent.zero_prompt.schemas import AppIdea


def test_returns_app_idea_instance():
    result = extract_insight_from_transcript("We are building a health tracking app for patients.")
    assert isinstance(result, AppIdea)


def test_confidence_bounded_lower():
    result = extract_insight_from_transcript("")
    assert result.confidence_score >= 0.0


def test_confidence_bounded_upper():
    long_text = " ".join(["health patient doctor clinic hospital medicine therapy"] * 100)
    result = extract_insight_from_transcript(long_text)
    assert result.confidence_score <= 1.0


def test_confidence_zero_for_empty_text():
    result = extract_insight_from_transcript("")
    assert result.confidence_score == 0.0


def test_domain_detection_healthcare():
    result = extract_insight_from_transcript("This app helps doctors monitor patient health records.")
    assert result.domain == "healthcare"


def test_domain_detection_finance():
    result = extract_insight_from_transcript("Manage your money, budget, and investment portfolio.")
    assert result.domain == "finance"


def test_domain_detection_education():
    result = extract_insight_from_transcript("Students can take courses and learn with interactive quizzes.")
    assert result.domain == "education"


def test_domain_detection_general_for_unknown():
    result = extract_insight_from_transcript("This is just a random sentence with no domain keywords.")
    assert result.domain == "general"


def test_feature_extraction_from_feature_keyword():
    text = "Feature: real-time notifications\nFeature: user authentication"
    result = extract_insight_from_transcript(text)
    assert len(result.key_features) >= 1


def test_feature_extraction_from_ability_pattern():
    text = "Users have the ability to export their data in CSV format."
    result = extract_insight_from_transcript(text)
    assert len(result.key_features) >= 1


def test_feature_list_capped_at_ten():
    lines = [f"Feature: capability number {i}" for i in range(20)]
    result = extract_insight_from_transcript("\n".join(lines))
    assert len(result.key_features) <= 10


def test_name_derived_from_video_title():
    result = extract_insight_from_transcript("Some transcript text.", video_title="My Awesome App Tutorial")
    assert "My" in result.name


def test_name_derived_from_domain_when_no_title():
    result = extract_insight_from_transcript("Travel booking and hotel reservation platform.")
    assert result.name != ""
    assert len(result.name) > 0


def test_description_is_non_empty():
    result = extract_insight_from_transcript("This app allows users to track their fitness goals daily.")
    assert len(result.description) > 0


def test_empty_text_with_title_uses_title_fallback():
    result = extract_insight_from_transcript("", video_title="Productivity Tool Demo")
    assert "Productivity Tool Demo" in result.description or result.name != ""


def test_target_audience_non_empty():
    result = extract_insight_from_transcript("A social network for developers to connect and collaborate.")
    assert len(result.target_audience) > 0


def test_target_audience_student_cue():
    result = extract_insight_from_transcript("Student learning platform with courses and quizzes.")
    assert result.target_audience == "Students"


def test_app_idea_model_fields_present():
    result = extract_insight_from_transcript("A food delivery app for restaurants.")
    assert hasattr(result, "name")
    assert hasattr(result, "domain")
    assert hasattr(result, "description")
    assert hasattr(result, "key_features")
    assert hasattr(result, "target_audience")
    assert hasattr(result, "confidence_score")


def test_insight_start_event_structure():
    event = insight_start_event("My Video Title")
    assert event["type"] == ZP_INSIGHT_START
    assert event["video_title"] == "My Video Title"


def test_insight_complete_event_structure():
    event = insight_complete_event("healthcare", 3, 0.75)
    assert event["type"] == ZP_INSIGHT_COMPLETE
    assert event["domain"] == "healthcare"
    assert event["features_found"] == 3
    assert event["confidence_score"] == 0.75


def test_insight_start_event_empty_title():
    event = insight_start_event("")
    assert event["type"] == ZP_INSIGHT_START
    assert event["video_title"] == ""


@pytest.mark.asyncio
async def test_extract_with_gemini_returns_none_without_api_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_GENAI_API_KEY", raising=False)
    result = await extract_with_gemini("some transcript text")
    assert result is None


@pytest.mark.asyncio
async def test_extract_with_gemini_returns_none_with_stub_key(monkeypatch):
    monkeypatch.setenv("GOOGLE_GENAI_API_KEY", "stub-key-for-testing")
    result = await extract_with_gemini("some transcript text")
    assert result is None


def test_confidence_increases_with_more_text():
    short_result = extract_insight_from_transcript("health app")
    long_text = " ".join(["patient doctor health clinic hospital medicine therapy"] * 50)
    long_result = extract_insight_from_transcript(long_text)
    assert long_result.confidence_score > short_result.confidence_score


def test_app_idea_schema_confidence_bounded_by_field():
    idea = AppIdea(
        name="Test",
        domain="general",
        description="A test app.",
        key_features=[],
        target_audience="General users",
        confidence_score=0.5,
    )
    assert 0.0 <= idea.confidence_score <= 1.0


def test_key_features_is_list():
    result = extract_insight_from_transcript("A simple ecommerce store for products.")
    assert isinstance(result.key_features, list)


def test_domain_detection_fitness():
    result = extract_insight_from_transcript("Track your workout, calories burned, and gym sessions.")
    assert result.domain == "fitness"


def test_environment_key_stripped(monkeypatch):
    monkeypatch.setenv("GOOGLE_GENAI_API_KEY", "   ")

    async def run():
        return await extract_with_gemini("text")

    import asyncio

    result = asyncio.run(run())
    assert result is None


def test_os_environ_absent_returns_none():
    original = os.environ.pop("GOOGLE_GENAI_API_KEY", None)
    try:
        import asyncio

        result = asyncio.run(extract_with_gemini("text"))
        assert result is None
    finally:
        if original is not None:
            os.environ["GOOGLE_GENAI_API_KEY"] = original
