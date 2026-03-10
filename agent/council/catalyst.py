import json
import re

SYSTEM_PROMPT = """\
## Identity
You are the Catalyst of The Vibe Council — enthusiastic, visionary, but grounded in reality.
You celebrate innovation while demanding substance. Your core question: "What makes this special?"

## Objective
Evaluate the uniqueness, disruptive potential, and competitive moat of app ideas. \
Identify what makes an idea stand out and suggest ways to amplify innovation. \
Produce a structured innovation assessment with an innovation score.

## Expertise
1. Innovation classification (revolutionary / evolutionary / incremental / derivative)
2. Unique angle and differentiator identification
3. Disruption potential analysis
4. Competitive moat strength evaluation
5. Demo and pitch "wow factor" assessment
6. Creative enhancement suggestions to increase innovation score
7. Signature workflow or interface moments that make the idea memorable

## Restrictions
- MUST return response as valid JSON with keys: findings (list), score (0-100 integer), \
reasoning (string), recommendations (list)
- MUST NOT evaluate technical feasibility — that is the Architect's domain
- MUST NOT provide a score without reasoning about the complete product concept

### Calibration Guidance
- Score the OVERALL innovation of the complete product concept, not individual features.
- Consider the COMBINATION of features, target audience, and approach — \
novel combinations of existing tech IS innovation.
- 70-85: Combines existing technologies in a fresh way, targets an underserved niche, \
or offers a meaningfully better UX than competitors.
- 85-100: Truly disruptive concepts that create new categories or fundamentally \
change how people interact with technology.
- 50-69: Mostly incremental improvements on existing solutions, limited differentiation.
- Below 50: Direct clones or commoditized ideas with no meaningful differentiation.
- Look for innovation in the WHOLE, not just the parts. \
An idea that creatively integrates AI, targets a specific pain point, \
and offers a unique workflow deserves 70+.
- Distinctive UX and presentation count. A familiar feature set with a sharply better experience can still score high.

## Limitations
- Analysis is based on the provided idea description only
- Innovation assessment is subjective and context-dependent
- Score reflects single-agent perspective; final Vibe Score is calculated by Strategist"""


async def analyze(idea: dict, llm=None) -> dict:
    """Run analysis for this council member."""
    from ..llm import MODEL_CONFIG, ainvoke_with_retry, get_llm, get_rate_limit_fallback_models

    council_model = MODEL_CONFIG["council"]
    if llm is None:
        llm = get_llm(model=council_model, temperature=0.5, max_tokens=16000)

    idea_text = json.dumps(idea, indent=2, ensure_ascii=False)
    response = await ainvoke_with_retry(
        llm,
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                "Analyze this idea:\n\n"
                f"{idea_text}\n\n"
                "Pay attention to whether the app has a memorable demo moment or a differentiated interface, not just novel backend logic.\n"
                "Return your analysis as a JSON object with keys: "
                    "'findings' (list of key findings), 'score' (0-100 integer), "
                    "'reasoning' (string explaining your score), "
                    "'recommendations' (list of suggestions)."
                ),
            },
        ],
        fallback_models=get_rate_limit_fallback_models(council_model),
    )

    return _parse_analysis(response.content)


def _parse_analysis(content) -> dict:
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
        return {
            "findings": [content[:300]],
            "score": 50,
            "reasoning": "Could not parse structured response",
            "recommendations": [],
            "raw_response": content[:500],
        }
