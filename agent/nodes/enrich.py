import json
import re

from ..state import VibeDeployState

ENRICH_PROMPT = (
    "You are a product strategist. Given a raw app idea, ENRICH it by adding:\n"
    "- Refined feature set (expand vague features into specific, buildable features)\n"
    "- Technical approach (suggest concrete tech stack and architecture)\n"
    "- Market positioning (target audience, competitive angle)\n"
    "- UX highlights (key user flows, onboarding experience)\n"
    "- Risk mitigations (proactive solutions for obvious challenges)\n\n"
    "Return a JSON object with:\n"
    "- 'enriched_features': list of 5-7 specific features (each with 'name' and 'description')\n"
    "- 'tech_approach': string describing recommended architecture\n"
    "- 'market_position': string describing target market and positioning\n"
    "- 'ux_highlights': list of 3 key UX moments\n"
    "- 'risk_mitigations': list of 2-3 preemptive solutions\n"
    "- 'enhanced_tagline': improved one-liner\n"
    "Return ONLY valid JSON."
)


async def enrich_idea(state: VibeDeployState) -> dict:
    from ..llm import MODEL_CONFIG, ainvoke_with_retry, get_llm, get_rate_limit_fallback_models

    idea = state.get("idea", {})
    brainstorm_model = MODEL_CONFIG["brainstorm"]
    llm = get_llm(model=brainstorm_model, temperature=0.7, max_tokens=4000)

    idea_text = json.dumps(idea, indent=2, ensure_ascii=False)
    response = await ainvoke_with_retry(
        llm,
        [
            {"role": "system", "content": ENRICH_PROMPT},
            {"role": "user", "content": f"Enrich this app idea:\n\n{idea_text}"},
        ],
        fallback_models=get_rate_limit_fallback_models(brainstorm_model),
    )

    enrichment = _parse_json(response.content)

    merged_idea = {**idea}
    if enrichment.get("enriched_features"):
        merged_idea["key_features"] = enrichment["enriched_features"]
    if enrichment.get("tech_approach"):
        merged_idea["tech_approach"] = enrichment["tech_approach"]
    if enrichment.get("market_position"):
        merged_idea["market_position"] = enrichment["market_position"]
    if enrichment.get("enhanced_tagline"):
        merged_idea["tagline"] = enrichment["enhanced_tagline"]

    return {
        "idea": merged_idea,
        "original_idea": idea,
        "enrich_result": enrichment,
        "eval_iteration": 0,
        "phase": "enriched",
    }


def _parse_json(content) -> dict:
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
        return {}
