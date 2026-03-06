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


async def analyze(idea: dict, llm=None) -> dict:
    """Run analysis for this council member."""
    from ..llm import MODEL_CONFIG, get_llm
    from ..tools.function_tools import ARCHITECT_TOOLS

    if llm is None:
        llm = get_llm(model=MODEL_CONFIG["council"], temperature=0.5, max_tokens=16000)

    llm_with_tools = llm.bind_tools(ARCHITECT_TOOLS)
    idea_text = json.dumps(idea, indent=2, ensure_ascii=False)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Analyze this idea:\n\n"
                f"{idea_text}\n\n"
                "You have access to tools for tech research and DO docs. Use them if helpful.\n"
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
            tool_fn = {t.name: t for t in ARCHITECT_TOOLS}.get(tool_call["name"])
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
