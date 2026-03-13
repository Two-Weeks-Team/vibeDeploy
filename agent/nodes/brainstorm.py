"""Brainstorm mode — creative ideation without evaluation.

Each council agent brainstorms from their perspective, generating
creative insights, opportunities, and possibilities rather than
scoring or judging the idea.
"""

import json
import os
import re

from langgraph.types import Send

BRAINSTORM_PROMPTS = {
    "architect": (
        "You are the Architect — a creative technical visionary.\n\n"
        "Given this app idea, brainstorm freely:\n"
        "- 3 innovative tech stack combinations that could make this shine\n"
        "- 2 unconventional architecture approaches (edge computing, serverless, event-driven, etc.)\n"
        "- 1 moonshot technical feature that would wow users\n"
        "- 1 frontend system choice that would make the product feel premium without hurting build reliability\n"
        "- Key technical enablers that exist today but most people don't know about\n\n"
        "Focus on POSSIBILITIES, not limitations. Be creative and specific."
    ),
    "scout": (
        "You are the Scout — a market opportunity hunter.\n\n"
        "Given this app idea, brainstorm freely:\n"
        "- 3 untapped market segments this could serve\n"
        "- 2 creative monetization models beyond the obvious\n"
        "- 1 strategic partnership opportunity that could accelerate growth\n"
        "- Emerging market trends this idea could ride\n\n"
        "Think like a VC looking for hidden gems. Be specific with numbers and segments."
    ),
    "catalyst": (
        "You are the Catalyst — an innovation provocateur.\n\n"
        "Given this app idea, brainstorm freely:\n"
        "- 3 ways to make this 10x more disruptive\n"
        "- 2 adjacent problems this solution could also solve\n"
        "- 1 'what if' scenario that would redefine the category\n"
        "- 1 signature product moment or interface behavior that would be unforgettable in a demo\n"
        "- Analogies from other industries that could inspire breakthrough features\n\n"
        "Think bold, unconventional, boundary-pushing. No idea is too wild."
    ),
    "guardian": (
        "You are the Guardian — a strategic risk advisor turned opportunity finder.\n\n"
        "Given this app idea, brainstorm freely:\n"
        "- 3 preemptive strategies that turn potential risks into competitive advantages\n"
        "- 2 compliance/legal angles that could become moats\n"
        "- 1 'anti-fragile' design that gets stronger under pressure\n"
        "- Trust-building features that users would love\n\n"
        "Frame every risk as a hidden opportunity. Be constructive, not cautionary."
    ),
    "advocate": (
        "You are the Advocate — a user experience visionary.\n\n"
        "Given this app idea, brainstorm freely:\n"
        "- 3 delightful UX micro-interactions that would make users smile\n"
        "- 2 accessibility features that expand the addressable market\n"
        "- 1 viral loop mechanism built into the core experience\n"
        "- 1 concrete visual direction that feels current and specific to the domain\n"
        "- 'Day in the life' scenario showing how this transforms a user's workflow\n\n"
        "Think from the user's heart, not just their hands. Make it human."
    ),
}


def _serialize_brainstorm_fanout() -> bool:
    return os.getenv("VIBEDEPLOY_SERIALIZE_AGENT_FANOUT", "").strip().lower() in {"1", "true", "yes", "on"}


def fan_out_brainstorm(state: dict) -> list[Send]:
    if _serialize_brainstorm_fanout():
        return [
            Send(
                "run_brainstorm_agent",
                {
                    "serial_run": True,
                    "agent_names": list(BRAINSTORM_PROMPTS),
                    "idea": state.get("idea", {}),
                    "idea_summary": state.get("idea_summary", ""),
                },
            )
        ]
    return [
        Send(
            "run_brainstorm_agent",
            {
                "agent_name": name,
                "idea": state.get("idea", {}),
                "idea_summary": state.get("idea_summary", ""),
            },
        )
        for name in BRAINSTORM_PROMPTS
    ]


async def run_brainstorm_agent(input: dict) -> dict:
    from ..llm import MODEL_CONFIG, ainvoke_with_retry, get_llm, get_rate_limit_fallback_models

    if input.get("serial_run"):
        merged: dict[str, dict] = {}
        for agent_name in input.get("agent_names", list(BRAINSTORM_PROMPTS)):
            result = await run_brainstorm_agent(
                {
                    "agent_name": agent_name,
                    "idea": input.get("idea", {}),
                    "idea_summary": input.get("idea_summary", ""),
                }
            )
            merged.update(result.get("brainstorm_insights", {}) or {})
        return {"brainstorm_insights": merged}

    agent_name = input.get("agent_name", "unknown")
    idea = input.get("idea", {})

    prompt = BRAINSTORM_PROMPTS.get(agent_name)
    if not prompt:
        return {"brainstorm_insights": {agent_name: {"ideas": [], "raw": f"Unknown agent: {agent_name}"}}}

    brainstorm_model = MODEL_CONFIG["brainstorm"]
    llm = get_llm(model=brainstorm_model, temperature=0.8, max_tokens=16000)
    idea_text = json.dumps(idea, indent=2, ensure_ascii=False)

    response = await ainvoke_with_retry(
        llm,
        [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": (
                    f"Brainstorm about this idea:\n\n{idea_text}\n\n"
                    "Return your brainstorming as a JSON object with keys:\n"
                    "- 'ideas' (list of creative ideas, each with 'title' and 'description')\n"
                    "- 'opportunities' (list of opportunity strings)\n"
                    "- 'wild_card' (one unexpected insight or connection)\n"
                    "- 'action_items' (list of concrete next steps)\n"
                    "Return ONLY valid JSON."
                ),
            },
        ],
        fallback_models=get_rate_limit_fallback_models(brainstorm_model),
    )

    return {
        "brainstorm_insights": {agent_name: _parse_brainstorm(response.content)},
    }


async def synthesize_brainstorm(state: dict) -> dict:
    from ..llm import MODEL_CONFIG, ainvoke_with_retry, get_llm, get_rate_limit_fallback_models

    insights = state.get("brainstorm_insights", {})
    idea = state.get("idea", {})

    synthesis_model = MODEL_CONFIG["brainstorm_synthesis"]
    llm = get_llm(model=synthesis_model, temperature=0.6, max_tokens=16000)

    insights_text = json.dumps(insights, indent=2, ensure_ascii=False)
    idea_text = json.dumps(idea, indent=2, ensure_ascii=False)

    response = await ainvoke_with_retry(
        llm,
        [
            {
                "role": "system",
                "content": (
                    "You are the Strategist — the synthesis lead of The Vibe Council.\n"
                    "Combine all brainstorming insights into a coherent creative brief.\n"
                    "Identify themes, synergies between agents' ideas, and prioritize "
                    "the most impactful opportunities."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Original idea:\n{idea_text}\n\n"
                    f"Brainstorming insights from all agents:\n{insights_text}\n\n"
                    "Synthesize into a JSON object with:\n"
                    "- 'themes' (list of 3-5 recurring themes across agents)\n"
                    "- 'top_ideas' (list of 5 best ideas ranked, each with "
                    "'title', 'description', 'source_agent')\n"
                    "- 'synergies' (list of idea combinations that are stronger together)\n"
                    "- 'experience_principles' (list of 3 concise UX or visual principles)\n"
                    "- 'demo_hook' (string describing the best 30-second wow moment)\n"
                    "- 'recommended_direction' (string — one paragraph strategic recommendation)\n"
                    "- 'quick_wins' (list of 3 things to implement first)\n"
                    "Return ONLY valid JSON."
                ),
            },
        ],
        fallback_models=get_rate_limit_fallback_models(synthesis_model),
    )

    return {
        "synthesis": _parse_brainstorm(response.content),
        "phase": "brainstorm_complete",
    }


def _parse_brainstorm(content) -> dict:
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
            "ideas": [{"title": "Raw insight", "description": content[:500]}],
            "opportunities": [],
            "wild_card": "",
            "action_items": [],
            "raw_response": content[:500],
        }
