import json
import logging
import re

from ..llm import MODEL_CONFIG, ainvoke_with_retry, content_to_str, get_llm, get_rate_limit_fallback_models
from ..state import VibeDeployState

logger = logging.getLogger(__name__)
_COLLECTION_UI_HINTS = (
    "save",
    "saved",
    "bookmark",
    "favorite",
    "library",
    "dashboard",
    "history",
    "collection",
    "organize",
    "manage",
    "review",
    "track",
)

BLUEPRINT_SYSTEM_PROMPT = """You are a senior software architect creating a file manifest for a full-stack application.

Given: PRD, Tech Spec, API Spec, and DB Schema documents.

Output a JSON object with this exact structure:
{
  "app_name": "short-kebab-name",
  "design_system": {
    "visual_direction": "brief phrase",
    "color_tokens": ["background", "primary", "accent"],
    "typography": "headline/body pairing",
    "motion_principles": ["staggered reveal", "soft hover lift"],
    "ui_constraints": ["avoid generic admin templates"]
  },
  "frontend_files": {
    "package.json": {"purpose": "npm manifest", "imports_from": [], "exports": []},
    "src/app/layout.tsx": {"purpose": "root layout", "imports_from": ["src/app/globals.css"], "exports": ["RootLayout"]},
    "src/app/page.tsx": {"purpose": "main landing page", "imports_from": ["src/components/Hero.tsx"], "exports": ["default"]},
    "src/app/globals.css": {"purpose": "global styles", "imports_from": [], "exports": []},
    "src/lib/api.ts": {"purpose": "API client", "imports_from": [], "exports": ["fetchItems"]}
  },
  "backend_files": {
    "requirements.txt": {"purpose": "python deps", "imports_from": [], "exports": []},
    "main.py": {"purpose": "FastAPI app entry", "imports_from": ["routes", "models"], "exports": ["app"]},
    "models.py": {"purpose": "SQLAlchemy models", "imports_from": [], "exports": ["Base", "engine"]},
    "routes.py": {"purpose": "API routes", "imports_from": ["models", "ai_service"], "exports": ["router"]},
    "ai_service.py": {"purpose": "DO inference client", "imports_from": [], "exports": ["call_inference"]}
  },
  "shared_constants": {
    "api_base_url": "/api",
    "env_vars": ["DATABASE_URL", "DIGITALOCEAN_INFERENCE_KEY"],
    "theme_tokens": ["background", "foreground", "primary", "accent", "card"]
  },
  "experience_contract": {
    "required_surfaces": ["hero", "primary workspace", "saved library"],
    "required_states": ["loading", "empty", "error", "success"],
    "proof_points": ["visible recent activity", "credible output framing"],
    "interaction_style": "brief phrase"
  },
  "frontend_backend_contract": [
    {"frontend_file": "src/lib/api.ts", "calls": "GET /api/items", "backend_file": "routes.py", "request_fields": [], "response_fields": ["items"]}
  ]
}

Rules:
- Frontend: Next.js 15 App Router. Required: package.json, src/app/layout.tsx, src/app/page.tsx, src/app/globals.css, src/lib/api.ts, 2-3 domain components.
- The frontend manifest must include a primary workflow shell, a result/list/detail component, and at least one explicit state or feedback component when relevant.
- Include an experience_contract that states which surfaces, states, and proof points must be visible in the generated UI.
- Backend: FastAPI. Required: requirements.txt, main.py, models.py, routes.py, ai_service.py.
- All backend files are FLAT in project root (no packages, no relative imports).
- Every file must have a clear purpose and list its dependencies.
- Include at least 2 AI-powered business endpoints in the contract.
- The contract should make request body field names explicit when a POST or PUT endpoint is involved.
- Reflect the visual direction from the PRD and tech spec in the manifest so code generation can carry it through.
- Return ONLY the JSON object, no markdown wrapping."""


async def blueprint_generator(state: VibeDeployState) -> dict:
    generated_docs = state.get("generated_docs", {})
    idea = state.get("idea", {})

    doc_model = MODEL_CONFIG["doc_gen"]
    fallback_models = get_rate_limit_fallback_models(doc_model)
    if _should_use_template_blueprint(fallback_models):
        return {"blueprint": _build_template_blueprint(idea), "phase": "blueprint"}

    llm = get_llm(model=doc_model, temperature=0.2, max_tokens=4000)

    context = json.dumps(
        {"idea": idea, "generated_docs": generated_docs},
        indent=2,
        ensure_ascii=False,
    )

    response = await ainvoke_with_retry(
        llm,
        [
            {"role": "system", "content": BLUEPRINT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Create a file manifest for this application:\n\n{context}"},
        ],
        fallback_models=fallback_models,
    )

    raw = content_to_str(response.content).strip()
    cleaned = raw
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)

    try:
        blueprint = json.loads(cleaned)
    except json.JSONDecodeError:
        json_match = re.search(r"\{[\s\S]*\}", cleaned)
        if json_match:
            try:
                blueprint = json.loads(json_match.group())
            except json.JSONDecodeError:
                logger.error("[BLUEPRINT] All JSON parse attempts failed")
                blueprint = {"error": "parse_failed", "raw": raw[:500]}
        else:
            blueprint = {"error": "no_json_found", "raw": raw[:500]}

    logger.info(
        "[BLUEPRINT] Generated: frontend=%d files, backend=%d files",
        len(blueprint.get("frontend_files", {})),
        len(blueprint.get("backend_files", {})),
    )

    blueprint = _normalize_blueprint(blueprint, idea)

    return {"blueprint": blueprint, "phase": "blueprint"}


def _should_use_template_blueprint(fallback_models: list[str]) -> bool:
    return not fallback_models


def _build_template_blueprint(idea: dict) -> dict:
    app_name = _slugify(idea.get("name") or idea.get("tagline") or "vibedeploy-app")
    visual_direction = _coerce_string_list(idea.get("visual_style_hints"))[:2]
    required_surfaces = _coerce_string_list(idea.get("must_have_surfaces"))[:5]
    proof_points = _coerce_string_list(idea.get("proof_points"))[:5]
    non_negotiables = _coerce_string_list(idea.get("experience_non_negotiables"))[:5]

    blueprint = {
        "app_name": app_name,
        "design_system": {
            "visual_direction": ", ".join(visual_direction) if visual_direction else "editorial showcase workspace",
            "color_tokens": ["background", "primary", "accent", "card", "muted"],
            "typography": "display serif with clean sans body",
            "motion_principles": ["staggered reveal", "soft hover lift", "panel transitions"],
            "ui_constraints": ["avoid generic admin templates", "keep the first screen demo-ready"],
        },
        "frontend_files": {},
        "backend_files": {},
        "shared_constants": {
            "api_base_url": "/api",
            "env_vars": ["DATABASE_URL", "DIGITALOCEAN_INFERENCE_KEY"],
            "theme_tokens": ["background", "foreground", "primary", "accent", "card"],
        },
        "experience_contract": {
            "required_surfaces": required_surfaces or ["hero", "primary workspace", "results panel", "saved library"],
            "required_states": ["loading", "empty", "error", "success"],
            "proof_points": proof_points or ["visible recent activity", "credible result framing", "shareable outputs"],
            "interaction_style": "guided, tactile, and demo-friendly",
        },
        "frontend_backend_contract": [
            {
                "frontend_file": "src/lib/api.ts",
                "calls": "POST /api/plan",
                "backend_file": "routes.py",
                "request_fields": ["query", "preferences"],
                "response_fields": ["summary", "items", "score"],
            },
            {
                "frontend_file": "src/lib/api.ts",
                "calls": "POST /api/insights",
                "backend_file": "routes.py",
                "request_fields": ["selection", "context"],
                "response_fields": ["insights", "next_actions", "highlights"],
            },
        ],
    }

    if non_negotiables:
        blueprint["design_system"]["ui_constraints"].extend(non_negotiables)

    return _normalize_blueprint(blueprint, idea)


def _normalize_blueprint(blueprint: dict, idea: dict) -> dict:
    if not isinstance(blueprint, dict):
        return blueprint

    normalized = dict(blueprint)
    frontend_files = dict(normalized.get("frontend_files") or {})
    backend_files = dict(normalized.get("backend_files") or {})

    frontend_files.setdefault("package.json", {"purpose": "npm manifest", "imports_from": [], "exports": []})
    frontend_files.setdefault(
        "src/app/layout.tsx",
        {"purpose": "root layout", "imports_from": ["src/app/globals.css"], "exports": ["RootLayout"]},
    )
    frontend_files.setdefault(
        "src/app/page.tsx",
        {"purpose": "main landing page", "imports_from": ["src/components/Hero.tsx"], "exports": ["default"]},
    )
    frontend_files.setdefault("src/app/globals.css", {"purpose": "global styles", "imports_from": [], "exports": []})
    frontend_files.setdefault("src/lib/api.ts", {"purpose": "API client", "imports_from": [], "exports": ["fetchItems"]})
    backend_files.setdefault("requirements.txt", {"purpose": "python deps", "imports_from": [], "exports": []})
    backend_files.setdefault(
        "main.py",
        {"purpose": "FastAPI app entry", "imports_from": ["routes", "models"], "exports": ["app"]},
    )
    backend_files.setdefault("models.py", {"purpose": "SQLAlchemy models", "imports_from": [], "exports": ["Base", "engine"]})
    backend_files.setdefault(
        "routes.py",
        {"purpose": "API routes", "imports_from": ["models", "ai_service"], "exports": ["router"]},
    )
    backend_files.setdefault(
        "ai_service.py",
        {"purpose": "DO inference client", "imports_from": [], "exports": ["call_inference"]},
    )

    page_meta = frontend_files.get("src/app/page.tsx")
    if not isinstance(page_meta, dict):
        page_meta = {"purpose": "main landing page", "imports_from": [], "exports": ["default"]}
    imports_from = page_meta.get("imports_from", [])
    if not isinstance(imports_from, list):
        imports_from = []

    idea_text = json.dumps(idea, ensure_ascii=False).lower()
    wants_collection_ui = any(token in idea_text for token in _COLLECTION_UI_HINTS)
    must_have_surfaces = _coerce_string_list(idea.get("must_have_surfaces"))
    proof_points = _coerce_string_list(idea.get("proof_points"))
    experience_non_negotiables = _coerce_string_list(idea.get("experience_non_negotiables"))

    component_specs = {
        "src/components/Hero.tsx": {
            "purpose": "hero and product positioning",
            "imports_from": ["src/lib/api.ts"],
            "exports": ["default"],
        },
        "src/components/InsightPanel.tsx": {
            "purpose": "primary AI result or detail panel",
            "imports_from": ["src/lib/api.ts"],
            "exports": ["default"],
        },
        "src/components/StatePanel.tsx": {
            "purpose": "loading, empty, error, and success states",
            "imports_from": [],
            "exports": ["default"],
        },
    }
    if wants_collection_ui:
        component_specs["src/components/CollectionPanel.tsx"] = {
            "purpose": "saved items, history, favorites, or dashboard surface",
            "imports_from": ["src/lib/api.ts"],
            "exports": ["default"],
        }
        component_specs["src/components/StatsStrip.tsx"] = {
            "purpose": "high-level metrics or quick status chips",
            "imports_from": [],
            "exports": ["default"],
        }
    else:
        component_specs["src/components/WorkspacePanel.tsx"] = {
            "purpose": "primary workbench or input workspace",
            "imports_from": ["src/lib/api.ts"],
            "exports": ["default"],
        }
        component_specs["src/components/FeaturePanel.tsx"] = {
            "purpose": "secondary feature or proof surface",
            "imports_from": [],
            "exports": ["default"],
        }

    for path, meta in component_specs.items():
        frontend_files.setdefault(path, meta)
        if path not in imports_from:
            imports_from.append(path)

    page_meta["imports_from"] = imports_from
    page_meta.setdefault("exports", ["default"])
    frontend_files["src/app/page.tsx"] = page_meta

    shared_constants = dict(normalized.get("shared_constants") or {})
    shared_constants.setdefault("api_base_url", "/api")
    shared_constants.setdefault("env_vars", ["DATABASE_URL", "DIGITALOCEAN_INFERENCE_KEY"])
    theme_tokens = shared_constants.get("theme_tokens", [])
    if not isinstance(theme_tokens, list):
        theme_tokens = []
    for token in ["background", "foreground", "primary", "accent", "card", "muted"]:
        if token not in theme_tokens:
            theme_tokens.append(token)
    shared_constants["theme_tokens"] = theme_tokens

    design_system = dict(normalized.get("design_system") or {})
    design_system.setdefault(
        "visual_direction",
        "editorial product surface with a clear hero, workbench, and supporting panels",
    )
    design_system.setdefault("color_tokens", ["background", "primary", "accent", "card", "muted"])
    design_system.setdefault("typography", "expressive headline paired with readable body copy")
    design_system.setdefault("motion_principles", ["staggered reveal", "soft state transitions"])
    constraints = design_system.get("ui_constraints", [])
    if not isinstance(constraints, list):
        constraints = []
    if "avoid generic admin templates" not in constraints:
        constraints.append("avoid generic admin templates")
    if "avoid single centered forms without secondary surfaces" not in constraints:
        constraints.append("avoid single centered forms without secondary surfaces")
    for rule in experience_non_negotiables:
        if rule not in constraints:
            constraints.append(rule)
    design_system["ui_constraints"] = constraints

    experience_contract = dict(normalized.get("experience_contract") or {})
    required_surfaces = _merge_unique_strings(
        _coerce_string_list(experience_contract.get("required_surfaces")),
        [
            "hero header",
            "primary workspace",
            "insight or result panel",
            "saved library and recent activity" if wants_collection_ui else "secondary supporting panel",
        ],
        must_have_surfaces,
    )
    required_states = _merge_unique_strings(
        _coerce_string_list(experience_contract.get("required_states")),
        ["loading", "empty", "error", "success"],
    )
    merged_proof_points = _merge_unique_strings(
        _coerce_string_list(experience_contract.get("proof_points")),
        [
            "domain-specific output framing",
            "clear feedback after the primary action",
            "visible saved history or proof of work" if wants_collection_ui else "clear supporting evidence or detail",
        ],
        proof_points,
    )
    interaction_style = experience_contract.get("interaction_style")
    if not isinstance(interaction_style, str) or not interaction_style.strip():
        interaction_style = design_system.get("visual_direction", "")
    experience_contract["required_surfaces"] = required_surfaces
    experience_contract["required_states"] = required_states
    experience_contract["proof_points"] = merged_proof_points
    experience_contract["interaction_style"] = interaction_style

    normalized["frontend_files"] = frontend_files
    normalized["backend_files"] = backend_files
    normalized["shared_constants"] = shared_constants
    normalized["design_system"] = design_system
    normalized["experience_contract"] = experience_contract
    normalized.setdefault("frontend_backend_contract", [])
    return normalized


def _slugify(value: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9\s-]", "", value).strip().lower()
    clean = re.sub(r"[\s_]+", "-", clean)
    clean = re.sub(r"-+", "-", clean)
    return clean or "vibedeploy-app"


def _coerce_string_list(value: object) -> list[str]:
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    if not isinstance(value, list):
        return []

    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        cleaned = item.strip()
        if cleaned:
            normalized.append(cleaned)
    return normalized


def _merge_unique_strings(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            key = item.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(item.strip())
    return merged
