import json
import re

from ..llm import MODEL_CONFIG, ainvoke_with_retry, get_llm, get_rate_limit_fallback_models
from ..state import VibeDeployState
from ..tools.youtube import extract_first_youtube_url, extract_youtube_transcript, is_youtube_url
from .task_contracts import build_task_distribution, derive_execution_tasks

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
    "Important constraints:\n"
    "- Keep the MVP realistic for a hackathon-grade FastAPI + Next.js deployment.\n"
    "- Prefer transcript, URL, and structured AI workflows over heavy media pipelines unless the user explicitly demands uploads.\n"
    "- Do not invent testimonials, awards, press mentions, partnerships, test coverage, pilot statistics, or benchmark numbers.\n"
    "- Return all list fields as plain short strings, not nested objects.\n\n"
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

    youtube_url = extract_first_youtube_url(raw_input) if is_youtube_url(raw_input) else None
    input_type = "youtube" if youtube_url else "text"
    transcript = None
    idea_context = raw_input
    selected_flagship = str(state.get("selected_flagship") or "").strip()
    flagship_contract = state.get("flagship_contract") if isinstance(state.get("flagship_contract"), dict) else {}

    if input_type == "youtube":
        transcript = await extract_youtube_transcript(youtube_url or raw_input)
        additional_guidance = raw_input.replace(youtube_url or raw_input, "", 1).strip()
        if transcript and not transcript.startswith("[Error"):
            context_parts = [
                f"YouTube video content:\n{transcript[:4000]}",
                f"Original URL: {youtube_url}",
            ]
            if additional_guidance:
                context_parts.append(f"Additional user instructions:\n{additional_guidance}")
            idea_context = "\n\n".join(context_parts)
        else:
            context_parts = [f"YouTube URL (content unavailable): {youtube_url}"]
            if additional_guidance:
                context_parts.append(f"Additional user instructions:\n{additional_guidance}")
            idea_context = "\n\n".join(context_parts)

    input_model = MODEL_CONFIG["input"]
    try:
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
        idea = _normalize_idea(_parse_idea_json(response.content))
    except Exception as exc:
        idea = _fallback_idea_from_context(raw_input, transcript, selected_flagship, flagship_contract, str(exc)[:200])

    idea = _merge_flagship_contract(idea, selected_flagship, flagship_contract)
    idea_summary = idea.get("tagline", idea.get("name", raw_input[:100]))
    execution_tasks = derive_execution_tasks(idea, flagship_contract)

    return {
        "input_type": input_type,
        "transcript": transcript,
        "selected_flagship": selected_flagship or None,
        "flagship_contract": flagship_contract or None,
        "idea": idea,
        "idea_summary": idea_summary,
        "execution_tasks": execution_tasks,
        "repair_tasks": [],
        "task_distribution": build_task_distribution(execution_tasks),
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


def _normalize_idea(idea: dict) -> dict:
    normalized = dict(idea or {})
    list_fields = [
        "key_features",
        "tech_hints",
        "monetization_hints",
        "visual_style_hints",
        "must_have_surfaces",
        "proof_points",
        "experience_non_negotiables",
        "reference_objects",
        "sample_seed_data",
    ]
    for field in list_fields:
        normalized[field] = _normalize_string_list(normalized.get(field))

    for field in (
        "name",
        "tagline",
        "problem",
        "solution",
        "target_users",
        "primary_user_flow",
        "differentiation_hook",
        "demo_story_hints",
    ):
        if field in normalized:
            normalized[field] = _normalize_string_value(normalized.get(field))
    return normalized


def _normalize_string_list(value) -> list[str]:
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if not isinstance(value, list):
        return []

    items: list[str] = []
    for entry in value:
        text = _normalize_string_value(entry)
        if text:
            items.append(text)
    return items


def _normalize_string_value(value) -> str:
    if isinstance(value, dict):
        primary = str(value.get("name") or value.get("title") or value.get("label") or "").strip()
        secondary = str(value.get("description") or value.get("detail") or value.get("summary") or "").strip()
        if primary and secondary:
            return f"{primary} - {secondary}"
        return primary or secondary
    if isinstance(value, list):
        parts = [_normalize_string_value(item) for item in value]
        return " / ".join(part for part in parts if part)
    return str(value or "").strip()


def _merge_flagship_contract(idea: dict, selected_flagship: str, contract: dict) -> dict:
    if not selected_flagship and not contract:
        return idea

    merged = dict(idea or {})
    normalized_contract = dict(contract or {})
    required_objects = _normalize_string_list(normalized_contract.get("required_objects"))
    required_results = _normalize_string_list(normalized_contract.get("required_results"))
    acceptance_checks = _normalize_string_list(normalized_contract.get("acceptance_checks"))
    forbidden_patterns = _normalize_string_list(normalized_contract.get("forbidden_patterns"))

    if selected_flagship:
        merged["selected_flagship"] = selected_flagship
    if normalized_contract.get("domain"):
        merged["flagship_domain"] = _normalize_string_value(normalized_contract.get("domain"))
        merged.setdefault("domain", _normalize_string_value(normalized_contract.get("domain")))
    if normalized_contract.get("visual_metaphor"):
        merged.setdefault("interface_metaphor", _normalize_string_value(normalized_contract.get("visual_metaphor")))
    if required_objects:
        merged["reference_objects"] = _merge_unique_strings(merged.get("reference_objects"), required_objects)
        merged["must_have_surfaces"] = _merge_unique_strings(merged.get("must_have_surfaces"), required_objects)
    if required_results:
        merged["sample_seed_data"] = _merge_unique_strings(merged.get("sample_seed_data"), required_results)
        merged["proof_points"] = _merge_unique_strings(merged.get("proof_points"), required_results)
        merged["output_entities"] = _merge_unique_strings(merged.get("output_entities"), required_results)
    if acceptance_checks:
        merged["acceptance_checks"] = _merge_unique_strings(merged.get("acceptance_checks"), acceptance_checks)
        merged["proof_points"] = _merge_unique_strings(merged.get("proof_points"), acceptance_checks)
    if forbidden_patterns:
        merged["experience_non_negotiables"] = _merge_unique_strings(
            merged.get("experience_non_negotiables"),
            forbidden_patterns,
        )
    return merged


def _merge_unique_strings(*groups) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        if isinstance(group, str):
            group = [group]
        if not isinstance(group, list):
            continue
        for item in group:
            text = str(item).strip()
            key = text.lower()
            if not text or key in seen:
                continue
            seen.add(key)
            merged.append(text)
    return merged


def _fallback_idea_from_context(
    raw_input: str,
    transcript: str | None,
    selected_flagship: str,
    contract: dict,
    reason: str,
) -> dict:
    contract = dict(contract or {})
    prompt_text = " ".join(part for part in [raw_input, transcript or ""] if part).strip()
    required_objects = _normalize_string_list(contract.get("required_objects"))
    required_results = _normalize_string_list(contract.get("required_results"))
    acceptance_checks = _normalize_string_list(contract.get("acceptance_checks"))
    forbidden_patterns = _normalize_string_list(contract.get("forbidden_patterns"))
    domain = _normalize_string_value(contract.get("domain")) or _infer_domain(prompt_text)
    visual_metaphor = _normalize_string_value(contract.get("visual_metaphor"))
    name = _humanize_slug(selected_flagship) or _fallback_name(prompt_text)
    tagline = _summarize_prompt(prompt_text, domain)

    return {
        "name": name,
        "tagline": tagline,
        "problem": f"Users need a clearer way to act on {domain or 'their idea'} without starting from a blank product spec.",
        "solution": f"Turn messy input into a structured {domain or 'product'} workflow with visible outputs and saved artifacts.",
        "target_users": f"People exploring {domain or 'a new product direction'} from incomplete context.",
        "key_features": required_objects or ["Guided workflow", "Saved artifacts", "Structured output"],
        "tech_hints": ["FastAPI backend", "Next.js frontend", "Simple persistence"],
        "monetization_hints": [],
        "visual_style_hints": [visual_metaphor] if visual_metaphor else [],
        "primary_user_flow": f"User brings rough context, reviews a structured {domain or 'product'} direction, and saves a usable result.",
        "differentiation_hook": f"Flagship-aware planning fallback used because model extraction was unavailable ({reason}).",
        "demo_story_hints": f"Show the system turning messy input into a usable {domain or 'product'} artifact in one pass.",
        "must_have_surfaces": required_objects[:5] or ["structured brief", "primary workflow", "saved results"],
        "proof_points": _merge_unique_strings(required_results, acceptance_checks)
        or ["Visible saved output", "Practical first-run result"],
        "experience_non_negotiables": forbidden_patterns,
        "reference_objects": required_objects,
        "sample_seed_data": required_results,
        "output_entities": required_results,
        "acceptance_checks": acceptance_checks,
    }


def _infer_domain(text: str) -> str:
    lowered = (text or "").lower()
    if any(token in lowered for token in ("travel", "trip", "route", "district", "weekend")):
        return "travel planning"
    if any(token in lowered for token in ("creator", "content", "hook", "publish", "short-form")):
        return "creator workflow"
    if any(token in lowered for token in ("budget", "cash", "money", "finance", "runway")):
        return "financial planning"
    if any(token in lowered for token in ("interview", "study", "learning", "drill", "sprint")):
        return "learning planner"
    if any(token in lowered for token in ("meal", "grocery", "prep", "cook", "recipe")):
        return "meal prep planning"
    return "product planning"


def _humanize_slug(value: str) -> str:
    text = str(value or "").strip().replace("-", " ")
    return " ".join(part.capitalize() for part in text.split())


def _fallback_name(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "").strip())
    words = [word for word in re.findall(r"[A-Za-z0-9]+", cleaned) if len(word) > 2]
    return " ".join(word.capitalize() for word in words[:3]) or "VibeDeploy Product"


def _summarize_prompt(text: str, domain: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "").strip())
    if cleaned:
        return cleaned[:120]
    return f"Turn rough {domain or 'product'} intent into a usable shipped experience."
