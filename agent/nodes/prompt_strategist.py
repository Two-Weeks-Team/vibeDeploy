import asyncio
import logging
import re
import time

import httpx

from ..llm import MODEL_CONFIG, get_rate_limit_fallback_models
from ..state import VibeDeployState

logger = logging.getLogger(__name__)

_PROMPT_RESEARCH_TTL_SECONDS = 6 * 60 * 60
_PROMPT_RESEARCH_TIMEOUT_SECONDS = 8.0
_PROMPT_RESEARCH_CACHE: dict[str, tuple[float, dict]] = {}

_OFFICIAL_MODEL_SOURCES = {
    "openai_gpt_oss": [
        {
            "label": "OpenAI GPT-OSS README",
            "url": "https://raw.githubusercontent.com/openai/gpt-oss/main/README.md",
        }
    ],
    "qwen3": [
        {
            "label": "Qwen3 README",
            "url": "https://raw.githubusercontent.com/QwenLM/Qwen3/main/README.md",
        }
    ],
    "deepseek_r1": [
        {
            "label": "DeepSeek-R1 README",
            "url": "https://raw.githubusercontent.com/deepseek-ai/DeepSeek-R1/master/README.md",
        }
    ],
    "generic": [],
}

_STATIC_MODEL_GUIDANCE = {
    "openai_gpt_oss": [
        "Keep role separation clear and make the output contract explicit because GPT-OSS expects chat/harmony-style structure.",
        "State the required final format directly and keep file-map schemas strict to improve parse reliability.",
        "Request only the final answer and keep hidden reasoning out of the user-visible response.",
    ],
    "qwen3": [
        "Force non-thinking behavior for code generation so the model emits only the final artifact payload.",
        "Repeat the output contract in the user message because Qwen can switch behavior based on the latest /think or /no_think instruction.",
        "Keep instructions short, direct, and format-first to reduce extra reasoning blocks.",
    ],
    "deepseek_r1": [
        "Place task-critical instructions in the user message because DeepSeek-R1 guidance recommends not relying on a system prompt.",
        "Use a moderate temperature band when DeepSeek is active to avoid repetition and unstable outputs.",
        "Ask for the final JSON/file-map only and do not invite free-form commentary.",
    ],
    "generic": [
        "Keep the task contract explicit, deterministic, and parseable.",
        "Repeat the final output schema in the user message.",
        "Prefer concise, implementation-ready instructions over open-ended ideation phrasing.",
    ],
}


async def prompt_strategist(state: VibeDeployState) -> dict:
    idea = state.get("idea", {}) or {}
    blueprint = state.get("blueprint", {}) or {}
    generated_docs = state.get("generated_docs", {}) or {}

    model_plan = _build_model_plan()
    family_names = {
        model_plan["frontend"]["family"],
        model_plan["backend"]["family"],
        *model_plan["frontend"]["fallback_families"],
        *model_plan["backend"]["fallback_families"],
    }
    guidance_by_family = await _collect_family_guidance(family_names)
    strategy = _build_prompt_strategy(
        idea=idea,
        blueprint=blueprint,
        generated_docs=generated_docs,
        model_plan=model_plan,
        guidance_by_family=guidance_by_family,
    )

    return {
        "prompt_strategy": strategy,
        "phase": "prompt_strategy",
    }


def infer_model_family(model: str) -> str:
    normalized = (model or "").strip().lower()
    if "gpt-oss" in normalized:
        return "openai_gpt_oss"
    if "qwen3" in normalized or "qwen-" in normalized or normalized.startswith("qwen"):
        return "qwen3"
    if "deepseek-r1" in normalized:
        return "deepseek_r1"
    return "generic"


def _build_model_plan() -> dict:
    frontend_model = MODEL_CONFIG.get("code_gen_frontend", MODEL_CONFIG["code_gen"]) or MODEL_CONFIG["code_gen"]
    backend_model = MODEL_CONFIG.get("code_gen_backend", MODEL_CONFIG["code_gen"]) or MODEL_CONFIG["code_gen"]
    frontend_fallbacks = get_rate_limit_fallback_models(frontend_model)
    backend_fallbacks = get_rate_limit_fallback_models(backend_model)

    return {
        "frontend": {
            "model": frontend_model,
            "family": infer_model_family(frontend_model),
            "fallback_models": frontend_fallbacks,
            "fallback_families": _unique(infer_model_family(model) for model in frontend_fallbacks),
        },
        "backend": {
            "model": backend_model,
            "family": infer_model_family(backend_model),
            "fallback_models": backend_fallbacks,
            "fallback_families": _unique(infer_model_family(model) for model in backend_fallbacks),
        },
    }


async def _collect_family_guidance(families: set[str]) -> dict[str, dict]:
    tasks = [asyncio.create_task(_get_family_guidance(family)) for family in families if family]
    if not tasks:
        return {}

    results = await asyncio.gather(*tasks)
    return {result["family"]: result for result in results}


async def _get_family_guidance(family: str) -> dict:
    cached = _PROMPT_RESEARCH_CACHE.get(family)
    now = time.time()
    if cached and now - cached[0] < _PROMPT_RESEARCH_TTL_SECONDS:
        return cached[1]

    sources = list(_OFFICIAL_MODEL_SOURCES.get(family, []))
    notes = list(_STATIC_MODEL_GUIDANCE.get(family, _STATIC_MODEL_GUIDANCE["generic"]))
    source_entries: list[dict[str, object]] = []

    if sources:
        async with httpx.AsyncClient(timeout=_PROMPT_RESEARCH_TIMEOUT_SECONDS, follow_redirects=True) as client:
            for source in sources:
                try:
                    response = await client.get(source["url"])
                    response.raise_for_status()
                    extracted = _extract_guidance_from_source(family, response.text)
                    notes.extend(extracted)
                    source_entries.append(
                        {
                            "label": source["label"],
                            "url": source["url"],
                            "status": "fetched",
                            "highlights": extracted[:3],
                        }
                    )
                except Exception as exc:
                    logger.warning("[PROMPT_STRATEGIST] Failed to fetch %s: %s", source["url"], exc)
                    source_entries.append(
                        {
                            "label": source["label"],
                            "url": source["url"],
                            "status": "fallback",
                            "highlights": [],
                        }
                    )

    payload = {
        "family": family,
        "notes": _unique(notes),
        "sources": source_entries,
    }
    _PROMPT_RESEARCH_CACHE[family] = (now, payload)
    return payload


def _extract_guidance_from_source(family: str, source: str) -> list[str]:
    normalized = source or ""
    notes: list[str] = []

    if family == "openai_gpt_oss":
        if "harmony response format" in normalized.lower():
            notes.append("Use standard chat-role structure and a strict message contract because GPT-OSS is trained around Harmony format.")
        if "configurable reasoning effort" in normalized.lower():
            notes.append("Call out the expected reasoning depth in plain language so GPT-OSS does not over- or under-think the generation task.")
        if "structured outputs" in normalized.lower():
            notes.append("Lean on structured output contracts for machine-parseable file bundles.")
    elif family == "qwen3":
        if "/no_think" in normalized or "enable_thinking=false" in normalized.lower():
            notes.append("Inject `/no_think` into code-generation requests so Qwen stays in final-answer mode.")
        if "non-thinking mode" in normalized.lower():
            notes.append("Prefer non-thinking mode for artifact generation and reserve deeper reasoning only for planning or diagnosis.")
    elif family == "deepseek_r1":
        if "avoid adding a system prompt" in normalized.lower():
            notes.append("Repeat all critical instructions in the user message so DeepSeek does not lose constraints when the system role is ignored.")
        temp_match = re.search(r"temperature within the range of 0\.5-0\.7", normalized, flags=re.IGNORECASE)
        if temp_match:
            notes.append("Keep DeepSeek generation near the 0.5-0.7 band when it becomes the active code model.")
        if "please reason step by step" in normalized.lower():
            notes.append("Allow structured internal reasoning, but still demand a compact final artifact with no extra prose.")

    return notes


def _build_prompt_strategy(
    *,
    idea: dict,
    blueprint: dict,
    generated_docs: dict,
    model_plan: dict,
    guidance_by_family: dict[str, dict],
) -> dict:
    idea_name = idea.get("name") or idea.get("tagline") or "Hackathon product"
    design_system = blueprint.get("design_system", {}) or {}
    experience_contract = blueprint.get("experience_contract", {}) or {}
    frontend_contract = blueprint.get("frontend_backend_contract", []) or []
    frontend_files = list((blueprint.get("frontend_files") or {}).keys())
    backend_files = list((blueprint.get("backend_files") or {}).keys())

    required_surfaces = _coerce_strings(experience_contract.get("required_surfaces"))
    required_states = _coerce_strings(experience_contract.get("required_states"))
    proof_points = _coerce_strings(experience_contract.get("proof_points"))
    layout_archetype = str(idea.get("layout_archetype") or "").strip()
    interface_metaphor = str(idea.get("interface_metaphor") or "").strip()
    signature_demo_moments = _coerce_strings(idea.get("signature_demo_moments"))
    output_entities = _coerce_strings(idea.get("output_entities"))
    trust_surfaces = _coerce_strings(idea.get("trust_surfaces"))
    tech_spec = generated_docs.get("tech_spec", "")
    api_spec = generated_docs.get("api_spec", "")
    context_priority = [
        "Generated docs (PRD, tech spec, API spec, DB schema) define the delivery contract first.",
        "Blueprint manifest (required files, surfaces, states, and frontend/backend contract) overrides speculative implementation choices.",
        "Official runtime model guidance tunes prompt shape for the active and fallback model families.",
        "Specialist briefs constrain execution by frontend, backend, QA, and delivery concerns.",
        "The final output contract remains strict JSON with complete file bodies only.",
    ]
    quality_gates = [
        "Document-first execution: generated docs and blueprint beat improvisation.",
        "Layered context delivery: shared delivery brief, target expert brief, model-family guidance, then final output contract.",
        "Language-server discipline: valid imports, defined symbols, compile-safe file bodies, and exact type alignment.",
        "No guessing: derive fields from the existing contract instead of inventing extra endpoints, props, or schema columns.",
        "Do not collapse concept-specific nouns into the same hero/workspace/feature/collection taxonomy when the idea defines a sharper interface metaphor.",
    ]

    frontend_guidance = _flatten_guidance(model_plan["frontend"], guidance_by_family)
    backend_guidance = _flatten_guidance(model_plan["backend"], guidance_by_family)

    specialist_briefs = {
        "cto_lead": _render_brief(
            "CTO Lead",
            [
                f"Ship `{idea_name}` as a judge-ready demo, not a generic scaffold.",
                "Treat the blueprint manifest as a delivery contract, not a suggestion.",
                f"Preserve proof points on first load: {_human_join(proof_points) or 'credible output framing and visible workflow value'}.",
                "Prefer opinionated, complete implementations over optional placeholders.",
            ],
        ),
        "frontend_architect": _render_brief(
            "Frontend Architect",
            [
                f"Visual direction: {design_system.get('visual_direction', 'intentional domain-specific product surface')}.",
                f"Layout archetype: {layout_archetype or 'domain-led custom surface'}.",
                f"Interface metaphor: {interface_metaphor or 'product-specific workflow metaphor'}.",
                f"Required surfaces: {_human_join(required_surfaces) or 'hero, workspace, and supporting insight surfaces'}.",
                f"Required states: {_human_join(required_states) or 'loading, empty, error, success'}.",
                f"Trust surfaces: {_human_join(trust_surfaces) or 'credible saved work and visible proof points'}.",
                f"Output entities that should appear in the UI: {_human_join(output_entities) or 'domain objects, not generic cards'}.",
                f"Manifest-critical frontend files: {_human_join(frontend_files[:6])}.",
            ],
        ),
        "backend_expert": _render_brief(
            "Backend Expert",
            [
                "Honor the frontend/backend contract exactly for endpoint paths, methods, request fields, and response fields.",
                f"Manifest-critical backend files: {_human_join(backend_files[:6])}.",
                _summarize_spec_line(api_spec, fallback="Keep API contracts explicit and machine-safe for the frontend."),
                _summarize_spec_line(tech_spec, fallback="Keep runtime and dependency choices DigitalOcean-compatible."),
            ],
        ),
        "prompt_engineer": _render_brief(
            "Prompt Engineer",
            [
                f"Frontend model: {model_plan['frontend']['model']} ({model_plan['frontend']['family']}).",
                f"Backend model: {model_plan['backend']['model']} ({model_plan['backend']['family']}).",
                f"Frontend guidance: {_human_join(frontend_guidance[:3])}.",
                f"Backend guidance: {_human_join(backend_guidance[:3])}.",
                f"Signature demo moments: {_human_join(signature_demo_moments) or 'one vivid first-run transformation'}.",
            ],
        ),
        "qa_strategist": _render_brief(
            "QA Strategist",
            [
                "Use LSP-grade correctness as a prompt constraint: valid imports, defined symbols, compile-safe file bodies, and strict endpoint alignment.",
                "Emit only complete files and prefer deterministic code paths over speculative abstractions.",
                f"Contract items to preserve: {max(len(frontend_contract), 1)} explicit frontend/backend integration path(s).",
            ],
        ),
    }

    source_index = []
    for family in _unique(
        [
            model_plan["frontend"]["family"],
            *model_plan["frontend"]["fallback_families"],
            model_plan["backend"]["family"],
            *model_plan["backend"]["fallback_families"],
        ]
    ):
        family_data = guidance_by_family.get(family, {"sources": []})
        for source in family_data.get("sources", []):
            source_index.append(
                {
                    "family": family,
                    "label": source.get("label", ""),
                    "url": source.get("url", ""),
                    "status": source.get("status", "fallback"),
                }
            )

    shared_prompt_appendix = "\n\n".join(
        [
            "Runtime Strategy Stack",
            _render_brief("Context Priority Order", context_priority),
            _render_brief("Runtime Quality Gates", quality_gates),
            specialist_briefs["cto_lead"],
            specialist_briefs["prompt_engineer"],
            specialist_briefs["qa_strategist"],
        ]
    )
    frontend_prompt_appendix = "\n\n".join(
        [
            shared_prompt_appendix,
            specialist_briefs["frontend_architect"],
        ]
    )
    backend_prompt_appendix = "\n\n".join(
        [
            shared_prompt_appendix,
            specialist_briefs["backend_expert"],
        ]
    )

    return {
        "strategy_version": "prompt-strategy-v1",
        "model_plan": model_plan,
        "model_guidance": guidance_by_family,
        "context_priority": context_priority,
        "quality_gates": quality_gates,
        "specialist_briefs": specialist_briefs,
        "shared_prompt_appendix": shared_prompt_appendix,
        "frontend_prompt_appendix": frontend_prompt_appendix,
        "backend_prompt_appendix": backend_prompt_appendix,
        "cross_model_user_contract": _render_brief(
            "Cross-Model Output Contract",
            [
                "Return only the final JSON object with a top-level `files` key.",
                "Do not emit markdown fences, commentary, or chain-of-thought.",
                "Every file body must be complete, self-contained, and ready to write to disk.",
                "If the model supports explicit thinking modes, stay in final-answer mode for code generation.",
            ],
        ),
        "source_index": source_index,
    }


def _flatten_guidance(plan: dict, guidance_by_family: dict[str, dict]) -> list[str]:
    notes: list[str] = []
    family_names = [plan["family"], *plan["fallback_families"]]
    for family in _unique(family_names):
        notes.extend(guidance_by_family.get(family, {}).get("notes", []))
    return _unique(notes)


def _render_brief(title: str, items: list[str]) -> str:
    cleaned = [item.strip() for item in items if item and item.strip()]
    return f"{title}:\n" + "\n".join(f"- {item}" for item in cleaned)


def _coerce_strings(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _human_join(items: list[str]) -> str:
    cleaned = [item.strip() for item in items if item and item.strip()]
    return ", ".join(cleaned)


def _summarize_spec_line(spec: str, fallback: str) -> str:
    if not spec:
        return fallback
    for line in spec.splitlines():
        stripped = line.strip().lstrip("-").strip()
        if len(stripped) >= 24:
            return stripped[:180]
    return fallback


def _unique(values) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered
