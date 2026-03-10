import logging
import re

from ..state import VibeDeployState

logger = logging.getLogger(__name__)

MAX_CODE_EVAL_ITERATIONS = 3
MAX_EMPTY_FRONTEND_RETRIES = 5
PASS_THRESHOLD = 80


async def code_evaluator(state: VibeDeployState) -> dict:
    blueprint = state.get("blueprint", {})
    frontend_code = state.get("frontend_code", {})
    backend_code = state.get("backend_code", {})
    iteration = state.get("code_eval_iteration", 0) + 1

    expected_frontend = set(blueprint.get("frontend_files", {}).keys())
    expected_backend = set(blueprint.get("backend_files", {}).keys())
    actual_frontend = set(frontend_code.keys()) if frontend_code else set()
    actual_backend = set(backend_code.keys()) if backend_code else set()

    frontend_coverage = len(actual_frontend & expected_frontend) / max(len(expected_frontend), 1) * 100
    backend_coverage = len(actual_backend & expected_backend) / max(len(expected_backend), 1) * 100
    completeness = (frontend_coverage + backend_coverage) / 2

    consistency = _check_consistency(frontend_code, backend_code, blueprint)
    runnability = _check_runnability(frontend_code, backend_code)
    match_rate = round(completeness * 0.4 + consistency * 0.3 + runnability * 0.3, 1)

    missing_fe = list(expected_frontend - actual_frontend)
    missing_be = list(expected_backend - actual_backend)

    eval_result = {
        "match_rate": match_rate,
        "completeness": round(completeness, 1),
        "consistency": round(consistency, 1),
        "runnability": round(runnability, 1),
        "iteration": iteration,
        "passed": match_rate >= PASS_THRESHOLD,
        "missing_frontend": missing_fe,
        "missing_backend": missing_be,
    }

    if not eval_result["passed"] and iteration < MAX_CODE_EVAL_ITERATIONS:
        eval_result["fix_instructions"] = _build_fix_instructions(eval_result)

    logger.info(
        "[CODE_EVAL] Iteration %d: match_rate=%.1f%% (completeness=%.1f, consistency=%.1f, runnability=%.1f) → %s",
        iteration,
        match_rate,
        completeness,
        consistency,
        runnability,
        "PASS" if eval_result["passed"] else f"FAIL (iter {iteration}/{MAX_CODE_EVAL_ITERATIONS})",
    )

    return {
        "code_eval_result": eval_result,
        "code_eval_iteration": iteration,
        "match_rate": match_rate,
        "phase": "code_evaluation",
    }


def _check_consistency(frontend_code: dict | None, backend_code: dict | None, blueprint: dict) -> float:
    contract = blueprint.get("frontend_backend_contract", [])
    fe = frontend_code or {}
    be = backend_code or {}
    frontend_endpoints = _extract_frontend_endpoints(fe)
    backend_endpoints = _extract_backend_endpoints(be)

    if not contract:
        api_file = _find_file_fuzzy(fe, "api.ts")
        if frontend_endpoints and backend_endpoints:
            overlap = len(frontend_endpoints & backend_endpoints) / max(len(backend_endpoints), 1)
            return max(75.0, min(95.0, 75.0 + overlap * 20.0))
        if api_file and ("fetch" in fe[api_file] or "axios" in fe[api_file]):
            return 85.0
        return 75.0 if fe else 50.0

    score = 0
    checks = 0
    all_fe_content = "\n".join(fe.values())
    all_be_content = "\n".join(be.values())

    for item in contract:
        checks += 1
        fe_file = item.get("frontend_file", "")
        be_file = item.get("backend_file", "")
        expected_endpoints = _normalize_contract_calls(item.get("calls", ""))

        fe_match = _find_file_fuzzy(fe, fe_file)
        be_match = _find_file_fuzzy(be, be_file)
        item_score = 0.0

        if fe_match:
            item_score += 0.2
        if be_match:
            item_score += 0.2

        if expected_endpoints:
            fe_specific = _extract_frontend_endpoints({fe_match: fe[fe_match]}) if fe_match else set()
            be_specific = _extract_backend_endpoints({be_match: be[be_match]}) if be_match else set()
            fe_hit = bool(expected_endpoints & (fe_specific or frontend_endpoints))
            be_hit = bool(expected_endpoints & (be_specific or backend_endpoints))

            if fe_hit and be_hit:
                item_score = max(item_score, 1.0)
            elif fe_hit or be_hit:
                item_score = max(item_score, 0.75)
            elif any(endpoint in all_fe_content or endpoint in all_be_content for endpoint in expected_endpoints):
                item_score = max(item_score, 0.55 if fe_match and be_match else 0.4)
            elif fe_match and be_match:
                item_score = max(item_score, 0.45)
            elif fe_match or be_match:
                item_score = max(item_score, 0.3)
        else:
            if fe_match and be_match:
                item_score = max(item_score, 0.8)
            elif fe_match or be_match:
                item_score = max(item_score, 0.5)

        score += min(item_score, 1.0)

    if frontend_endpoints and backend_endpoints:
        overlap_bonus = len(frontend_endpoints & backend_endpoints) / max(len(backend_endpoints), 1)
        score += min(overlap_bonus, 0.5)
        checks += 0.5

    return (score / max(checks, 1)) * 100


def _find_file_fuzzy(files: dict, target: str) -> str | None:
    """Find a file in the dict, allowing for path prefix differences."""
    if not target or not files:
        return None
    if target in files:
        return target
    target_name = target.rsplit("/", 1)[-1]
    for key in files:
        if key.endswith(target_name) or key == target_name:
            return key
    return None


def _check_runnability(frontend_code: dict | None, backend_code: dict | None) -> float:
    score = 0
    total = 0

    if backend_code:
        total += 5
        if "requirements.txt" in backend_code:
            score += 1
        if "main.py" in backend_code:
            score += 1
            main_content = backend_code.get("main.py", "")
            if "FastAPI" in main_content:
                score += 1
            if "uvicorn" in main_content or "__name__" in main_content:
                score += 0.5
        if "routes.py" in backend_code:
            score += 0.5
        if "ai_service.py" in backend_code:
            score += 0.5
        if any("import" in (backend_code.get(f, "") or "") for f in backend_code if f.endswith(".py")):
            score += 0.5

    if frontend_code:
        total += 5
        if "package.json" in frontend_code:
            score += 1
            pkg = frontend_code.get("package.json", "")
            if "next" in pkg:
                score += 1
        if any("layout" in f for f in frontend_code):
            score += 1
        if any("page" in f for f in frontend_code):
            score += 0.5
        has_api_client = _find_file_fuzzy(frontend_code, "api.ts") or any(
            "fetch(" in (content or "") or "axios." in (content or "") for content in frontend_code.values()
        )
        if has_api_client:
            score += 0.5
        if any("globals.css" in f for f in frontend_code):
            score += 0.5
        needs_use_client = any(
            re.search(r"\b(useState|useEffect|useRef|useReducer|useTransition|onClick=|onSubmit=|onChange=)\b", content)
            for f, content in frontend_code.items()
            if f.endswith(".tsx") and "layout" not in f
        )
        has_use_client = any(
            (frontend_code.get(f, "") or "").lstrip().startswith('"use client"')
            or (frontend_code.get(f, "") or "").lstrip().startswith("'use client'")
            for f in frontend_code
            if f.endswith(".tsx") and "layout" not in f
        )
        if has_use_client or not needs_use_client:
            score += 0.5

    return (score / max(total, 1)) * 100


def _build_fix_instructions(eval_result: dict) -> str:
    issues = []
    if eval_result.get("missing_frontend"):
        issues.append(f"MUST generate these frontend files: {', '.join(eval_result['missing_frontend'])}")
    if eval_result.get("missing_backend"):
        issues.append(f"MUST generate these backend files: {', '.join(eval_result['missing_backend'])}")
    if eval_result["consistency"] < 80:
        issues.append(
            "Frontend-backend API consistency is low. "
            "Ensure src/lib/api.ts contains fetch calls to EXACTLY the same endpoint paths "
            "defined in routes.py (e.g. '/api/items'). Every backend route must be callable from frontend."
        )
    if eval_result["runnability"] < 80:
        issues.append(
            "Runnability check failed. Ensure: "
            "backend has requirements.txt + main.py (with FastAPI + uvicorn) + routes.py + ai_service.py; "
            "frontend has package.json (with next) + layout.tsx + page.tsx + globals.css + api.ts; "
            'interactive .tsx files must start with "use client".'
        )
    return "\n".join(issues) if issues else "General quality improvement needed"


def _normalize_contract_calls(calls: object) -> set[str]:
    if isinstance(calls, str):
        values = [calls]
    elif isinstance(calls, list):
        values = [value for value in calls if isinstance(value, str)]
    else:
        return set()

    normalized = set()
    for value in values:
        endpoint = _normalize_endpoint_path(value)
        if endpoint:
            normalized.add(endpoint)
    return normalized


def _normalize_endpoint_path(value: str) -> str:
    raw = value.strip()
    if not raw:
        return ""

    parts = raw.split(" ", 1)
    if len(parts) == 2 and parts[0].upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
        raw = parts[1]

    raw = re.sub(r"^https?://[^/]+", "", raw)
    raw = raw.split("?", 1)[0].split("#", 1)[0].strip()

    api_index = raw.find("/api/")
    if api_index >= 0:
        raw = raw[api_index:]

    if not raw.startswith("/"):
        return ""

    raw = re.sub(r"/+", "/", raw).rstrip("/")
    if raw == "/api":
        return "root"

    if raw.startswith("/api/"):
        raw = raw[len("/api/") :]
    else:
        raw = raw.lstrip("/")

    return raw.strip("/") or "root"


def _extract_frontend_endpoints(files: dict[str, str]) -> set[str]:
    endpoints: set[str] = set()
    for content in files.values():
        for raw in re.findall(r"['\"`](/api/[^'\"`?#)]+)", content):
            normalized = _normalize_endpoint_path(raw)
            if normalized:
                endpoints.add(normalized)
    return endpoints


def _extract_backend_endpoints(files: dict[str, str]) -> set[str]:
    endpoints: set[str] = set()
    route_pattern = re.compile(r"@\w+\.(?:get|post|put|patch|delete)\(\s*['\"]([^'\"]+)['\"]")
    prefix_pattern = re.compile(r"APIRouter\([^)]*prefix\s*=\s*['\"]([^'\"]+)['\"]")

    for content in files.values():
        prefixes = prefix_pattern.findall(content)
        prefix = prefixes[0] if prefixes else ""

        for route in route_pattern.findall(content):
            combined = route
            if prefix and route.startswith("/") and not route.startswith("/api/"):
                combined = f"{prefix.rstrip('/')}/{route.lstrip('/')}"
            normalized = _normalize_endpoint_path(combined)
            if normalized:
                endpoints.add(normalized)

        for raw in re.findall(r"['\"](/api/[^'\"]+)['\"]", content):
            normalized = _normalize_endpoint_path(raw)
            if normalized:
                endpoints.add(normalized)
    return endpoints


def route_code_eval(state: VibeDeployState) -> str:
    eval_result = state.get("code_eval_result", {})
    iteration = state.get("code_eval_iteration", 0)
    blueprint = state.get("blueprint", {}) or {}
    frontend_code = state.get("frontend_code", {}) or {}

    if eval_result.get("passed", False):
        logger.info("[CODE_EVAL] PASSED → deployer")
        return "deployer"

    expected_frontend = blueprint.get("frontend_files", {})
    if not frontend_code and expected_frontend:
        if iteration < MAX_EMPTY_FRONTEND_RETRIES:
            logger.warning(
                "[CODE_EVAL] 0 frontend files (expected %d) → force retry (iter %d/%d)",
                len(expected_frontend),
                iteration,
                MAX_EMPTY_FRONTEND_RETRIES,
            )
            return "code_generator"
        logger.error(
            "[CODE_EVAL] Still 0 frontend after %d iters → deployer (backend-only)",
            iteration,
        )
        return "deployer"

    if iteration >= MAX_CODE_EVAL_ITERATIONS:
        logger.info("[CODE_EVAL] Max iterations reached → deployer (best effort)")
        return "deployer"

    logger.info("[CODE_EVAL] FAILED → code_generator (retry)")
    return "code_generator"
