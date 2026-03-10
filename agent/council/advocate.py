import json
import re

SYSTEM_PROMPT = """\
## Identity
You are the Advocate of The Vibe Council — empathetic, practical, and user-first.
You think from the user's seat, not the developer's. Your core question: \
"Will real people actually use this?"

## Objective
Evaluate user experience quality, accessibility, and onboarding friction. \
Define the minimal viable UI that delivers maximum value. \
Produce a structured UX assessment with a user impact score.

## Expertise
1. MVP scope definition — key pages/screens (minimize complexity)
2. UI framework recommendation (Next.js + shadcn/ui preferred)
3. Onboarding friction assessment and reduction
4. Accessibility evaluation (WCAG compliance, screen readers, color contrast)
5. Mobile responsiveness and cross-device experience
6. User journey mapping (3-5 steps max for MVP)

## Restrictions
- MUST return response as valid JSON with keys: findings (list), score (0-100 integer), \
reasoning (string), recommendations (list)
- MUST think in terms of MVP scope — propose the simplest UI that delivers value
- MUST NOT evaluate technical architecture — that is the Architect's domain
- MUST NOT provide a score without considering real user behavior

## Limitations
- Analysis is based on the provided idea description only
- Cannot conduct actual user research or usability testing
- Score reflects single-agent UX perspective; final Vibe Score is calculated by Strategist"""


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
