"""OpenAPI 3.1.0 Spec Generator — deterministic, no LLM calls."""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, Field, ValidationError


class OpenAPISpec(BaseModel):
    openapi: str = "3.1.0"
    info: dict
    paths: dict
    components: dict = Field(default_factory=lambda: {"schemas": {}})


def _parse_method_and_path(item: dict) -> tuple[str, str]:
    """Extract HTTP method and URL path from a contract item.

    Supports two shapes:
    - Explicit: {"method": "GET", "path": "/api/items", ...}
    - Blueprint native: {"calls": "GET /api/items", ...}
    """
    if "method" in item and "path" in item:
        return str(item["method"]).upper(), str(item["path"])

    calls = str(item.get("calls", ""))
    parts = calls.strip().split(None, 1)
    if len(parts) == 2:
        return parts[0].upper(), parts[1]

    return "GET", "/unknown"


def _to_schema_name(path: str, suffix: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9/]", "_", path)
    segments = [s.capitalize() for s in clean.strip("/").split("/") if s]
    return "".join(segments) + suffix


def _build_schema_from_fields(fields: list[str] | dict | None) -> dict:
    if isinstance(fields, dict):
        properties: dict[str, dict] = {}
        for key, val in fields.items():
            if isinstance(val, dict):
                properties[key] = val
            else:
                properties[key] = {"type": "string", "example": str(val)}
        return {"type": "object", "properties": properties}

    if isinstance(fields, list) and fields:
        properties = {str(f): {"type": "string"} for f in fields}
        return {"type": "object", "properties": properties}

    return {"type": "object"}


def generate_api_contract(blueprint: dict) -> str:
    """Generate a valid OpenAPI 3.1.0 JSON string from a blueprint dict.

    Reads ``blueprint["frontend_backend_contract"]`` (list of endpoint dicts).
    Each item may contain:
      - method, path, description, request_body, response_body  (preferred)
      - OR  calls (e.g. "POST /api/plan"), request_fields, response_fields  (blueprint native)

    Returns a JSON string representing the full OpenAPI spec.
    """
    contract: list[dict] = blueprint.get("frontend_backend_contract") or []
    app_name: str = str(blueprint.get("app_name") or "vibedeploy-app")

    paths: dict = {}
    schemas: dict = {}

    for item in contract:
        if not isinstance(item, dict):
            continue

        method, path = _parse_method_and_path(item)
        description: str = str(item.get("description") or item.get("calls") or f"{method} {path}")

        # Resolve request/response body sources (prefer explicit over fields list)
        request_body_raw = item.get("request_body") or item.get("request_fields")
        response_body_raw = item.get("response_body") or item.get("response_fields")

        request_schema = _build_schema_from_fields(request_body_raw)
        response_schema = _build_schema_from_fields(response_body_raw)

        method_prefix = method.capitalize()
        req_schema_name = _to_schema_name(path, f"{method_prefix}Request")
        resp_schema_name = _to_schema_name(path, f"{method_prefix}Response")
        schemas[req_schema_name] = request_schema
        schemas[resp_schema_name] = response_schema

        operation: dict = {
            "summary": description,
            "responses": {
                "200": {
                    "description": "Successful response",
                    "content": {"application/json": {"schema": {"$ref": f"#/components/schemas/{resp_schema_name}"}}},
                }
            },
        }

        if method in ("POST", "PUT", "PATCH") and request_schema.get("properties"):
            operation["requestBody"] = {
                "required": True,
                "content": {"application/json": {"schema": {"$ref": f"#/components/schemas/{req_schema_name}"}}},
            }

        if path not in paths:
            paths[path] = {}
        paths[path][method.lower()] = operation

    spec = OpenAPISpec(
        openapi="3.1.0",
        info={
            "title": app_name,
            "version": "1.0.0",
            "description": f"Auto-generated API contract for {app_name}",
        },
        paths=paths,
        components={"schemas": schemas},
    )

    return json.dumps(spec.model_dump(), indent=2, ensure_ascii=False)


def validate_openapi_spec(spec_json: str) -> bool:
    try:
        data = json.loads(spec_json)
        OpenAPISpec.model_validate(data)
        return True
    except (json.JSONDecodeError, ValidationError):
        return False


async def api_contract_generator_node(state: dict, config=None) -> dict:
    blueprint = state.get("blueprint") or {}
    spec_json = generate_api_contract(blueprint)
    if not validate_openapi_spec(spec_json):
        return {
            "api_contract": spec_json,
            "spec_frozen": False,
            "spec_freeze_errors": ["Generated API contract is not valid OpenAPI JSON"],
            "phase": "api_contract_invalid",
        }
    return {
        "api_contract": spec_json,
        "phase": "api_contract_generated",
    }
