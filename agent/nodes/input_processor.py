import json
import re

from ..llm import MODEL_CONFIG, ainvoke_with_retry, get_llm, get_rate_limit_fallback_models
from ..state import VibeDeployState
from ..tools.youtube import extract_youtube_transcript, is_youtube_url

IDEA_EXTRACTION_PROMPT = (
    "You are an expert product analyst. Given the user's raw input (and optionally a YouTube transcript), "
    "extract a structured idea description.\n\n"
    "Return a JSON object with these fields:\n"
    "- name: A short, catchy app name suggestion (2-3 words)\n"
    "- tagline: One-line elevator pitch\n"
    "- problem: The problem it solves\n"
    "- solution: How it solves the problem\n"
    "- target_users: Who would use this\n"
    "- key_features: List of 3-5 core features\n"
    "- tech_hints: Any technology preferences mentioned\n"
    "- monetization_hints: Any revenue model hints\n\n"
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
            "raw_response": content[:500],
        }
