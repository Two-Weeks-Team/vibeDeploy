from __future__ import annotations

import json
from typing import Any

from .api_contract_generator import validate_openapi_spec


def _extract_contract_endpoints(blueprint: dict[str, Any]) -> set[tuple[str, str]]:
    items = blueprint.get("frontend_backend_contract") or []
    endpoints: set[tuple[str, str]] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        calls = str(item.get("calls") or "").strip()
        method = str(item.get("method") or "").strip().upper()
        path = str(item.get("path") or "").strip()
        if calls and not (method and path):
            parts = calls.split(None, 1)
            if len(parts) == 2:
                method, path = parts[0].upper(), parts[1]
        if method and path:
            endpoints.add((method, path))
    return endpoints


def _extract_spec_endpoints(spec_json: str) -> set[tuple[str, str]]:
    data = json.loads(spec_json)
    paths = data.get("paths") or {}
    endpoints: set[tuple[str, str]] = set()
    if not isinstance(paths, dict):
        return endpoints
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method in methods.keys():
            if method.lower() in {"get", "post", "put", "patch", "delete", "head", "options"}:
                endpoints.add((method.upper(), str(path)))
    return endpoints


async def spec_freeze_gate(state: dict[str, Any], config=None) -> dict:
    spec_json = str(state.get("api_contract") or "").strip()
    blueprint = state.get("blueprint") or {}
    attempt = int(state.get("spec_freeze_attempt_count") or 0) + 1
    errors: list[str] = []

    if not spec_json:
        errors.append("api_contract_missing")
    elif not validate_openapi_spec(spec_json):
        errors.append("api_contract_invalid")

    if spec_json:
        try:
            spec_endpoints = _extract_spec_endpoints(spec_json)
        except Exception:
            spec_endpoints = set()
            errors.append("api_contract_unparseable")
        contract_endpoints = _extract_contract_endpoints(blueprint)
        missing = sorted(contract_endpoints - spec_endpoints)
        if missing:
            errors.append("missing_contract_endpoints:" + ", ".join(f"{m} {p}" for m, p in missing))
        if not spec_endpoints:
            errors.append("api_contract_has_no_endpoints")

    return {
        "spec_frozen": len(errors) == 0,
        "spec_freeze_errors": errors,
        "spec_freeze_attempt_count": attempt,
        "phase": "spec_frozen" if not errors else "spec_freeze_failed",
        "error": "; ".join(errors) if errors else None,
    }
