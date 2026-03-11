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


def test_extract_first_youtube_url_finds_first_link_in_prompt():
    prompt = (
        "Reference https://www.youtube.com/watch?v=NZWA8Y-gFGs and compare it with "
        "https://youtu.be/GqlyxP5mvQw"
    )

    assert extract_first_youtube_url(prompt) == "https://www.youtube.com/watch?v=NZWA8Y-gFGs"
