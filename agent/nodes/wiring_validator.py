from __future__ import annotations

import re
from typing import Any

from .contract_validator import validate_with_timeout


def _extract_frontend_api_targets(frontend_code: dict[str, str]) -> list[tuple[str, str]]:
    pattern = re.compile(
        r'fetch\(["\'](?P<path>/api/[^"\']+)["\']\s*,\s*\{[^}]*method:\s*["\'](?P<method>[A-Z]+)["\']', re.DOTALL
    )
    get_pattern = re.compile(r'fetch\(["\'](?P<path>/api/[^"\']+)["\']')
    targets: list[tuple[str, str]] = []
    for content in frontend_code.values():
        if not isinstance(content, str):
            continue
        for m in pattern.finditer(content):
            targets.append((m.group("method").upper(), m.group("path")))
        paths_with_explicit_method = {p for _, p in targets}
        for m in get_pattern.finditer(content):
            path = m.group("path")
            if path not in paths_with_explicit_method and ("GET", path) not in targets:
                targets.append(("GET", path))
    return targets


async def wiring_validator(state: dict[str, Any], config=None) -> dict:
    api_contract = str(state.get("api_contract") or "").strip()
    backend_code = dict(state.get("backend_code") or {})
    frontend_code = dict(state.get("frontend_code") or {})
    if not api_contract:
        return {
            "wiring_validation": {"passed": False, "errors": ["api_contract_missing"]},
            "phase": "wiring_validation_failed",
        }
    contract_result = await validate_with_timeout(api_contract, backend_code, timeout=10.0)
    frontend_targets = _extract_frontend_api_targets(frontend_code)
    errors = list(contract_result.get("errors") or [])
    errors.extend(contract_result.get("missing") or [])
    errors.extend(contract_result.get("schema_mismatches") or [])
    if not frontend_targets:
        errors.append("frontend_has_no_api_fetch_calls")
    passed = bool(contract_result.get("passed")) and not errors
    return {
        "wiring_validation": {
            **contract_result,
            "frontend_targets": sorted(f"{m} {p}" for m, p in frontend_targets),
            "errors": errors,
            "passed": passed,
        },
        "phase": "wiring_validated" if passed else "wiring_validation_failed",
        "error": "; ".join(errors) if errors else None,
    }
