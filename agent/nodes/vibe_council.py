from langgraph.graph import Send

from ..state import VibeDeployState

COUNCIL_MEMBERS = ["architect", "scout", "guardian", "catalyst", "advocate"]


def fan_out_analysis(state: VibeDeployState) -> list[Send]:
    return [
        Send(
            "run_council_agent",
            {
                "agent_name": name,
                "idea": state.get("idea", {}),
                "idea_summary": state.get("idea_summary", ""),
            },
        )
        for name in COUNCIL_MEMBERS
    ]


async def run_council_agent(input: dict) -> dict:
    return {
        "agent_name": input.get("agent_name", "unknown"),
        "analysis": {
            "findings": [],
            "score": 0,
            "reasoning": "stub",
        },
    }


async def cross_examination(state: VibeDeployState) -> dict:
    _ = state
    return {
        "cross_examination": {
            "architect_vs_guardian": {},
            "scout_vs_catalyst": {},
            "advocate_challenges": {},
            "score_adjustments": {},
        },
        "phase": "cross_examination_complete",
    }


def fan_out_scoring(state: VibeDeployState) -> list[Send]:
    return [
        Send(
            "score_axis",
            {
                "agent_name": name,
                "idea": state.get("idea", {}),
                "analysis": state.get("council_analysis", {}).get(name, {}),
                "cross_examination": state.get("cross_examination", {}),
            },
        )
        for name in COUNCIL_MEMBERS
    ]


async def score_axis(input: dict) -> dict:
    return {
        "agent_name": input.get("agent_name", "unknown"),
        "score": {
            "score": 0,
            "reasoning": "stub",
            "key_findings": [],
        },
    }


async def strategist_verdict(state: VibeDeployState) -> dict:
    existing = state.get("scoring") or {}
    scoring = {
        "technical_feasibility": existing.get(
            "technical_feasibility",
            {"score": 0, "reasoning": "stub", "key_findings": []},
        ),
        "market_viability": existing.get(
            "market_viability", {"score": 0, "reasoning": "stub", "key_findings": []}
        ),
        "innovation_score": existing.get(
            "innovation_score", {"score": 0, "reasoning": "stub", "key_findings": []}
        ),
        "risk_profile": existing.get(
            "risk_profile", {"score": 100, "reasoning": "stub", "key_findings": []}
        ),
        "user_impact": existing.get(
            "user_impact", {"score": 0, "reasoning": "stub", "key_findings": []}
        ),
        "final_score": float(existing.get("final_score", 0.0)),
        "decision": existing.get("decision", "NO_GO"),
    }
    return {
        "scoring": scoring,
        "phase": "verdict_delivered",
    }
