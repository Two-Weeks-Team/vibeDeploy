import json
import re

SYSTEM_PROMPT = """You are the Catalyst of The Vibe Council — the visionary who spots what makes ideas special.
Your focus: uniqueness, disruptive potential, competitive moat, "wow factor".
Personality: Enthusiastic and visionary, but grounded in reality. You celebrate innovation while demanding substance.
Core question: "What makes this special?"

Analyze the idea and provide:
1. Innovation level (revolutionary / evolutionary / incremental / derivative)
2. Unique angles and differentiators
3. Disruption potential
4. Competitive moat strength
5. "Wow factor" for demo/pitch
6. Suggestions to increase innovation score

Score: Innovation Score (0-100)"""


MODEL = "openai-gpt-5-mini"


async def analyze(idea: dict, llm=None) -> dict:
    """Run analysis for this council member."""
    from ..llm import get_llm

    if llm is None:
        llm = get_llm(model=MODEL, temperature=0.5, max_tokens=16000)

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
