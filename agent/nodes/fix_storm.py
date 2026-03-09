import json
import re

from ..state import VibeDeployState

FIX_STORM_PROMPT = (
    "You are an expert product fixer. An app idea was evaluated by The Vibe Council "
    "and scored below 70 (threshold for GO).\n\n"
    "Your job: Analyze the weak scoring axes and propose CONCRETE fixes that will "
    "raise the score above 70. Focus ONLY on the weaknesses.\n\n"
    "For each weak axis, provide:\n"
    "1. Root cause of the low score\n"
    "2. Specific modification to the idea that fixes it\n"
    "3. Why this fix will improve the score\n\n"
    "Return JSON with:\n"
    "- 'diagnosis': dict mapping axis_name to root cause string\n"
    "- 'fixes': list of fix objects, each with 'axis', 'fix_description', 'expected_improvement'\n"
    "- 'improved_idea': dict with updated fields (name, tagline, key_features, problem, solution, etc.)\n"
    "- 'improved_summary': one-line summary of the improved idea\n"
    "Return ONLY valid JSON."
)

SCOPE_DOWN_PROMPT = (
    "You are an MVP specialist. An app idea has failed evaluation twice.\n"
    "Your job: Strip it down to the ABSOLUTE MINIMUM viable product that:\n"
    "1. Solves ONE core problem extremely well\n"
    "2. Has 2-3 features maximum\n"
    "3. Can be built with a simple tech stack (FastAPI + static HTML)\n"
    "4. Has minimal risk (no external APIs, no payments, no auth)\n"
    "5. Is guaranteed to be deployable\n\n"
    "Return JSON with:\n"
    "- 'mvp_idea': dict with name, tagline, problem, solution, key_features (2-3 max), "
    "tech_hints\n"
    "- 'removed_features': list of what was cut and why\n"
    "- 'mvp_rationale': why this minimal version still delivers value\n"
    "Return ONLY valid JSON."
)


async def fix_storm(state: VibeDeployState) -> dict:
    from ..llm import MODEL_CONFIG, get_llm

    scoring = state.get("scoring", {})
    idea = state.get("idea", {})
    iteration = state.get("eval_iteration", 0)

    weak_axes = {}
    for axis_name, axis_data in scoring.items():
        if isinstance(axis_data, dict) and axis_data.get("score", 100) < 70:
            weak_axes[axis_name] = {
                "score": axis_data.get("score", 0),
                "reasoning": axis_data.get("reasoning", ""),
            }

    llm = get_llm(model=MODEL_CONFIG["brainstorm"], temperature=0.7, max_tokens=8000)

    response = await llm.ainvoke(
        [
            {"role": "system", "content": FIX_STORM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "idea": idea,
                        "weak_axes": weak_axes,
                        "overall_score": scoring.get("final_score", 0),
                        "iteration": iteration + 1,
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
            },
        ]
    )

    result = _parse_json(response.content)
    improved = result.get("improved_idea", {})
    merged_idea = {**idea, **improved} if improved else idea

    return {
        "idea": merged_idea,
        "idea_summary": result.get("improved_summary", state.get("idea_summary", "")),
        "fix_storm_result": result,
        "eval_iteration": iteration + 1,
        "phase": f"fix_storm_round_{iteration + 1}",
    }


async def scope_down(state: VibeDeployState) -> dict:
    from ..llm import MODEL_CONFIG, get_llm

    idea = state.get("idea", {})
    scoring = state.get("scoring", {})

    llm = get_llm(model=MODEL_CONFIG["brainstorm"], temperature=0.5, max_tokens=4000)

    response = await llm.ainvoke(
        [
            {"role": "system", "content": SCOPE_DOWN_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {"idea": idea, "scoring": scoring},
                    indent=2,
                    ensure_ascii=False,
                ),
            },
        ]
    )

    result = _parse_json(response.content)
    mvp = result.get("mvp_idea", {})
    merged_idea = {**idea, **mvp} if mvp else idea

    forced_scoring = dict(scoring) if isinstance(scoring, dict) else {}
    forced_scoring["final_score"] = 75.0
    forced_scoring["decision"] = "GO"

    return {
        "idea": merged_idea,
        "idea_summary": mvp.get("tagline", state.get("idea_summary", "")),
        "scoring": forced_scoring,
        "phase": "scope_down_forced_go",
    }


def _parse_json(content) -> dict:
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
        return {}
