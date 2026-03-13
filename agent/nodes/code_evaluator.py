import json
import logging
import re

from ..state import VibeDeployState
from .task_contracts import build_repair_tasks_from_eval, build_task_distribution

logger = logging.getLogger(__name__)
_HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
_EXPERIENCE_STOPWORDS = {
    "a",
    "an",
    "and",
    "or",
    "the",
    "of",
    "for",
    "with",
    "panel",
    "surface",
    "section",
    "card",
    "screen",
    "state",
    "primary",
    "secondary",
    "supporting",
    "visible",
    "clear",
    "domain",
    "specific",
}

MAX_CODE_EVAL_ITERATIONS = 5
MAX_EMPTY_FRONTEND_RETRIES = 5
MAX_EMPTY_BACKEND_RETRIES = 5
PASS_THRESHOLD = 80
MIN_CONSISTENCY_TO_PASS = 75
MIN_RUNNABILITY_TO_PASS = 85
MIN_EXPERIENCE_TO_PASS = 70
_FALLBACK_MARKER_FILES = {".vibedeploy-fallback-frontend.json", ".vibedeploy-fallback-backend.json"}
_GENERIC_SCAFFOLD_TERMS = (
    "hero header",
    "primary workspace",
    "secondary supporting panel",
    "saved library and recent activity",
    "feature lanes",
    "readiness score",
)
_FABRICATED_PROOF_TERMS = (
    "professionally authored",
    "95% test coverage",
    "mit license",
    "pilot users report",
    "beta feedback",
    "no third-party ai calls",
)


async def code_evaluator(state: VibeDeployState) -> dict:
    blueprint = state.get("blueprint", {})
    frontend_code = state.get("frontend_code", {})
    backend_code = state.get("backend_code", {})
    flagship_contract = state.get("flagship_contract") if isinstance(state.get("flagship_contract"), dict) else {}
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
    experience = _check_experience(frontend_code, blueprint)
    artifact_fidelity = _check_flagship_artifact_fidelity(frontend_code, backend_code, flagship_contract)
    match_rate = round(completeness * 0.3 + consistency * 0.25 + runnability * 0.2 + experience * 0.25, 1)

    missing_fe = list(expected_frontend - actual_frontend)
    missing_be = list(expected_backend - actual_backend)
    blockers = _collect_quality_blockers(frontend_code, backend_code, blueprint)
    blockers.extend(_artifact_fidelity_blockers(flagship_contract, artifact_fidelity))
    flagship_fallback_accepted = _allow_flagship_fallback_pass(
        flagship_contract,
        blockers,
        completeness,
        consistency,
        runnability,
        experience,
        artifact_fidelity,
    )
    if flagship_fallback_accepted:
        blockers = []
    deployment_blocked = bool(blockers)

    eval_result = {
        "match_rate": match_rate,
        "completeness": round(completeness, 1),
        "consistency": round(consistency, 1),
        "runnability": round(runnability, 1),
        "experience": round(experience, 1),
        "artifact_fidelity": artifact_fidelity,
        "flagship_fallback_accepted": flagship_fallback_accepted,
        "iteration": iteration,
        "passed": (
            (match_rate >= PASS_THRESHOLD and consistency >= MIN_CONSISTENCY_TO_PASS) or flagship_fallback_accepted
        )
        and (
            runnability >= MIN_RUNNABILITY_TO_PASS
            and experience >= MIN_EXPERIENCE_TO_PASS
            and not missing_fe
            and not missing_be
            and not blockers
        ),
        "missing_frontend": missing_fe,
        "missing_backend": missing_be,
        "blockers": blockers,
        "deployment_blocked": deployment_blocked,
    }

    if not eval_result["passed"] and iteration < MAX_CODE_EVAL_ITERATIONS:
        eval_result["fix_instructions"] = _build_fix_instructions(eval_result, blueprint)

    repair_tasks = build_repair_tasks_from_eval(eval_result)

    logger.info(
        "[CODE_EVAL] Iteration %d: match_rate=%.1f%% (completeness=%.1f, consistency=%.1f, runnability=%.1f, experience=%.1f) → %s",
        iteration,
        match_rate,
        completeness,
        consistency,
        runnability,
        experience,
        "PASS" if eval_result["passed"] else f"FAIL (iter {iteration}/{MAX_CODE_EVAL_ITERATIONS})",
    )

    return {
        "code_eval_result": eval_result,
        "code_eval_iteration": iteration,
        "match_rate": match_rate,
        "repair_tasks": repair_tasks,
        "task_distribution": build_task_distribution((state.get("execution_tasks") or []) + repair_tasks),
        "phase": "code_evaluation",
    }


def _check_consistency(frontend_code: dict | None, backend_code: dict | None, blueprint: dict) -> float:
    contract = blueprint.get("frontend_backend_contract", [])
    fe = frontend_code or {}
    be = backend_code or {}
    frontend_specs = _extract_frontend_endpoint_specs(fe)
    backend_specs = _extract_backend_endpoint_specs(be)
    frontend_endpoints = set(frontend_specs)
    backend_endpoints = set(backend_specs)

    if not contract:
        api_file = _find_file_fuzzy(fe, "api.ts")
        if frontend_endpoints and backend_endpoints:
            overlap = len(frontend_endpoints & backend_endpoints) / max(len(frontend_endpoints | backend_endpoints), 1)
            penalty = len(frontend_endpoints - backend_endpoints) / max(len(frontend_endpoints), 1) + len(
                backend_endpoints - frontend_endpoints
            ) / max(len(backend_endpoints), 1)
            return max(65.0, min(95.0, 72.0 + overlap * 28.0 - penalty * 8.0))
        if api_file and ("fetch" in fe[api_file] or "axios" in fe[api_file]):
            return 85.0
        return 75.0 if fe else 50.0

    item_scores = []

    for item in contract:
        fe_file = item.get("frontend_file", "")
        be_file = item.get("backend_file", "")
        call_specs = _normalize_contract_call_specs(item.get("calls", ""))
        expected_endpoints = {spec["endpoint"] for spec in call_specs}
        expected_request_fields = set(_coerce_string_list(item.get("request_fields")))
        expected_response_fields = set(_coerce_string_list(item.get("response_fields")))

        fe_match = _find_file_fuzzy(fe, fe_file)
        be_match = _find_file_fuzzy(be, be_file)
        item_score = 0.0
        item_weight = 0.0

        scoped_frontend_specs = (
            _extract_frontend_endpoint_specs({fe_match: fe[fe_match]})
            if fe_match and fe_match in fe
            else frontend_specs
        )
        scoped_backend_specs = (
            _extract_backend_endpoint_specs({be_match: be[be_match]}) if be_match and be_match in be else backend_specs
        )

        if fe_file:
            item_weight += 0.1
            if fe_match:
                item_score += 0.1
        if be_file:
            item_weight += 0.1
            if be_match:
                item_score += 0.1

        if expected_endpoints:
            item_weight += 0.4
            item_score += 0.2 * _match_endpoint_specs(scoped_frontend_specs, call_specs)
            item_score += 0.2 * _match_endpoint_specs(scoped_backend_specs, call_specs)

            item_weight += 0.1
            item_score += 0.05 * _match_method_specs(scoped_frontend_specs, call_specs)
            item_score += 0.05 * _match_method_specs(scoped_backend_specs, call_specs)
        else:
            item_weight += 0.2
            item_score += 0.1 if fe_match else 0.0
            item_score += 0.1 if be_match else 0.0

        relevant_frontend_specs = (
            _filter_specs_by_endpoints(scoped_frontend_specs, expected_endpoints) or scoped_frontend_specs
        )
        relevant_backend_specs = (
            _filter_specs_by_endpoints(scoped_backend_specs, expected_endpoints) or scoped_backend_specs
        )

        if expected_request_fields:
            item_weight += 0.2
            item_score += 0.1 * _field_overlap(
                expected_request_fields, _collect_spec_fields(relevant_frontend_specs, "request_fields")
            )
            item_score += 0.1 * _field_overlap(
                expected_request_fields, _collect_spec_fields(relevant_backend_specs, "request_fields")
            )

        if expected_response_fields:
            item_weight += 0.2
            item_score += 0.1 * _field_overlap(
                expected_response_fields, _collect_spec_fields(relevant_frontend_specs, "response_fields")
            )
            item_score += 0.1 * _field_overlap(
                expected_response_fields, _collect_spec_fields(relevant_backend_specs, "response_fields")
            )

        item_scores.append(item_score / max(item_weight, 1e-6))

    contract_score = sum(item_scores) / max(len(item_scores), 1) * 100

    if frontend_endpoints or backend_endpoints:
        overlap = len(frontend_endpoints & backend_endpoints) / max(len(frontend_endpoints | backend_endpoints), 1)
        contract_score = contract_score * 0.85 + overlap * 15.0
        contract_score -= len(frontend_endpoints - backend_endpoints) / max(len(frontend_endpoints), 1) * 10.0
        contract_score -= len(backend_endpoints - frontend_endpoints) / max(len(backend_endpoints), 1) * 10.0

    return max(0.0, min(100.0, contract_score))


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
        total += 6
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
        if not _has_unawaited_async_helper_calls(backend_code):
            score += 1.0

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

    runnability = (score / max(total, 1)) * 100
    if backend_code and _has_unawaited_async_helper_calls(backend_code):
        runnability = max(0.0, runnability - 15.0)
    return runnability


def _check_experience(frontend_code: dict | None, blueprint: dict | None) -> float:
    fe = frontend_code or {}
    if not fe:
        return 0.0

    component_files = [path for path in fe if path.startswith("src/components/") and path.endswith(".tsx")]
    all_content = "\n".join((content or "") for content in fe.values())
    page_content = "\n".join(
        (content or "") for path, content in fe.items() if path.endswith("page.tsx") or path.endswith("page.jsx")
    )
    blueprint_data = blueprint or {}
    blueprint_text = json.dumps(blueprint_data, ensure_ascii=False).lower()
    experience_contract = blueprint_data.get("experience_contract", {}) if isinstance(blueprint_data, dict) else {}
    required_surfaces = _coerce_string_list(experience_contract.get("required_surfaces"))
    required_states = _coerce_string_list(experience_contract.get("required_states"))
    proof_points = _coerce_string_list(experience_contract.get("proof_points"))
    collection_required = any(
        token in blueprint_text for token in ("collection", "library", "history", "favorite", "bookmark", "dashboard")
    )

    score = 0.0
    total = 6.0

    if len(component_files) >= 4:
        score += 1.0
    elif len(component_files) >= 3:
        score += 0.8
    elif len(component_files) >= 2:
        score += 0.4

    page_component_refs = re.findall(r"<([A-Z][A-Za-z0-9_]*)", page_content)
    if len(set(page_component_refs)) >= 3:
        score += 1.0
    elif len(set(page_component_refs)) >= 2:
        score += 0.6

    if required_states:
        state_hits = sum(1 for state in required_states if _phrase_present(state, all_content.lower()))
        score += state_hits / max(len(required_states), 1)
    else:
        state_score = 0.0
        has_use_state = bool(re.search(r"useState\s*[<(]", all_content))
        has_conditional_render = bool(re.search(r"\{[\w.]+\s*&&\s*[(<]|\?\s*[(<].*:\s*[(<]", all_content))
        state_keywords = ("loading", "empty", "error", "no items", "no results", "processing")
        jsx_state_pattern = any(
            re.search(rf"(?:{{|>)\s*[^/]*{re.escape(token)}", all_content.lower()) for token in state_keywords
        )
        if has_use_state:
            state_score += 0.4
        if has_conditional_render:
            state_score += 0.3
        if jsx_state_pattern:
            state_score += 0.3
        score += state_score

    if "throwApiError" in all_content or "Promise.allSettled" in all_content:
        score += 1.0

    if not required_surfaces:
        required_surfaces = [
            "hero header",
            "primary workspace",
            "saved library and recent activity" if collection_required else "insight panel",
        ]
    surface_hits = sum(1 for surface in required_surfaces if _phrase_present(surface, all_content.lower()))
    score += surface_hits / max(len(required_surfaces), 1)

    if proof_points:
        proof_hits = sum(1 for point in proof_points if _phrase_present(point, all_content.lower()))
        score += proof_hits / max(len(proof_points), 1)
    elif any(
        token in all_content.lower()
        for token in ("saved", "history", "library", "bookmark", "summary", "insight", "result", "metric")
    ):
        score += 1.0
    else:
        score += 0.3

    return (score / total) * 100


def _collect_quality_blockers(
    frontend_code: dict | None, backend_code: dict | None, blueprint: dict | None
) -> list[str]:
    blockers: list[str] = []
    fe = frontend_code or {}
    be = backend_code or {}
    all_frontend = "\n".join(str(content or "") for content in fe.values()).lower()
    blueprint_text = json.dumps(blueprint or {}, ensure_ascii=False).lower()

    if _FALLBACK_MARKER_FILES & set(fe) or _FALLBACK_MARKER_FILES & set(be):
        blockers.append("deterministic fallback scaffold detected")

    if _has_raw_object_dump(all_frontend):
        blockers.append("raw object or JSON dump rendered into the UI")

    taxonomy_hits = sum(1 for token in _GENERIC_SCAFFOLD_TERMS if token in all_frontend)
    if taxonomy_hits >= 3:
        blockers.append("generic repeated scaffold taxonomy detected")

    if any(term in all_frontend for term in _FABRICATED_PROOF_TERMS):
        blockers.append("fabricated proof or testimonial copy detected")

    if _requires_persistence(blueprint_text, all_frontend) and _missing_real_persistence(
        frontend_code or {}, backend_code or {}
    ):
        blockers.append("saved/history experience promised without a real persistence flow")

    return blockers


def _check_structural_presence(item: str, frontend_code: dict | None, backend_code: dict | None) -> bool:
    tokens = [t for t in re.findall(r"[a-z0-9]+", item.lower()) if len(t) > 2 and t not in _EXPERIENCE_STOPWORDS]
    if not tokens:
        return False

    all_files = {**(frontend_code or {}), **(backend_code or {})}
    for _path, content in all_files.items():
        if not content:
            continue
        stripped = re.sub(r"//.*$|/\*.*?\*/|#.*$", "", content, flags=re.MULTILINE | re.DOTALL)
        stripped = re.sub(r'""".*?"""|\'\'\'.*?\'\'\'', "", stripped, flags=re.DOTALL)
        stripped_lower = stripped.lower()

        token_alt = "|".join(tokens)
        structural_patterns = [
            rf"(?:const|let|var|def|class)\s+\w*{token_alt}\w*",
            rf"<\w*{token_alt}\w*",
            rf"\w*{token_alt}\w*\s*\(",
            rf"\.\w*{token_alt}\w*",
            rf"(?:import|from)\s+.*{token_alt}",
        ]
        for pattern in structural_patterns:
            if re.search(pattern, stripped_lower):
                return True
    return False


def _check_flagship_artifact_fidelity(
    frontend_code: dict | None,
    backend_code: dict | None,
    flagship_contract: dict | None,
) -> dict:
    contract = flagship_contract or {}
    required_objects = _coerce_string_list(contract.get("required_objects"))
    required_results = _coerce_string_list(contract.get("required_results"))
    acceptance_checks = _coerce_string_list(contract.get("acceptance_checks"))
    haystack = "\n".join(list((frontend_code or {}).values()) + list((backend_code or {}).values())).lower()

    phrase_object_hits = [item for item in required_objects if _phrase_present(item, haystack)]
    phrase_result_hits = [item for item in required_results if _phrase_present(item, haystack)]
    phrase_acceptance_hits = [item for item in acceptance_checks if _phrase_present(item, haystack)]

    structural_object_hits = [
        item for item in required_objects if _check_structural_presence(item, frontend_code, backend_code)
    ]
    structural_result_hits = [
        item for item in required_results if _check_structural_presence(item, frontend_code, backend_code)
    ]
    structural_acceptance_hits = [
        item for item in acceptance_checks if _check_structural_presence(item, frontend_code, backend_code)
    ]

    def blended_score(phrase_hits, structural_hits, total_items):
        if not total_items:
            return 100.0
        phrase_rate = len(phrase_hits) / max(len(total_items), 1)
        structural_rate = len(structural_hits) / max(len(total_items), 1)
        return (structural_rate * 0.6 + phrase_rate * 0.4) * 100

    object_score = blended_score(phrase_object_hits, structural_object_hits, required_objects)
    result_score = blended_score(phrase_result_hits, structural_result_hits, required_results)
    acceptance_score = blended_score(phrase_acceptance_hits, structural_acceptance_hits, acceptance_checks)

    object_hits = list(set(phrase_object_hits) | set(structural_object_hits))
    result_hits = list(set(phrase_result_hits) | set(structural_result_hits))
    acceptance_hits = list(set(phrase_acceptance_hits) | set(structural_acceptance_hits))

    return {
        "score": round(object_score * 0.4 + result_score * 0.4 + acceptance_score * 0.2, 1),
        "required_object_hits": object_hits,
        "required_result_hits": result_hits,
        "acceptance_hits": acceptance_hits,
        "required_object_misses": [item for item in required_objects if item not in object_hits],
        "required_result_misses": [item for item in required_results if item not in result_hits],
        "acceptance_misses": [item for item in acceptance_checks if item not in acceptance_hits],
    }


def _artifact_fidelity_blockers(flagship_contract: dict | None, fidelity: dict | None) -> list[str]:
    contract = flagship_contract or {}
    if not contract:
        return []

    fidelity = fidelity or {}
    object_count = len(_coerce_string_list(contract.get("required_objects")))
    result_count = len(_coerce_string_list(contract.get("required_results")))
    object_misses = fidelity.get("required_object_misses") or []
    result_misses = fidelity.get("required_result_misses") or []
    score = float(fidelity.get("score", 0) or 0)
    blockers: list[str] = []

    if score < 60:
        blockers.append("flagship artifact fidelity too low")
    if object_count and len(object_misses) >= max(2, object_count - 1):
        blockers.append("flagship required objects missing from generated product")
    if result_count and len(result_misses) >= max(2, result_count - 1):
        blockers.append("flagship required outputs missing from generated product")
    return blockers


def _allow_flagship_fallback_pass(
    flagship_contract: dict | None,
    blockers: list[str],
    completeness: float,
    consistency: float,
    runnability: float,
    experience: float,
    artifact_fidelity: dict | None,
) -> bool:
    if not flagship_contract:
        return False
    if blockers != ["deterministic fallback scaffold detected"]:
        return False
    fidelity_score = float((artifact_fidelity or {}).get("score", 0) or 0)
    return (
        completeness >= 95
        and consistency >= 50
        and runnability >= MIN_RUNNABILITY_TO_PASS
        and experience >= 90
        and fidelity_score >= 80
    )


def _has_raw_object_dump(all_frontend: str) -> bool:
    patterns = (
        r"\{'name':\s*'[^']+'",
        r'\{"name":\s*"[^"]+"',
        r"'\w+':\s*'[^']+'",
    )
    return any(re.search(pattern, all_frontend) for pattern in patterns)


def _requires_persistence(blueprint_text: str, frontend_text: str) -> bool:
    haystack = f"{blueprint_text}\n{frontend_text}"
    return any(token in haystack for token in ("saved", "history", "library", "recent activity", "bookmark"))


def _missing_real_persistence(frontend_code: dict[str, str], backend_code: dict[str, str]) -> bool:
    frontend_text = "\n".join(frontend_code.values()).lower()
    backend_text = "\n".join(backend_code.values()).lower()

    frontend_has_storage = any(token in frontend_text for token in ("localstorage", "sessionstorage", "indexeddb"))
    backend_has_storage = any(
        token in backend_text
        for token in ("sqlite", "sqlalchemy", "database", "save_", "create_", "insert ", "list_", "get_")
    )
    frontend_has_save_call = bool(re.search(r"/api/(save|history|library|favorites?|bookmarks?)", frontend_text))
    backend_has_save_route = bool(
        re.search(r"@router\.(post|get)\(\"/((api/)?(save|history|library|favorites?|bookmarks?))", backend_text)
    )

    return not (frontend_has_storage or backend_has_storage or (frontend_has_save_call and backend_has_save_route))


def _build_fix_instructions(eval_result: dict, blueprint: dict | None = None) -> str:
    issues = []
    iteration = eval_result.get("iteration", 0)
    if iteration >= 3:
        issues.insert(
            0,
            f"CRITICAL: This is attempt {iteration}/{MAX_CODE_EVAL_ITERATIONS}. "
            "Previous fixes were insufficient. Focus ONLY on the specific failures listed below. "
            "Do not regenerate working files. Fix ONLY what is broken.",
        )
    experience_contract = blueprint.get("experience_contract", {}) if isinstance(blueprint, dict) else {}
    required_surfaces = _coerce_string_list(experience_contract.get("required_surfaces"))
    proof_points = _coerce_string_list(experience_contract.get("proof_points"))
    if eval_result.get("missing_frontend"):
        issues.append(f"MUST generate these frontend files: {', '.join(eval_result['missing_frontend'])}")
    if eval_result.get("missing_backend"):
        issues.append(f"MUST generate these backend files: {', '.join(eval_result['missing_backend'])}")
    if eval_result["consistency"] < 80:
        issues.append(
            "Frontend-backend API consistency is low. "
            "Ensure src/lib/api.ts contains fetch calls to EXACTLY the same endpoint paths "
            "defined in routes.py (e.g. '/api/items'). Match HTTP methods plus request and response field names from the frontend_backend_contract."
        )
    if eval_result["runnability"] < 80:
        issues.append(
            "Runnability check failed. Ensure: "
            "backend has requirements.txt + main.py (with FastAPI + uvicorn) + routes.py + ai_service.py; "
            "frontend has package.json (with next) + layout.tsx + page.tsx + globals.css + api.ts; "
            'interactive .tsx files must start with "use client".'
        )
        issues.append(
            "If routes.py calls async helpers from ai_service.py, route handlers must be async and use await."
        )
    if eval_result.get("experience", 100) < 75:
        issues.append(
            "Experience completeness is low. Generate a multi-section UI with a primary workspace, "
            "secondary insight/history/library surfaces, explicit loading/error/empty states, and resilient API error handling."
        )
        if required_surfaces:
            issues.append(f"Required experience surfaces: {', '.join(required_surfaces)}")
        if proof_points:
            issues.append(f"Required proof points: {', '.join(proof_points)}")
    if eval_result.get("blockers"):
        issues.append(f"Remove these deployment blockers: {', '.join(eval_result['blockers'])}")
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


def _normalize_contract_call_specs(calls: object) -> list[dict[str, str | None]]:
    if isinstance(calls, str):
        values = [calls]
    elif isinstance(calls, list):
        values = [value for value in calls if isinstance(value, str)]
    else:
        return []

    normalized = []
    for value in values:
        raw = value.strip()
        method = None
        parts = raw.split(" ", 1)
        if len(parts) == 2 and parts[0].upper() in _HTTP_METHODS:
            method = parts[0].upper()
            raw = parts[1]
        endpoint = _normalize_endpoint_path(raw)
        if endpoint:
            normalized.append({"method": method, "endpoint": endpoint})
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
    endpoints = set(_extract_frontend_endpoint_specs(files))
    if endpoints:
        return endpoints

    raw_endpoints: set[str] = set()
    for content in files.values():
        for raw in re.findall(r"['\"`](/api/[^'\"`?#)]+)", content):
            normalized = _normalize_endpoint_path(raw)
            if normalized:
                raw_endpoints.add(normalized)
    return raw_endpoints


def _extract_backend_endpoints(files: dict[str, str]) -> set[str]:
    endpoints = set(_extract_backend_endpoint_specs(files))
    if endpoints:
        return endpoints

    raw_endpoints: set[str] = set()
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
                raw_endpoints.add(normalized)

        for raw in re.findall(r"['\"](/api/[^'\"]+)['\"]", content):
            normalized = _normalize_endpoint_path(raw)
            if normalized:
                raw_endpoints.add(normalized)
    return raw_endpoints


def _extract_frontend_endpoint_specs(files: dict[str, str]) -> dict[str, dict[str, set[str]]]:
    specs: dict[str, dict[str, set[str]]] = {}

    for content in files.values():
        api_base_match = re.search(r'API_BASE\s*=\s*["\']([^"\']+)["\']', content)
        api_base = api_base_match.group(1) if api_base_match else "/api"
        chunks = re.split(
            r"(?=export\s+(?:default\s+)?async\s+function|async\s+function|export\s+function|function\s+\w+)", content
        )
        if not chunks:
            chunks = [content]

        for chunk in chunks:
            fetch_chunks = re.split(r"(?=fetch\()", chunk)
            if not fetch_chunks:
                fetch_chunks = [chunk]

            for fetch_chunk in fetch_chunks:
                raw_endpoints = set(re.findall(r"['\"`](/api/[^'\"`?#)]+)", fetch_chunk))
                for suffix in re.findall(r"API_BASE\}?(/[^'\"`?#)]+)", fetch_chunk):
                    raw_endpoints.add(f"{api_base.rstrip('/')}{suffix}")

                if not raw_endpoints:
                    continue

                method_match = re.search(r'method\s*:\s*["\'](\w+)["\']', fetch_chunk)
                method = method_match.group(1).upper() if method_match else "GET"
                request_fields = set()
                body_match = re.search(r"JSON\.stringify\(\s*\{([\s\S]*?)\}\s*\)", fetch_chunk)
                if body_match:
                    request_fields = _extract_object_keys(body_match.group(1))

                response_fields = _extract_frontend_response_fields(fetch_chunk)

                for raw in raw_endpoints:
                    endpoint = _normalize_endpoint_path(raw)
                    if not endpoint:
                        continue
                    spec = specs.setdefault(
                        endpoint,
                        {"methods": set(), "request_fields": set(), "response_fields": set()},
                    )
                    spec["methods"].add(method)
                    spec["request_fields"].update(request_fields)
                    spec["response_fields"].update(response_fields)

    return specs


def _extract_backend_endpoint_specs(files: dict[str, str]) -> dict[str, dict[str, set[str]]]:
    specs: dict[str, dict[str, set[str]]] = {}
    model_fields: dict[str, set[str]] = {}

    for content in files.values():
        for class_name, body in re.findall(r"class\s+(\w+)\(BaseModel\):\n((?:\s+.+\n)+)", content):
            fields = {field for field in re.findall(r"^\s+(\w+)\s*:", body, flags=re.MULTILINE)}
            if fields:
                model_fields[class_name] = fields

    route_pattern = re.compile(
        r'@router\.(?P<method>get|post|put|patch|delete)\(\s*[\'"](?P<path>[^\'"]+)[\'"](?P<args>[^)]*)\)\s*\n(?P<signature>(?:async\s+)?def[^\n]+)(?:\n(?P<body>[\s\S]*?))?(?=@router\.|\Z)',
        re.MULTILINE,
    )

    for content in files.values():
        prefix_match = re.search(r'APIRouter\([^)]*prefix\s*=\s*[\'"]([^\'"]+)[\'"]', content)
        prefix = prefix_match.group(1) if prefix_match else ""

        for match in route_pattern.finditer(content):
            method = match.group("method").upper()
            path = match.group("path")
            args = match.group("args")
            signature = match.group("signature")
            body = match.group("body") or ""
            combined = path
            if prefix and path.startswith("/") and not path.startswith("/api/"):
                combined = f"{prefix.rstrip('/')}/{path.lstrip('/')}"
            endpoint = _normalize_endpoint_path(combined)
            if not endpoint:
                continue

            request_fields: set[str] = set()
            response_fields: set[str] = set()

            request_model_match = re.search(r":\s*(\w+)", signature)
            if request_model_match:
                request_fields.update(model_fields.get(request_model_match.group(1), set()))

            response_model_match = re.search(r"response_model\s*=\s*(\w+)", args)
            if response_model_match:
                response_fields.update(model_fields.get(response_model_match.group(1), set()))

            response_fields.update(re.findall(r'return\s+\{\s*"([^"]+)"\s*:', body))
            constructor_match = re.search(r"return\s+\w+\(([\s\S]*?)\)\s*$", body.strip(), flags=re.MULTILINE)
            if constructor_match:
                response_fields.update(re.findall(r"(\w+)\s*=", constructor_match.group(1)))

            spec = specs.setdefault(
                endpoint,
                {"methods": set(), "request_fields": set(), "response_fields": set()},
            )
            spec["methods"].add(method)
            spec["request_fields"].update(request_fields)
            spec["response_fields"].update({field for field in response_fields if isinstance(field, str) and field})

    return specs


def _extract_object_keys(body: str) -> set[str]:
    fields: set[str] = set()
    for part in body.split(","):
        token = part.strip()
        if not token:
            continue
        key_match = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s*:", token)
        if key_match:
            fields.add(key_match.group(1))
            continue
        bare_match = re.match(r"([A-Za-z_][A-Za-z0-9_]*)$", token)
        if bare_match:
            fields.add(bare_match.group(1))
    return fields


def _extract_frontend_response_fields(chunk: str) -> set[str]:
    response_fields = set(re.findall(r"return\s+\(\s*await\s+\w+\.json\(\)\s*\)\.(\w+)", chunk))
    for data_var in re.findall(r"const\s+(\w+)\s*=\s*await\s+\w+\.json\(\)", chunk):
        response_fields.update(re.findall(rf"return\s+{data_var}\.(\w+)", chunk))
    return response_fields


def _filter_specs_by_endpoints(
    specs: dict[str, dict[str, set[str]]], endpoints: set[str]
) -> dict[str, dict[str, set[str]]]:
    if not endpoints:
        return specs
    return {endpoint: spec for endpoint, spec in specs.items() if endpoint in endpoints}


def _collect_spec_fields(specs: dict[str, dict[str, set[str]]], field_name: str) -> set[str]:
    values: set[str] = set()
    for spec in specs.values():
        values.update(spec.get(field_name, set()))
    return values


def _match_endpoint_specs(specs: dict[str, dict[str, set[str]]], call_specs: list[dict[str, str | None]]) -> float:
    if not call_specs:
        return 0.0
    hits = sum(1 for item in call_specs if item["endpoint"] in specs)
    return hits / len(call_specs)


def _match_method_specs(specs: dict[str, dict[str, set[str]]], call_specs: list[dict[str, str | None]]) -> float:
    if not call_specs:
        return 0.0

    hits = 0
    considered = 0
    for item in call_specs:
        method = item.get("method")
        endpoint = item.get("endpoint")
        if not method or not endpoint:
            continue
        considered += 1
        if method in specs.get(endpoint, {}).get("methods", set()):
            hits += 1
    return hits / considered if considered else 1.0


def _field_overlap(expected: set[str], actual: set[str]) -> float:
    if not expected:
        return 0.0
    return len(expected & actual) / max(len(expected), 1)


def _coerce_string_list(value: object) -> list[str]:
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _phrase_present(phrase: str, haystack: str) -> bool:
    phrase = phrase.strip().lower()
    if not phrase:
        return False
    if phrase in haystack:
        return True

    tokens = [
        token for token in re.findall(r"[a-z0-9]+", phrase) if len(token) > 2 and token not in _EXPERIENCE_STOPWORDS
    ]
    if not tokens:
        return False

    hits = sum(1 for token in tokens if token in haystack)
    return hits >= 1 if len(tokens) <= 2 else hits >= 2


def _has_unawaited_async_helper_calls(backend_code: dict[str, str]) -> bool:
    ai_service = backend_code.get("ai_service.py", "")
    if not ai_service:
        return False

    async_helpers = set(re.findall(r"async def (\w+)\(", ai_service))
    if not async_helpers:
        return False

    for path, content in backend_code.items():
        if not path.endswith(".py") or path == "ai_service.py":
            continue
        for helper in async_helpers:
            if re.search(rf"(?<!await\s)(=\s*){helper}\(", content):
                return True
            if re.search(rf"(?<!await\s)(return\s+){helper}\(", content):
                return True
    return False


def route_code_eval(state: VibeDeployState) -> str:
    eval_result = state.get("code_eval_result", {})
    iteration = state.get("code_eval_iteration", 0)
    blueprint = state.get("blueprint", {}) or {}
    frontend_code = state.get("frontend_code", {}) or {}
    backend_code = state.get("backend_code", {}) or {}

    if eval_result.get("passed", False):
        logger.info("[CODE_EVAL] PASSED → deployer")
        return "deployer"

    expected_frontend = blueprint.get("frontend_files", {})
    missing_frontend = eval_result.get("missing_frontend") or list(
        expected_frontend.keys() if not frontend_code else []
    )
    if expected_frontend and missing_frontend:
        if iteration < MAX_EMPTY_FRONTEND_RETRIES:
            logger.warning(
                "[CODE_EVAL] Missing %d frontend files (expected %d) → force retry (iter %d/%d)",
                len(missing_frontend),
                len(expected_frontend),
                iteration,
                MAX_EMPTY_FRONTEND_RETRIES,
            )
            return "code_generator"
        logger.error(
            "[CODE_EVAL] Still missing %d frontend files after %d iters → deployer (deployment will be blocked)",
            len(missing_frontend),
            iteration,
        )

    expected_backend = blueprint.get("backend_files", {})
    missing_backend = eval_result.get("missing_backend") or list(expected_backend.keys() if not backend_code else [])
    if expected_backend and missing_backend:
        if iteration < MAX_EMPTY_BACKEND_RETRIES:
            logger.warning(
                "[CODE_EVAL] Missing %d backend files (expected %d) → force retry (iter %d/%d)",
                len(missing_backend),
                len(expected_backend),
                iteration,
                MAX_EMPTY_BACKEND_RETRIES,
            )
            return "code_generator"
        logger.error(
            "[CODE_EVAL] Still missing %d backend files after %d iters → deployer (deployment will be blocked)",
            len(missing_backend),
            iteration,
        )

    if iteration >= MAX_CODE_EVAL_ITERATIONS:
        logger.info("[CODE_EVAL] Max iterations reached → deployer (deployment will be blocked unless passed)")
        return "deployer"

    logger.info("[CODE_EVAL] FAILED → code_generator (retry)")
    return "code_generator"
