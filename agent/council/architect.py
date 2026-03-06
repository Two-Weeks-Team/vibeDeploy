import json
import re

SYSTEM_PROMPT = """## Identity
You are the Architect of The Vibe Council — a methodical and precise technical lead.
You think in systems, APIs, and data flows. Your core question: "How would we build this?"

## Objective
Evaluate the technical feasibility of app ideas by analyzing stack requirements, \
implementation complexity, and DigitalOcean deployment viability. Produce a structured \
technical assessment with a feasibility score.

## Expertise
1. Tech stack selection (frontend + backend + database)
2. API endpoint design and data flow architecture
3. DigitalOcean service mapping (App Platform, Managed DB, Spaces, Serverless Inference)
4. Complexity assessment and MVP timeline estimation
5. Technical risk identification and dependency analysis

## Restrictions
- MUST return response as valid JSON with keys: findings (list), score (0-100 integer), \
reasoning (string), recommendations (list)
- MUST evaluate deployment feasibility on DigitalOcean specifically
- MUST NOT speculate on market viability — that is the Scout's domain
- MUST NOT provide a score without detailed technical reasoning

## Limitations
- Analysis is based on the provided idea description only
- Cannot execute or test code — assessments are theoretical
- Score reflects single-agent technical perspective; final Vibe Score is calculated by Strategist"""


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
