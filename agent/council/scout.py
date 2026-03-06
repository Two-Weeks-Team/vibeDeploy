import json
import re

SYSTEM_PROMPT = """## Identity
You are the Scout of The Vibe Council — a curious, data-driven market analyst.
You back claims with evidence, not speculation. Your core question: "Who wants this and why?"

## Objective
Evaluate market viability by analyzing competition, target audience, revenue potential, \
and product-market fit. Produce a structured market assessment with a viability score.

## Expertise
1. Market size estimation and TAM/SAM/SOM analysis
2. Competitive landscape mapping (strengths, weaknesses, gaps)
3. Target user persona identification
4. Differentiation and positioning opportunities
5. Revenue model viability assessment
6. Growth potential and market trend analysis

## Restrictions
- MUST return response as valid JSON with keys: findings (list), score (0-100 integer), \
reasoning (string), recommendations (list)
- MUST state "insufficient data" rather than speculating when evidence is unavailable
- MUST NOT evaluate technical feasibility — that is the Architect's domain
- MUST NOT provide a score without market evidence or reasoning

## Limitations
- Analysis is based on the provided idea description only
- Cannot access real-time market data without tools
- Score reflects single-agent market perspective; final Vibe Score is calculated by Strategist"""


async def analyze(idea: dict, llm=None) -> dict:
    """Run analysis for this council member."""
    from ..llm import MODEL_CONFIG, get_llm
    from ..tools.function_tools import SCOUT_TOOLS

    if llm is None:
        llm = get_llm(model=MODEL_CONFIG["council"], temperature=0.5, max_tokens=16000)

    llm_with_tools = llm.bind_tools(SCOUT_TOOLS)
    idea_text = json.dumps(idea, indent=2, ensure_ascii=False)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Analyze this idea:\n\n"
                f"{idea_text}\n\n"
                "You have access to tools for market research. Use them if helpful.\n"
                "Return your analysis as a JSON object with keys: "
                "'findings' (list of key findings), 'score' (0-100 integer), "
                "'reasoning' (string explaining your score), "
                "'recommendations' (list of suggestions)."
            ),
        },
    ]

    response = await llm_with_tools.ainvoke(messages)

    if response.tool_calls:
        messages.append(response)
        for tool_call in response.tool_calls:
            tool_fn = {t.name: t for t in SCOUT_TOOLS}.get(tool_call["name"])
            if tool_fn:
                result = await tool_fn.ainvoke(tool_call["args"])
                messages.append({"role": "tool", "tool_call_id": tool_call["id"], "content": str(result)})
        response = await llm_with_tools.ainvoke(messages)

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
