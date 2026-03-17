"""Contract Validator — compares OpenAPI spec endpoints against generated FastAPI routes."""

from __future__ import annotations

import asyncio
import json
import re

# Regex to match FastAPI route decorators
_ROUTE_PATTERN = re.compile(
    r"""@(?:app|router)\.(get|post|put|delete|patch|head|options)\s*\(\s*["']([^"']+)["']""",
    re.IGNORECASE,
)

# Regex to extract Pydantic model field definitions: field_name: type (with optional default)
_PYDANTIC_FIELD_PATTERN = re.compile(
    r"""^\s{4}(\w+)\s*:\s*([\w\[\], |]+?)(?:\s*=.*)?$""",
    re.MULTILINE,
)

# Regex to extract class names (Pydantic models inherit from BaseModel)
_PYDANTIC_CLASS_PATTERN = re.compile(
    r"""^class\s+(\w+)\s*\(\s*(?:[\w.]*BaseModel[\w.]*|[\w.]*Schema[\w.]*)\s*\)\s*:""",
    re.MULTILINE,
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


def _parse_spec_schemas(api_contract_json: str) -> dict[str, dict]:
    """Extract component schemas from an OpenAPI spec JSON string.

    Args:
        api_contract_json: OpenAPI 3.x JSON string.

    Returns:
        Mapping of schema_name → {field_name: type_string}.
    """
    try:
        spec = json.loads(api_contract_json)
    except (json.JSONDecodeError, ValueError):
        return {}

    if not isinstance(spec, dict):
        return {}

    components = spec.get("components") or {}
    schemas = components.get("schemas") or {}
    if not isinstance(schemas, dict):
        return {}

    result: dict[str, dict] = {}
    for schema_name, schema_def in schemas.items():
        if not isinstance(schema_def, dict):
            continue
        props = schema_def.get("properties") or {}
        fields: dict[str, str] = {}
        for field_name, field_def in props.items():
            if isinstance(field_def, dict):
                # Resolve $ref shorthand (e.g. "#/components/schemas/Foo" → "Foo")
                if "$ref" in field_def:
                    ref = field_def["$ref"]
                    type_str = ref.split("/")[-1] if "/" in ref else ref
                else:
                    field_type = field_def.get("type", "object")
                    fmt = field_def.get("format")
                    type_str = f"{field_type}({fmt})" if fmt else field_type
                fields[field_name] = type_str
        result[schema_name] = fields
    return result


def _extract_pydantic_models(backend_code: dict[str, str]) -> dict[str, dict]:
    """Extract field names from Pydantic model classes in the backend source.

    Looks at ``schemas.py`` first, then ``models.py``, then any ``.py`` file.

    Args:
        backend_code: Mapping of filename → source code.

    Returns:
        Mapping of class_name → {field_name: raw_type_annotation}.
    """
    # Determine which sources to scan
    if "schemas.py" in backend_code:
        sources = [("schemas.py", backend_code["schemas.py"])]
    elif "models.py" in backend_code:
        sources = [("models.py", backend_code["models.py"])]
    else:
        sources = [(k, v) for k, v in backend_code.items() if k.endswith(".py") and isinstance(v, str)]

    models: dict[str, dict] = {}
    for _filename, code in sources:
        if not isinstance(code, str):
            continue
        # Find all Pydantic class blocks
        class_matches = list(_PYDANTIC_CLASS_PATTERN.finditer(code))
        for idx, cls_match in enumerate(class_matches):
            class_name = cls_match.group(1)
            start = cls_match.end()
            # Extract class body up to the next class declaration or end of file
            end = class_matches[idx + 1].start() if idx + 1 < len(class_matches) else len(code)
            class_body = code[start:end]
            fields: dict[str, str] = {}
            for field_match in _PYDANTIC_FIELD_PATTERN.finditer(class_body):
                field_name = field_match.group(1)
                type_annotation = field_match.group(2).strip()
                # Skip dunder / private attributes
                if not field_name.startswith("_"):
                    fields[field_name] = type_annotation
            models[class_name] = fields
    return models


def compare_schemas(expected_schemas: dict, actual_models: dict) -> list[dict]:
    """Compare OpenAPI component schemas against Pydantic model fields.

    Checks that every field declared in an OpenAPI schema exists in the
    corresponding Pydantic model.  Extra fields in the model are allowed.

    Args:
        expected_schemas: Mapping of schema_name → {field_name: type_string}
                          as returned by ``_parse_spec_schemas``.
        actual_models:    Mapping of class_name → {field_name: annotation}
                          as returned by ``_extract_pydantic_models``.

    Returns:
        List of mismatch dicts: ``{"schema": name, "field": field, "issue": description}``.
    """
    mismatches: list[dict] = []

    for schema_name, spec_fields in expected_schemas.items():
        model_fields = actual_models.get(schema_name)
        if model_fields is None:
            mismatches.append(
                {
                    "schema": schema_name,
                    "field": None,
                    "issue": f"Pydantic model '{schema_name}' not found in backend code",
                }
            )
            continue

        for field_name in spec_fields:
            if field_name not in model_fields:
                mismatches.append(
                    {
                        "schema": schema_name,
                        "field": field_name,
                        "issue": f"Field '{field_name}' missing from model '{schema_name}'",
                    }
                )

    return mismatches


def _build_repair_instructions(endpoint_result: dict, schema_mismatches: list[dict]) -> list[dict]:
    """Build structured repair instructions for the code_generator node.

    Args:
        endpoint_result: Result dict from ``compare_endpoints``.
        schema_mismatches: List of mismatch dicts from ``compare_schemas``.

    Returns:
        List of repair instruction dicts.
    """
    instructions: list[dict] = []

    # Endpoint repair: add missing routes
    for missing_key in endpoint_result.get("missing", []):
        parts = missing_key.split(" ", 1)
        method = parts[0] if len(parts) == 2 else "GET"
        path = parts[1] if len(parts) == 2 else missing_key
        instructions.append(
            {
                "file": "main.py",
                "action": "add_endpoint",
                "path": path,
                "method": method,
            }
        )

    # Schema repair: add missing fields
    for mismatch in schema_mismatches:
        if mismatch.get("field") is None:
            # Missing model entirely — ask code_generator to create it
            instructions.append(
                {
                    "file": "schemas.py",
                    "action": "add_model",
                    "schema": mismatch["schema"],
                }
            )
        else:
            instructions.append(
                {
                    "file": "schemas.py",
                    "action": "add_field",
                    "schema": mismatch["schema"],
                    "field": mismatch["field"],
                    "type": "str",  # conservative default; code_generator should infer from context
                }
            )

    return instructions


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
    """Validate OpenAPI spec endpoints **and** schemas against generated FastAPI code.

    Parses ``api_contract_json`` for paths and component schemas, then scans
    ``backend_code`` for FastAPI route decorators and Pydantic model definitions.
    Prefers ``routes.py`` for endpoint detection but falls back to ``main.py``.
    Prefers ``schemas.py`` / ``models.py`` for schema detection.

    When mismatches are found the result includes ``repair_instructions`` — a
    list of structured actions the ``code_generator`` node can act on.

    Args:
        api_contract_json: OpenAPI 3.x JSON string.
        backend_code: Mapping of filename → source code.

    Returns:
        Dict::

            {
                "passed": bool,
                "total_endpoints": int,
                "matched": int,
                "missing": [...],
                "extra": [...],
                "schema_mismatches": [...],
                "repair_instructions": [...],
            }
    """
    # ── Endpoint validation ──────────────────────────────────────────────────
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

    endpoint_result = compare_endpoints(spec_endpoints, unique_code_endpoints)

    # ── Schema validation ────────────────────────────────────────────────────
    expected_schemas = _parse_spec_schemas(api_contract_json)
    actual_models = _extract_pydantic_models(backend_code)
    schema_mismatches = compare_schemas(expected_schemas, actual_models)

    # ── Combine results ──────────────────────────────────────────────────────
    all_passed = endpoint_result["passed"] and len(schema_mismatches) == 0
    repair_instructions = _build_repair_instructions(endpoint_result, schema_mismatches)

    return {
        "passed": all_passed,
        "total_endpoints": endpoint_result["total_endpoints"],
        "matched": endpoint_result["matched"],
        "missing": endpoint_result["missing"],
        "extra": endpoint_result["extra"],
        "schema_mismatches": schema_mismatches,
        "repair_instructions": repair_instructions,
    }


async def _validate(api_contract_json: str, backend_code: dict[str, str]) -> dict:
    """Async wrapper around the synchronous ``validate_contract``."""
    return validate_contract(api_contract_json, backend_code)


async def validate_with_timeout(
    api_contract_json: str,
    backend_code: dict[str, str],
    timeout: float = 10.0,
) -> dict:
    """Run contract validation with a hard timeout.

    Args:
        api_contract_json: OpenAPI 3.x JSON string.
        backend_code: Mapping of filename → source code.
        timeout: Maximum seconds to wait (default ``10.0``).

    Returns:
        Validation result dict (same shape as ``validate_contract``) or a
        timed-out error dict::

            {
                "passed": False,
                "errors": ["Validation timed out after 10s"],
                "schema_mismatches": [],
                "repair_instructions": [],
            }
    """
    try:
        return await asyncio.wait_for(_validate(api_contract_json, backend_code), timeout=timeout)
    except asyncio.TimeoutError:
        return {
            "passed": False,
            "errors": [f"Validation timed out after {timeout}s"],
            "total_endpoints": 0,
            "matched": 0,
            "missing": [],
            "extra": [],
            "schema_mismatches": [],
            "repair_instructions": [],
        }
