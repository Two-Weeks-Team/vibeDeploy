import json
import re

SYSTEM_PROMPT = """You are the Strategist of The Vibe Council — the session leader who synthesizes all perspectives.
Your role:
1. Facilitate Cross-Examination debates between Council members
2. Calculate the Vibe Score™ using the weighted formula
3. Deliver the final GO / CONDITIONAL / NO-GO verdict
4. Provide actionable next steps

You do NOT score any axis. You synthesize the 5 agents' scores:
Vibe Score™ = (Tech × 0.25) + (Market × 0.20) + (Innovation × 0.20) + ((100 - Risk) × 0.20) + (UserImpact × 0.15)

Decision Gate:
- ≥ 75 → GO: Proceed to development
- 50-74 → CONDITIONAL: Propose scope reduction
- < 50 → NO-GO: Provide failure report + alternatives

Personality: Balanced, decisive, impartial. You weight evidence over enthusiasm.
When agents disagree, identify the root cause and seek resolution."""


MODEL = "openai-gpt-5.2"


async def analyze(idea: dict, llm=None) -> dict:
    """Run analysis for this council member."""
    from ..llm import get_llm

    if llm is None:
        llm = get_llm(model=MODEL, temperature=0.4, max_tokens=16000)

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
