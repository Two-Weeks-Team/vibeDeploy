import json
import re

from ..llm import MODEL_CONFIG, ainvoke_with_retry, get_llm, get_rate_limit_fallback_models
from ..state import VibeDeployState
from ..tools.youtube import extract_youtube_transcript, is_youtube_url

IDEA_EXTRACTION_PROMPT = (
    "You are an expert product and experience strategist. Given the user's raw input "
    "(and optionally a YouTube transcript), extract a structured idea description that "
    "preserves product intent, user workflow, and any visual cues.\n\n"
    "Return a JSON object with these fields:\n"
    "- name: A short, catchy app name suggestion (2-3 words)\n"
    "- tagline: One-line elevator pitch\n"
    "- problem: The problem it solves\n"
    "- solution: How it solves the problem\n"
    "- target_users: Who would use this\n"
    "- key_features: List of 3-5 core features\n"
    "- tech_hints: Any technology preferences mentioned\n"
    "- monetization_hints: Any revenue model hints\n\n"
    "- visual_style_hints: List of any brand, mood, design, or aesthetic cues implied by the input\n"
    "- primary_user_flow: One sentence describing the core before/after journey\n"
    "- differentiation_hook: Why this should feel distinct from a generic dashboard or chatbot\n"
    "- demo_story_hints: What moment should feel impressive in a live demo\n\n"
    "- must_have_surfaces: List of 3-5 concrete first-screen surfaces the product should show (examples: analysis workbench, saved library, recent activity, insights rail)\n"
    "- proof_points: List of trust, credibility, or proof elements users would expect before believing the product\n"
    "- experience_non_negotiables: List of UX constraints or anti-patterns the product must respect\n\n"
    "If the user did not specify a field, infer cautiously from the domain and keep it concise.\n"
    "Return ONLY valid JSON, no markdown fences."
)


async def input_processor(state: VibeDeployState) -> dict:
    raw_input = state.get("raw_input", "")
    if not raw_input.strip():
        return {
            "error": "No input provided",
            "phase": "error",
        }

    input_type = "youtube" if is_youtube_url(raw_input) else "text"
    transcript = None
    idea_context = raw_input

    if input_type == "youtube":
        transcript = await extract_youtube_transcript(raw_input)
        if transcript and not transcript.startswith("[Error"):
            idea_context = f"YouTube video content:\n{transcript[:4000]}\n\nOriginal URL: {raw_input}"
        else:
            idea_context = f"YouTube URL (content unavailable): {raw_input}"

    input_model = MODEL_CONFIG["input"]
    llm = get_llm(
        model=input_model,
        temperature=0.4,
        max_tokens=2000,
    )

    response = await ainvoke_with_retry(
        llm,
        [
            {"role": "system", "content": IDEA_EXTRACTION_PROMPT},
            {"role": "user", "content": idea_context},
        ],
        fallback_models=get_rate_limit_fallback_models(input_model),
    )

    idea = _parse_idea_json(response.content)
    idea_summary = idea.get("tagline", idea.get("name", raw_input[:100]))

    return {
        "input_type": input_type,
        "transcript": transcript,
        "idea": idea,
        "idea_summary": idea_summary,
        "phase": "council_analysis",
    }


def _parse_idea_json(content) -> dict:
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
            "name": "Unknown App",
            "tagline": content[:100],
            "problem": "Could not parse structured idea",
            "solution": content[:200],
            "target_users": "Unknown",
            "key_features": [],
            "tech_hints": [],
            "monetization_hints": [],
            "visual_style_hints": [],
            "primary_user_flow": "",
            "differentiation_hook": "",
            "demo_story_hints": "",
            "must_have_surfaces": [],
            "proof_points": [],
            "experience_non_negotiables": [],
            "raw_response": content[:500],
        }
