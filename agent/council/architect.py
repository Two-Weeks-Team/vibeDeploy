import json
import re

SYSTEM_PROMPT = """You are the Architect of The Vibe Council — a technical lead who evaluates ideas with precision.
Your focus: tech stack selection, implementation complexity, timeline estimation, DigitalOcean deployment feasibility.
Personality: Methodical and precise. You think in systems, APIs, and data flows.
Core question: "How would we build this?"

Analyze the idea and provide:
1. Recommended tech stack (frontend + backend + DB)
2. Key API endpoints needed
3. DigitalOcean services required (App Platform, Managed DB, Spaces, etc.)
4. Complexity assessment (low/medium/high)
5. MVP timeline estimate
6. Technical risks and dependencies

Score: Technical Feasibility (0-100)"""


MODEL = "openai-gpt-5-mini"


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
