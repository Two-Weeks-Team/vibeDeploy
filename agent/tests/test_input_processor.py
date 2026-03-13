import pytest

from agent.nodes import input_processor as input_processor_module
from agent.tools.youtube import extract_first_youtube_url


class _FakeResponse:
    def __init__(self, content: str):
        self.content = content


@pytest.mark.asyncio
async def test_input_processor_extracts_embedded_youtube_url(monkeypatch):
    captured = {}

    async def _fake_extract(url: str):
        captured["url"] = url
        return "Video transcript"

    async def _fake_invoke(_llm, messages, **kwargs):
        captured["messages"] = messages
        return _FakeResponse(
            '{"name":"TripCanvas AI","tagline":"Plan cinematic journeys","problem":"Travel planning is fragmented","solution":"One guided planner","target_users":"Travelers","key_features":["Planner"],"tech_hints":[],"monetization_hints":[],"visual_style_hints":[],"primary_user_flow":"User plans a trip","differentiation_hook":"Story-first planning","demo_story_hints":"Watch plans update live","must_have_surfaces":["hero"],"proof_points":["saved plans"],"experience_non_negotiables":["responsive UI"]}'
        )

    monkeypatch.setattr(input_processor_module, "extract_youtube_transcript", _fake_extract)
    monkeypatch.setattr(input_processor_module, "get_llm", lambda *args, **kwargs: object())
    monkeypatch.setattr(input_processor_module, "ainvoke_with_retry", _fake_invoke)

    result = await input_processor_module.input_processor(
        {
            "raw_input": (
                "Use this demo as inspiration: https://www.youtube.com/watch?v=NZWA8Y-gFGs\n\n"
                "Build a premium trip planner with a cinematic landing page."
            )
        }
    )

    assert result["input_type"] == "youtube"
    assert captured["url"] == "https://www.youtube.com/watch?v=NZWA8Y-gFGs"
    assert "Additional user instructions:" in captured["messages"][1]["content"]
    assert "premium trip planner" in captured["messages"][1]["content"]
    assert result["idea"]["name"] == "TripCanvas AI"


@pytest.mark.asyncio
async def test_input_processor_merges_flagship_contract(monkeypatch):
    async def _fake_invoke(_llm, _messages, **_kwargs):
        return _FakeResponse(
            '{"name":"RoutePostcard","tagline":"Plan weekends","problem":"Planning is messy","solution":"One guided planner","target_users":"Travelers","key_features":["Route planning"],"tech_hints":[],"monetization_hints":[],"visual_style_hints":[],"primary_user_flow":"User creates a route","differentiation_hook":"Travel-first artifact","demo_story_hints":"See a weekend board appear","must_have_surfaces":["destination brief"],"proof_points":["saved plans"],"experience_non_negotiables":["no KPI tiles"]}'
        )

    monkeypatch.setattr(input_processor_module, "get_llm", lambda *args, **kwargs: object())
    monkeypatch.setattr(input_processor_module, "ainvoke_with_retry", _fake_invoke)

    result = await input_processor_module.input_processor(
        {
            "raw_input": "Build a travel planner from this idea.",
            "selected_flagship": "weekender-route-postcards",
            "flagship_contract": {
                "slug": "weekender-route-postcards",
                "domain": "travel weekender planning",
                "visual_metaphor": "cinematic postcard route board",
                "forbidden_patterns": ["generic dashboard grid"],
                "required_objects": ["route card", "district stop"],
                "required_results": ["day-by-day route sequence"],
                "acceptance_checks": ["first fold already looks like a travel artifact"],
            },
        }
    )

    idea = result["idea"]
    assert result["selected_flagship"] == "weekender-route-postcards"
    assert idea["selected_flagship"] == "weekender-route-postcards"
    assert idea["domain"] == "travel weekender planning"
    assert "route card" in idea["reference_objects"]
    assert "day-by-day route sequence" in idea["proof_points"]
    assert "generic dashboard grid" in idea["experience_non_negotiables"]
    assert result["execution_tasks"]
    assert any(task["title"] == "route card" for task in result["execution_tasks"])
    assert result["task_distribution"]["total"] >= 3


def test_extract_first_youtube_url_finds_first_link_in_prompt():
    prompt = "Reference https://www.youtube.com/watch?v=NZWA8Y-gFGs and compare it with https://youtu.be/GqlyxP5mvQw"

    assert extract_first_youtube_url(prompt) == "https://www.youtube.com/watch?v=NZWA8Y-gFGs"


def test_normalize_idea_flattens_nested_feature_objects():
    idea = input_processor_module._normalize_idea(
        {
            "name": "RoutePostcard",
            "key_features": [
                {"name": "Route board", "description": "Build a day-by-day board"},
                {"label": "Backup lane", "detail": "Show rain alternatives"},
            ],
            "proof_points": [{"title": "Saved itineraries", "summary": "Snapshots persist after generation"}],
        }
    )

    assert idea["key_features"] == [
        "Route board - Build a day-by-day board",
        "Backup lane - Show rain alternatives",
    ]
    assert idea["proof_points"] == ["Saved itineraries - Snapshots persist after generation"]
