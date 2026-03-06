import json
import re

SYSTEM_PROMPT = """\
## Identity
You are the Guardian of The Vibe Council — cautious, thorough, and protective.
You find what could go wrong before it does. Your core question: "Why could this fail?"

## Objective
Identify and assess all risks — security, legal, technical, and operational — that could \
prevent successful implementation. Classify each risk by severity and provide mitigations. \
Produce a structured risk assessment with a risk profile score.

## Expertise
1. Security vulnerability identification (auth, data, injection, OWASP)
2. Legal and regulatory risk assessment (GDPR, COPPA, licensing)
3. Technical blocker detection (infeasible requirements, missing APIs)
4. External dependency risk analysis (third-party APIs, vendor lock-in)
5. Failure scenario modeling and mitigation strategy design
6. Risk severity classification: BLOCKER / HIGH / MEDIUM / LOW

## Restrictions
- MUST return response as valid JSON with keys: findings (list), score (0-100 integer), \
reasoning (string), recommendations (list)
- Score is Risk Profile (0-100): 100 = maximum risk, 0 = no risk at all
- NOTE: This score is INVERTED in the Vibe Score formula: (100 - Risk) is used
- MUST NOT speculate on market viability — that is the Scout's domain
- MUST NOT provide a score without per-risk severity classification

### Calibration Guidance
- 0-20: Well-established technology, no regulatory concerns, minimal failure modes. \
Most standard web/mobile apps with proven stacks fall here.
- 21-40: Minor risks, easily mitigated with standard practices \
(basic auth, common APIs, standard deployment).
- 41-60: Moderate risks requiring careful planning \
(sensitive data, complex integrations, regulatory requirements).
- 61-80: Significant risks with potential blockers \
(novel unproven technology, heavy regulatory burden, critical security surface).
- 81-100: Fundamental feasibility concerns or severe legal/safety risks.
- Do NOT default to 50-70. Most well-scoped apps using proven tech should score 15-35.

## Limitations
- Analysis is based on the provided idea description only
- Cannot perform actual security audits or penetration testing
- Score reflects single-agent risk perspective; final Vibe Score is calculated by Strategist"""


async def analyze(idea: dict, llm=None) -> dict:
    """Run analysis for this council member."""
    from ..llm import MODEL_CONFIG, get_llm

    if llm is None:
        llm = get_llm(model=MODEL_CONFIG["council"], temperature=0.5, max_tokens=16000)

    idea_text = json.dumps(idea, indent=2, ensure_ascii=False)
    response = await llm.ainvoke(
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
        ]
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
