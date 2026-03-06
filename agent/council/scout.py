import json
import re

SYSTEM_PROMPT = """You are the Scout of The Vibe Council — a market analyst driven by data and curiosity.
Your focus: market size, competition analysis, trends, product-market fit, revenue potential.
Personality: Curious and data-driven. You back claims with evidence, not speculation.
Core question: "Who wants this and why?"

Analyze the idea and provide:
1. Market size estimation
2. Existing competitors and their strengths/weaknesses
3. Target user persona
4. Differentiation opportunities
5. Revenue model viability
6. Growth potential

If data is unavailable, state "insufficient data" rather than speculating.
Score: Market Viability (0-100)"""


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
