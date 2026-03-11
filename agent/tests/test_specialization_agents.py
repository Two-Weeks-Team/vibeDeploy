import pytest

from agent.nodes.experience_agent import experience_agent
from agent.nodes.inspiration_agent import inspiration_agent


@pytest.mark.asyncio
async def test_inspiration_agent_fallback_maps_travel_idea_without_llm(monkeypatch):
    async def _fail(*args, **kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr("agent.nodes.inspiration_agent.ainvoke_with_retry", _fail)
    monkeypatch.setattr("agent.nodes.inspiration_agent.get_llm", lambda **kwargs: object())

    result = await inspiration_agent(
        {
            "raw_input": "Use this YouTube as inspiration and build a cinematic Seoul trip planner.",
            "idea": {
                "name": "TripCanvas AI",
                "tagline": "Plan cinematic journeys",
                "problem": "Travel planning is fragmented",
            },
            "transcript": "A travel creator walks through neighborhood cafes, night views, and day-by-day route planning.",
        }
    )

    assert result["phase"] == "inspiration_mapped"
    assert result["inspiration_pack"]["layout_archetype"] == "storyboard"
    assert result["idea"]["domain"] == "travel"
    assert "postcard route studio" in result["idea"]["interface_metaphor"]
    assert "editorial travel spreads" in result["idea"]["visual_style_hints"]


@pytest.mark.asyncio
async def test_experience_agent_fallback_builds_domain_specific_contract(monkeypatch):
    async def _fail(*args, **kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr("agent.nodes.experience_agent.ainvoke_with_retry", _fail)
    monkeypatch.setattr("agent.nodes.experience_agent.get_llm", lambda **kwargs: object())

    result = await experience_agent(
        {
            "idea": {
                "name": "BudgetAtlas AI",
                "domain": "finance",
                "layout_archetype": "atlas",
                "interface_metaphor": "money runway atlas",
            },
            "inspiration_pack": {
                "domain": "finance",
                "layout_archetype": "atlas",
            },
        }
    )

    assert result["phase"] == "experience_specialized"
    assert "money runway summary" in result["experience_spec"]["must_have_surfaces"]
    assert result["idea"]["primary_action_label"] == "Shape money plan"
    assert "runway" in " ".join(result["idea"]["output_entities"]).lower()
    assert "avoid spreadsheet skin" in result["idea"]["experience_non_negotiables"]
