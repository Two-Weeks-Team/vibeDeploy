"""Contract Validator — compares OpenAPI spec endpoints against generated FastAPI routes."""

from __future__ import annotations

import json
import re

# Regex to match FastAPI route decorators
_ROUTE_PATTERN = re.compile(
    r"""@(?:app|router)\.(get|post|put|delete|patch|head|options)\s*\(\s*["']([^"']+)["']""",
    re.IGNORECASE,
)


def extract_fastapi_routes(code: str) -> list[dict]:
    """Extract route definitions from FastAPI Python code using regex.

    Scans for ``@app.get("/path")``, ``@router.post("/path")``, etc.

    Args:
        code: Python source code string.

    Returns:
        List of dicts with ``method`` (uppercase) and ``path`` keys.
    """
    routes: list[dict] = []
    for match in _ROUTE_PATTERN.finditer(code):
        method = match.group(1).upper()
        path = match.group(2)
        routes.append({"method": method, "path": path})
    return routes


def _parse_spec_endpoints(api_contract_json: str) -> list[dict]:
    try:
        spec = json.loads(api_contract_json)
    except (json.JSONDecodeError, ValueError):
        return []

    if not isinstance(spec, dict):
        return []

    paths = spec.get("paths") or {}
    if not isinstance(paths, dict):
        return []

    endpoints: list[dict] = []
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method in methods:
            # Skip OpenAPI special keys like "parameters", "summary"
            if method.lower() in ("get", "post", "put", "delete", "patch", "head", "options"):
                endpoints.append({"method": method.upper(), "path": path})
    return endpoints


def _endpoint_key(endpoint: dict) -> str:
    return f"{endpoint['method'].upper()} {endpoint['path']}"


def compare_endpoints(spec_endpoints: list[dict], code_endpoints: list[dict]) -> dict:
    """Set-based comparison of spec vs code endpoint lists.

    Args:
        spec_endpoints: Endpoints from OpenAPI spec (list of {method, path}).
        code_endpoints: Endpoints extracted from backend code.

    Returns:
        Dict with keys: passed, total_endpoints, matched, missing, extra.
    """
    spec_keys = {_endpoint_key(e) for e in spec_endpoints}
    code_keys = {_endpoint_key(e) for e in code_endpoints}

    matched_keys = spec_keys & code_keys
    missing_keys = spec_keys - code_keys
    extra_keys = code_keys - spec_keys

    matched = len(matched_keys)
    total_endpoints = len(spec_keys)
    passed = len(missing_keys) == 0 and total_endpoints > 0 or (total_endpoints == 0 and len(extra_keys) == 0)

    return {
        "passed": passed,
        "total_endpoints": total_endpoints,
        "matched": matched,
        "missing": sorted(missing_keys),
        "extra": sorted(extra_keys),
    }


def validate_contract(api_contract_json: str, backend_code: dict[str, str]) -> dict:
    """Validate OpenAPI spec endpoints against generated FastAPI routes.

    Parses ``api_contract_json`` for paths, then scans ``backend_code`` for
    FastAPI route decorators.  Prefers ``routes.py`` but falls back to
    ``main.py`` if ``routes.py`` is absent.  If neither is present all
    available ``.py`` files are searched.

    Args:
        api_contract_json: OpenAPI 3.x JSON string.
        backend_code: Mapping of filename → source code.

    Returns:
        Dict: {passed, total_endpoints, matched, missing, extra}
    """
    spec_endpoints = _parse_spec_endpoints(api_contract_json)

    if "routes.py" in backend_code:
        code_sources = [backend_code["routes.py"]]
    elif "main.py" in backend_code:
        code_sources = [backend_code["main.py"]]
    else:
        code_sources = [v for k, v in backend_code.items() if k.endswith(".py") and isinstance(v, str)]

    code_endpoints: list[dict] = []
    for source in code_sources:
        if isinstance(source, str):
            code_endpoints.extend(extract_fastapi_routes(source))

    seen: set[str] = set()
    unique_code_endpoints: list[dict] = []
    for ep in code_endpoints:
        key = _endpoint_key(ep)
        if key not in seen:
            seen.add(key)
            unique_code_endpoints.append(ep)

    return compare_endpoints(spec_endpoints, unique_code_endpoints)
