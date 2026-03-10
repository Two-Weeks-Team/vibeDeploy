import logging

from ..state import VibeDeployState

logger = logging.getLogger(__name__)

MAX_CODE_EVAL_ITERATIONS = 3
MAX_EMPTY_FRONTEND_RETRIES = 5
PASS_THRESHOLD = 85


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
    if not contract:
        fe = frontend_code or {}
        api_file = _find_file_fuzzy(fe, "api.ts")
        if api_file and ("fetch" in fe[api_file] or "axios" in fe[api_file]):
            return 85.0
        return 75.0 if fe else 50.0

    score = 0
    checks = 0
    fe = frontend_code or {}
    be = backend_code or {}
    all_fe_content = "\n".join(fe.values())
    all_be_content = "\n".join(be.values())

    for item in contract:
        checks += 1
        fe_file = item.get("frontend_file", "")
        be_file = item.get("backend_file", "")
        endpoint = item.get("calls", "")

        fe_match = _find_file_fuzzy(fe, fe_file)
        be_match = _find_file_fuzzy(be, be_file)

        endpoint_path = endpoint.split(" ")[-1] if " " in endpoint else endpoint
        endpoint_stem = endpoint_path.strip("/").replace("api/", "")

        if fe_match and be_match:
            fe_content = fe[fe_match]
            be_content = be[be_match]
            if endpoint_path in fe_content or endpoint_stem in fe_content:
                score += 1
            elif endpoint_path in be_content or endpoint_stem in be_content:
                score += 0.7
            else:
                score += 0.4
        elif fe_match or be_match:
            if endpoint_stem in all_fe_content or endpoint_stem in all_be_content:
                score += 0.6
            else:
                score += 0.3

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
        if _find_file_fuzzy(frontend_code, "api.ts"):
            score += 0.5
        if any("globals.css" in f for f in frontend_code):
            score += 0.5
        has_use_client = any(
            (frontend_code.get(f, "") or "").lstrip().startswith('"use client"')
            or (frontend_code.get(f, "") or "").lstrip().startswith("'use client'")
            for f in frontend_code
            if f.endswith(".tsx") and "layout" not in f
        )
        if has_use_client:
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
