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
    from ..llm import MODEL_CONFIG, get_llm

    analyses = state.get("council_analysis", {})
    idea = state.get("idea", {})

    llm = get_llm(model=MODEL_CONFIG["cross_exam"], temperature=0.6, max_tokens=16000)
    debates = {}

    debates["architect_vs_guardian"] = await _run_debate(
        llm,
        idea,
        analyses,
        agent_a="architect",
        agent_b="guardian",
        topic="Technical feasibility vs potential risks",
    )
    debates["scout_vs_catalyst"] = await _run_debate(
        llm,
        idea,
        analyses,
        agent_a="scout",
        agent_b="catalyst",
        topic="Market reality vs innovation potential",
    )
    debates["advocate_challenges"] = await _run_advocate_challenge(llm, idea, analyses)

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
    analysis_a = json.dumps(analyses.get(agent_a, {}), indent=2, ensure_ascii=False)
    analysis_b = json.dumps(analyses.get(agent_b, {}), indent=2, ensure_ascii=False)
    prompt = (
        f"You are moderating a debate about: {topic}\n\n"
        f"Idea: {json.dumps(idea, ensure_ascii=False)}\n\n"
        f"{agent_a.title()}'s analysis:\n{analysis_a}\n\n"
        f"{agent_b.title()}'s analysis:\n{analysis_b}\n\n"
        "Generate a structured debate with 2 rounds of exchange. "
        "Each agent should challenge the other's findings and defend their position. "
        "Return JSON with keys: 'rounds' (list of exchanges), 'consensus' (areas of agreement), "
        "'disagreements' (unresolved points), 'score_adjustments' (dict mapping agent names to "
        "integer adjustments, e.g. {'architect': -5, 'guardian': +3})."
    )

    default = {
        "rounds": [],
        "consensus": [],
        "disagreements": [],
        "score_adjustments": {},
    }

    try:
        response = await asyncio.wait_for(
            llm.ainvoke(
                [
                    {
                        "role": "system",
                        "content": "You simulate structured debates between AI council members. Return valid JSON only.",
                    },
                    {"role": "user", "content": prompt},
                ]
            ),
            timeout=_COUNCIL_LLM_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        logger.warning("Cross-examination debate timed out: %s vs %s", agent_a, agent_b)
        return {**default, "note": f"{agent_a}_vs_{agent_b} debate timed out"}
    except Exception as exc:
        logger.exception("Cross-examination debate failed: %s vs %s", agent_a, agent_b)
        return {**default, "note": str(exc)[:200]}

    return _parse_json_response(response.content, default)


async def _run_advocate_challenge(llm, idea: dict, analyses: dict) -> dict:
    all_analyses = json.dumps(analyses, indent=2, ensure_ascii=False)
    prompt = (
        "You are the Advocate (UX Champion) challenging all other council members.\n\n"
        f"Idea: {json.dumps(idea, ensure_ascii=False)}\n\n"
        f"All analyses:\n{all_analyses}\n\n"
        "Challenge each agent's findings from the user's perspective. "
        "Ask: Will real users actually benefit? Is the proposed tech stack user-friendly? "
        "Are the risks relevant to end-users? "
        "Return JSON with keys: 'challenges' (list of challenge objects with 'target_agent' and "
        "'challenge' and 'response'), 'user_concerns' (list), 'score_adjustments' "
        "(dict of agent name to int adjustment)."
    )

    default = {
        "challenges": [],
        "user_concerns": [],
        "score_adjustments": {},
    }

    try:
        response = await asyncio.wait_for(
            llm.ainvoke(
                [
                    {
                        "role": "system",
                        "content": "You are the Advocate, the voice of end users. Return valid JSON only.",
                    },
                    {"role": "user", "content": prompt},
                ]
            ),
            timeout=_COUNCIL_LLM_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        logger.warning("Advocate challenge timed out")
        return {**default, "note": "advocate challenge timed out"}
    except Exception as exc:
        logger.exception("Advocate challenge failed")
        return {**default, "note": str(exc)[:200]}

    return _parse_json_response(response.content, default)


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

    tech = scoring.get("technical_feasibility", {}).get("score", 0)
    market = scoring.get("market_viability", {}).get("score", 0)
    innovation = scoring.get("innovation_score", {}).get("score", 0)
    risk = scoring.get("risk_profile", {}).get("score", 0)
    user_impact = scoring.get("user_impact", {}).get("score", 0)

    final_score = tech * 0.25 + market * 0.20 + innovation * 0.20 + (100 - risk) * 0.20 + user_impact * 0.15

    if final_score >= 70:
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
