import pytest

from agent.nodes.vibe_council import strategist_verdict


@pytest.mark.asyncio
async def test_strategist_verdict_relaxes_go_threshold_for_fallback_agents():
    result = await strategist_verdict(
        {
            "council_analysis": {
                "guardian": {"fallback": True},
                "architect": {"fallback": False},
            },
            "scoring": {
                "technical_feasibility": {"score": 68},
                "market_viability": {"score": 68},
                "innovation_score": {"score": 68},
                "risk_profile": {"score": 30},
                "user_impact": {"score": 68},
            },
        }
    )

    assert result["scoring"]["final_score"] == 68.4
    assert result["scoring"]["decision"] == "GO"
    assert result["scoring"]["go_threshold"] == 68
    assert result["scoring"]["fallback_agents"] == ["guardian"]


@pytest.mark.asyncio
async def test_strategist_verdict_keeps_default_go_threshold_without_fallbacks():
    result = await strategist_verdict(
        {
            "council_analysis": {
                "guardian": {"fallback": False},
                "architect": {"fallback": False},
            },
            "scoring": {
                "technical_feasibility": {"score": 68},
                "market_viability": {"score": 68},
                "innovation_score": {"score": 68},
                "risk_profile": {"score": 30},
                "user_impact": {"score": 68},
            },
        }
    )

    assert result["scoring"]["final_score"] == 68.4
    assert result["scoring"]["decision"] == "CONDITIONAL"
    assert result["scoring"]["go_threshold"] == 70
    assert result["scoring"]["fallback_agents"] == []
