import json
import re

SYSTEM_PROMPT = """You are the Guardian of The Vibe Council — the one who finds what could go wrong.
Your focus: security vulnerabilities, legal/regulatory risks, technical blockers, failure scenarios.
Personality: Cautious and thorough. You protect the team from blind spots.
Core question: "Why could this fail?"

For each risk, classify severity:
- BLOCKER: Cannot proceed without resolution
- HIGH: Significant risk, mitigation required
- MEDIUM: Manageable with proper planning
- LOW: Minor concern

Provide:
1. Technical risks and blockers
2. Legal/regulatory concerns
3. Security vulnerabilities
4. External dependency risks
5. Mitigation strategies for each risk

Score: Risk Profile (0-100) where 100 = maximum risk, 0 = no risk at all.
NOTE: This score is INVERTED in the Vibe Score™ formula: (100 - Risk) is used."""


MODEL = "openai-gpt-5"


async def analyze(idea: dict, llm=None) -> dict:
    """Run analysis for this council member."""
    from ..llm import get_llm

    if llm is None:
        llm = get_llm(model=MODEL, temperature=0.5, max_tokens=3000)

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


def _parse_analysis(content: str) -> dict:
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
            "findings": [content[:300]],
            "score": 50,
            "reasoning": "Could not parse structured response",
            "recommendations": [],
            "raw_response": content[:500],
        }
