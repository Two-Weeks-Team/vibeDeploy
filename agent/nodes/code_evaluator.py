import logging

from ..state import VibeDeployState

logger = logging.getLogger(__name__)

MAX_CODE_EVAL_ITERATIONS = 3
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
        return 80.0

    score = 0
    checks = 0
    for item in contract:
        checks += 1
        fe_file = item.get("frontend_file", "")
        be_file = item.get("backend_file", "")
        endpoint = item.get("calls", "")

        fe_exists = fe_file in (frontend_code or {})
        be_exists = be_file in (backend_code or {})

        if fe_exists and be_exists:
            fe_content = (frontend_code or {}).get(fe_file, "")
            be_content = (backend_code or {}).get(be_file, "")
            endpoint_path = endpoint.split(" ")[-1] if " " in endpoint else endpoint
            if endpoint_path in fe_content or endpoint_path.replace("/api", "") in fe_content:
                score += 1
            elif endpoint_path in be_content:
                score += 0.5
        elif fe_exists or be_exists:
            score += 0.3

    return (score / max(checks, 1)) * 100


def _check_runnability(frontend_code: dict | None, backend_code: dict | None) -> float:
    score = 0
    total = 0

    if backend_code:
        total += 3
        if "requirements.txt" in backend_code:
            score += 1
        if "main.py" in backend_code:
            score += 1
            main_content = backend_code.get("main.py", "")
            if "uvicorn" in main_content or "FastAPI" in main_content:
                score += 1

    if frontend_code:
        total += 3
        if "package.json" in frontend_code:
            score += 1
            pkg = frontend_code.get("package.json", "")
            if "next" in pkg:
                score += 1
        if any("layout" in f for f in frontend_code):
            score += 1

    return (score / max(total, 1)) * 100


def _build_fix_instructions(eval_result: dict) -> str:
    issues = []
    if eval_result.get("missing_frontend"):
        issues.append(f"Missing frontend files: {', '.join(eval_result['missing_frontend'])}")
    if eval_result.get("missing_backend"):
        issues.append(f"Missing backend files: {', '.join(eval_result['missing_backend'])}")
    if eval_result["consistency"] < 80:
        issues.append(
            "Frontend-backend API contract mismatch: verify endpoint paths match between api.ts and routes.py"
        )
    if eval_result["runnability"] < 80:
        issues.append("Missing critical files (requirements.txt, package.json, main.py, or layout.tsx)")
    return "; ".join(issues) if issues else "General quality improvement needed"


def route_code_eval(state: VibeDeployState) -> str:
    eval_result = state.get("code_eval_result", {})
    iteration = state.get("code_eval_iteration", 0)

    if eval_result.get("passed", False):
        logger.info("[CODE_EVAL] PASSED → deployer")
        return "deployer"

    if iteration >= MAX_CODE_EVAL_ITERATIONS:
        logger.info("[CODE_EVAL] Max iterations reached → deployer (best effort)")
        return "deployer"

    logger.info("[CODE_EVAL] FAILED → code_generator (retry)")
    return "code_generator"
