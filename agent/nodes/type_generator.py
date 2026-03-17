"""TypeScript type generator from OpenAPI spec — deterministic, no subprocess, no npx."""

from __future__ import annotations

import json
from typing import Any

_TYPE_MAP: dict[str, str] = {
    "string": "string",
    "integer": "number",
    "number": "number",
    "boolean": "boolean",
    "null": "null",
}


def _resolve_ref(ref: str) -> str:
    return ref.split("/")[-1]


def _openapi_type_to_ts(schema: Any, *, _depth: int = 0) -> str:
    """Convert an OpenAPI schema node to a TypeScript type expression.

    ``_depth`` guards against infinite recursion on pathological circular schemas.
    """
    if not isinstance(schema, dict) or _depth > 8:
        return "any"

    if "$ref" in schema:
        return _resolve_ref(str(schema["$ref"]))

    schema_type: str | None = schema.get("type")

    for keyword in ("oneOf", "anyOf"):
        if keyword in schema:
            sub = schema[keyword]
            if isinstance(sub, list) and sub:
                parts = [_openapi_type_to_ts(s, _depth=_depth + 1) for s in sub]
                return " | ".join(parts)

    if schema_type == "array":
        items = schema.get("items", {})
        item_ts = _openapi_type_to_ts(items, _depth=_depth + 1)
        return f"{item_ts}[]"

    if schema_type == "object" or (schema_type is None and "properties" in schema):
        props: dict = schema.get("properties") or {}
        if not props:
            return "Record<string, unknown>"
        inner = _render_object_props(props, _depth=_depth + 1)
        pad = "  " * _depth
        return "{\n" + inner + pad + "}"

    if schema_type in _TYPE_MAP:
        return _TYPE_MAP[schema_type]

    return "any"


def _render_object_props(properties: dict[str, Any], *, _depth: int = 1) -> str:
    pad = "  " * _depth
    lines: list[str] = []
    for prop_name, prop_schema in properties.items():
        if not isinstance(prop_schema, dict):
            prop_schema = {}
        ts_type = _openapi_type_to_ts(prop_schema, _depth=_depth)
        lines.append(f"{pad}{prop_name}: {ts_type};")
    return "\n".join(lines) + "\n"


def _schema_to_interface(name: str, schema: dict[str, Any]) -> str:
    lines: list[str] = [f"export interface {name} {{"]

    properties: dict[str, Any] = schema.get("properties") or {}
    required: list[str] = schema.get("required") or []

    if not isinstance(properties, dict):
        properties = {}

    if properties:
        for prop_name, prop_schema in properties.items():
            if not isinstance(prop_schema, dict):
                prop_schema = {}
            optional = "" if prop_name in required else "?"
            ts_type = _openapi_type_to_ts(prop_schema)
            lines.append(f"  {prop_name}{optional}: {ts_type};")
    else:
        lines.append("  [key: string]: unknown;")

    lines.append("}")
    return "\n".join(lines)


def generate_typescript_types(openapi_json: str) -> str:
    """Convert an OpenAPI spec JSON string to TypeScript interface definitions.

    For each schema in ``components/schemas``, emits one ``export interface``.
    Pure Python — no subprocess, no npx.

    Returns a comment line when no schemas exist or the input is not valid JSON.
    """
    try:
        spec = json.loads(openapi_json)
    except (json.JSONDecodeError, ValueError):
        return "// Error: invalid JSON input\n"

    if not isinstance(spec, dict):
        return "// Error: spec root must be a JSON object\n"

    components = spec.get("components") or {}
    schemas: dict[str, Any] = components.get("schemas") or {} if isinstance(components, dict) else {}

    if not isinstance(schemas, dict) or not schemas:
        return "// No schemas found\n"

    interfaces: list[str] = []
    for schema_name, schema_def in schemas.items():
        if not isinstance(schema_def, dict):
            schema_def = {}
        interfaces.append(_schema_to_interface(schema_name, schema_def))

    return "\n\n".join(interfaces) + "\n"


def generate_api_dts(openapi_json: str) -> str:
    """Wrap generated TypeScript types in ``api.d.ts`` format with a header comment.

    The header records the API title and version from the OpenAPI ``info`` block.
    Returns an error comment line when the input is not valid JSON.
    """
    try:
        spec = json.loads(openapi_json)
    except (json.JSONDecodeError, ValueError):
        return "// Error: invalid JSON input\n"

    info: dict = spec.get("info") or {} if isinstance(spec, dict) else {}
    title: str = str(info.get("title") or "Unknown API")
    version: str = str(info.get("version") or "0.0.0")

    header = (
        f"/**\n"
        f" * Auto-generated TypeScript types for {title}\n"
        f" * Version: {version}\n"
        f" * DO NOT EDIT — generated from OpenAPI spec\n"
        f" */\n\n"
    )

    body = generate_typescript_types(openapi_json)
    return header + body
