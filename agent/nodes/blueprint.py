import json
import logging
import re

from ..llm import MODEL_CONFIG, ainvoke_with_retry, content_to_str, get_llm, get_rate_limit_fallback_models
from ..state import VibeDeployState

logger = logging.getLogger(__name__)

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
  "frontend_backend_contract": [
    {"frontend_file": "src/lib/api.ts", "calls": "GET /api/items", "backend_file": "routes.py", "request_fields": [], "response_fields": ["items"]}
  ]
}

Rules:
- Frontend: Next.js 15 App Router. Required: package.json, src/app/layout.tsx, src/app/page.tsx, src/app/globals.css, src/lib/api.ts, 2-3 domain components.
- The frontend manifest must include a primary workflow shell, a result/list/detail component, and at least one explicit state or feedback component when relevant.
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
        fallback_models=get_rate_limit_fallback_models(doc_model),
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

    return {"blueprint": blueprint, "phase": "blueprint"}
