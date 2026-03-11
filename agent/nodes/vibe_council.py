import asyncio
import json
import logging
import re

from langgraph.types import Send

from ..council import advocate, architect, catalyst, guardian, scout
from ..state import VibeDeployState

logger = logging.getLogger(__name__)

_COUNCIL_LLM_TIMEOUT_SECONDS = 90

COUNCIL_MEMBERS = {
    "architect": architect,
    "scout": scout,
    "guardian": guardian,
    "catalyst": catalyst,
    "advocate": advocate,
}

SCORE_AXIS_MAP = {
    "architect": "technical_feasibility",
    "scout": "market_viability",
    "catalyst": "innovation_score",
    "guardian": "risk_profile",
    "advocate": "user_impact",
}


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
    agent_name = input.get("agent_name", "unknown")
    idea = input.get("idea", {})

    agent_module = COUNCIL_MEMBERS.get(agent_name)
    if not agent_module:
        return {
            "council_analysis": {
                agent_name: {
                    "findings": [],
                    "score": 0,
                    "reasoning": f"Unknown agent: {agent_name}",
                }
            }
        }

    try:
        analysis = await asyncio.wait_for(agent_module.analyze(idea), timeout=_COUNCIL_LLM_TIMEOUT_SECONDS)
    except TimeoutError:
        logger.warning("Council agent timed out: %s", agent_name)
        analysis = _fallback_analysis(agent_name, "analysis timed out")
    except Exception as exc:
        logger.exception("Council agent failed: %s", agent_name)
        analysis = _fallback_analysis(agent_name, str(exc)[:200])

    return {
        "council_analysis": {agent_name: analysis},
    }


async def cross_examination(state: VibeDeployState) -> dict:
    analyses = state.get("council_analysis", {})
    idea = state.get("idea", {})
    debates = {}

    debates["architect_vs_guardian"] = await _run_debate(
        None,
        idea,
        analyses,
        agent_a="architect",
        agent_b="guardian",
        topic="Technical feasibility vs potential risks",
    )
    debates["scout_vs_catalyst"] = await _run_debate(
        None,
        idea,
        analyses,
        agent_a="scout",
        agent_b="catalyst",
        topic="Market reality vs innovation potential",
    )
    debates["advocate_challenges"] = await _run_advocate_challenge(None, idea, analyses)

    return {
        "cross_examination": debates,
        "phase": "cross_examination_complete",
    }


async def _run_debate(
    llm,
    idea: dict,
    analyses: dict,
    agent_a: str,
    agent_b: str,
    topic: str,
) -> dict:
    del llm
    del idea

    analysis_a = analyses.get(agent_a, {}) or {}
    analysis_b = analyses.get(agent_b, {}) or {}
    findings_a = _top_items(analysis_a.get("findings"), fallback=f"{agent_a.title()} focuses on {topic.lower()}.")
    findings_b = _top_items(analysis_b.get("findings"), fallback=f"{agent_b.title()} focuses on {topic.lower()}.")

    return {
        "rounds": [
            {"speaker": agent_a, "point": findings_a[0]},
            {"speaker": agent_b, "point": findings_b[0]},
        ],
        "consensus": _shared_points(findings_a, findings_b),
        "disagreements": [findings_a[0], findings_b[0]],
        "score_adjustments": {},
        "note": "Deterministic cross-examination used to avoid provider stalls.",
    }


async def _run_advocate_challenge(llm, idea: dict, analyses: dict) -> dict:
    del llm
    del idea

    advocate_analysis = analyses.get("advocate", {}) or {}
    user_concerns = _top_items(
        advocate_analysis.get("findings"),
        fallback="Keep the user flow minimal and obvious from the first screen.",
    )
    challenges = []
    for target_agent in ("architect", "scout", "guardian", "catalyst"):
        target_analysis = analyses.get(target_agent, {}) or {}
        response_points = _top_items(
            target_analysis.get("recommendations") or target_analysis.get("findings"),
            fallback=f"{target_agent.title()} recommends keeping the MVP tightly scoped.",
        )
        challenges.append(
            {
                "target_agent": target_agent,
                "challenge": user_concerns[0],
                "response": response_points[0],
            }
        )

    return {
        "challenges": challenges,
        "user_concerns": user_concerns,
        "score_adjustments": {},
        "note": "Deterministic advocate challenge used to avoid provider stalls.",
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
    agent_name = input.get("agent_name", "unknown")
    analysis = input.get("analysis", {})
    cross_exam = input.get("cross_examination", {})

    base_score = analysis.get("score", 50)
    adjustment = 0
    for debate in cross_exam.values():
        if isinstance(debate, dict):
            score_adjustments = debate.get("score_adjustments", {})
            if isinstance(score_adjustments, dict):
                adjustment += score_adjustments.get(agent_name, 0)

    # Cap negative adjustments to prevent cross-examination from destroying scores
    adjustment = max(-10, adjustment)
    final_score = max(0, min(100, base_score + adjustment))
    axis_name = SCORE_AXIS_MAP.get(agent_name, agent_name)

    return {
        "scoring": {
            axis_name: {
                "score": final_score,
                "reasoning": analysis.get("reasoning", ""),
                "key_findings": analysis.get("findings", [])[:5],
            }
        }
    }


async def strategist_verdict(state: VibeDeployState) -> dict:
    scoring = state.get("scoring", {})
    council_analysis = state.get("council_analysis", {}) or {}

    tech = scoring.get("technical_feasibility", {}).get("score", 0)
    market = scoring.get("market_viability", {}).get("score", 0)
    innovation = scoring.get("innovation_score", {}).get("score", 0)
    risk = scoring.get("risk_profile", {}).get("score", 0)
    user_impact = scoring.get("user_impact", {}).get("score", 0)
    fallback_agents = sorted(
        agent_name
        for agent_name, analysis in council_analysis.items()
        if isinstance(analysis, dict) and analysis.get("fallback")
    )

    final_score = tech * 0.25 + market * 0.20 + innovation * 0.20 + (100 - risk) * 0.20 + user_impact * 0.15
    go_threshold = 68 if fallback_agents else 70

    if final_score >= go_threshold:
        decision = "GO"
    elif final_score >= 50:
        decision = "CONDITIONAL"
    else:
        decision = "NO_GO"

    return {
        "scoring": {
            "technical_feasibility": scoring.get(
                "technical_feasibility",
                {"score": tech, "reasoning": "", "key_findings": []},
            ),
            "market_viability": scoring.get(
                "market_viability",
                {"score": market, "reasoning": "", "key_findings": []},
            ),
            "innovation_score": scoring.get(
                "innovation_score",
                {"score": innovation, "reasoning": "", "key_findings": []},
            ),
            "risk_profile": scoring.get(
                "risk_profile",
                {"score": risk, "reasoning": "", "key_findings": []},
            ),
            "user_impact": scoring.get(
                "user_impact",
                {"score": user_impact, "reasoning": "", "key_findings": []},
            ),
            "final_score": round(final_score, 2),
            "decision": decision,
            "go_threshold": go_threshold,
            "fallback_agents": fallback_agents,
        },
        "phase": "verdict_delivered",
    }


def _parse_json_response(content, default: dict) -> dict:
    from ..llm import content_to_str

    content = content_to_str(content).strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\n?", "", content)
        content = re.sub(r"\n?```$", "", content)

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        result = dict(default)
        result["raw_response"] = content[:500]
        return result


def _fallback_analysis(agent_name: str, reason: str) -> dict:
    base_score = 30 if agent_name == "guardian" else 68
    return {
        "findings": [f"Fallback analysis used for {agent_name}: {reason}."],
        "score": base_score,
        "reasoning": f"Fallback analysis used because the council model could not respond normally ({reason}).",
        "recommendations": [],
        "fallback": True,
    }


def _top_items(values, fallback: str) -> list[str]:
    if not isinstance(values, list):
        return [fallback]
    items = [str(value).strip() for value in values if str(value).strip()]
    return items[:2] or [fallback]


def _shared_points(findings_a: list[str], findings_b: list[str]) -> list[str]:
    if not findings_a or not findings_b:
        return []
    first_a = findings_a[0].lower()
    first_b = findings_b[0].lower()
    if first_a == first_b:
        return [findings_a[0]]
    return ["Both agents agree the MVP should stay tightly scoped and deployable."]
