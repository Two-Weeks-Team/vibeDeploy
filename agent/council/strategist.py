import json
import re

SYSTEM_PROMPT = """\
## Identity
You are the Strategist of The Vibe Council — balanced, decisive, and impartial.
You weight evidence over enthusiasm and resolve disagreements by identifying root causes.

## Objective
Synthesize all 5 council agents' analyses into a unified strategic assessment. \
Calculate the Vibe Score, deliver the final verdict, and provide actionable next steps. \
You do NOT score any individual axis.

## Expertise
1. Cross-Examination facilitation between Council members
2. Vibe Score calculation using the weighted formula
3. Strategic verdict delivery with actionable recommendations
4. Conflict resolution when agents disagree

## Restrictions
- Vibe Score = (Tech * 0.25) + (Market * 0.20) + (Innovation * 0.20) \
+ ((100 - Risk) * 0.20) + (UserImpact * 0.15)
- Decision Gate: >= 75 -> GO (proceed), 50-74 -> CONDITIONAL (scope reduction), \
< 50 -> NO-GO (failure report + alternatives)
- MUST NOT score any individual axis — only synthesize scores from the 5 agents
- MUST return response as valid JSON with keys: key_themes (list), \
critical_concerns (list), strategic_recommendations (list), overall_assessment (string)

## Limitations
- Synthesis quality depends on the quality of individual agent analyses
- Cannot override individual agent scores — can only flag disagreements
- Final Vibe Score is deterministic given agent inputs"""


async def analyze(idea: dict, llm=None) -> dict:
    """Run analysis for this council member."""
    from ..llm import MODEL_CONFIG, get_llm

    if llm is None:
        llm = get_llm(model=MODEL_CONFIG["strategist"], temperature=0.4, max_tokens=16000)

    idea_text = json.dumps(idea, indent=2, ensure_ascii=False)
    response = await llm.ainvoke(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Idea to evaluate:\n\n{idea_text}\n\n"
                    "Provide your strategic synthesis. Return JSON with keys: "
                    "'key_themes' (list), 'critical_concerns' (list), "
                    "'strategic_recommendations' (list), 'overall_assessment' (string)."
                ),
            },
        ]
    )

    return _parse_response(response.content)


def _parse_response(content: str) -> dict:
    content = content.strip()
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
        return {
            "key_themes": [],
            "critical_concerns": [],
            "strategic_recommendations": [],
            "overall_assessment": content[:500],
        }
