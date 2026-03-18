"""TypeScript type generator from OpenAPI spec — deterministic, no subprocess, no npx."""

from __future__ import annotations

import json
import re
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
        req: list[str] = schema.get("required") or []
        inner = _render_object_props(props, required=req, _depth=_depth + 1)
        pad = "  " * _depth
        return "{\n" + inner + pad + "}"

    if schema_type in _TYPE_MAP:
        return _TYPE_MAP[schema_type]

    return "any"


def _render_object_props(properties: dict[str, Any], *, required: list[str] | None = None, _depth: int = 1) -> str:
    pad = "  " * _depth
    required_set = set(required or [])
    lines: list[str] = []
    for prop_name, prop_schema in properties.items():
        if not isinstance(prop_schema, dict):
            prop_schema = {}
        optional = "" if prop_name in required_set else "?"
        ts_type = _openapi_type_to_ts(prop_schema, _depth=_depth)
        lines.append(f"{pad}{prop_name}{optional}: {ts_type};")
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


_HTTP_METHODS_WITH_BODY = {"post", "put", "patch"}
_ALL_HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}

_API_CLIENT_PREAMBLE = """\
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

export class ApiError extends Error {
  constructor(public status: number, public body: string) {
    super(`API error ${status}: ${body}`);
  }
}"""


def _to_pascal(segment: str) -> str:
    """Convert a kebab/snake/plain string segment to PascalCase."""
    parts = re.split(r"[-_]", segment)
    return "".join(p.capitalize() for p in parts if p)


def _path_to_function_name(method: str, path: str) -> str:
    """Convert HTTP method + path to a camelCase TypeScript function name.

    Path parameters like ``{id}`` become ``ById`` in the name.

    Examples::

        GET  /users         → getUsers
        POST /items         → postItems
        GET  /users/{id}    → getUsersById
        DELETE /users/{id}  → deleteUsersById
    """
    segments = [s for s in path.split("/") if s]
    name_parts: list[str] = []
    for seg in segments:
        if seg.startswith("{") and seg.endswith("}"):
            param = seg[1:-1]
            name_parts.append("By" + _to_pascal(param))
        else:
            name_parts.append(_to_pascal(seg))
    method_lower = method.lower()
    return method_lower + "".join(name_parts) if name_parts else method_lower


def _extract_response_type(operation: dict[str, Any], fallback: str) -> str:
    """Return the TypeScript response type for an OpenAPI operation.

    Inspects the ``responses`` block (prefers HTTP 200, then 201, then first
    available) for an ``application/json`` schema ``$ref``.  Falls back to
    ``fallback`` when no ``$ref`` can be resolved.
    """
    responses = operation.get("responses") or {}
    if not isinstance(responses, dict):
        return fallback

    response: dict | None = responses.get("200") or responses.get("201")
    if response is None and responses:
        response = next(iter(responses.values()), None)

    if not isinstance(response, dict):
        return fallback

    content = response.get("content") or {}
    if not isinstance(content, dict):
        return fallback

    json_content = content.get("application/json") or {}
    if not isinstance(json_content, dict):
        return fallback

    schema = json_content.get("schema") or {}
    if not isinstance(schema, dict):
        return fallback

    if "$ref" in schema:
        return _resolve_ref(str(schema["$ref"]))

    if schema.get("type") == "array":
        items = schema.get("items") or {}
        if isinstance(items, dict) and "$ref" in items:
            return f"{_resolve_ref(str(items['$ref']))}[]"

    return fallback


def _extract_body_type(operation: dict[str, Any]) -> str:
    """Return the TypeScript request body type for an OpenAPI operation.

    Resolves a ``$ref`` when present; falls back to ``Record<string, unknown>``.
    """
    request_body = operation.get("requestBody") or {}
    if not isinstance(request_body, dict):
        return "Record<string, unknown>"

    content = request_body.get("content") or {}
    if not isinstance(content, dict):
        return "Record<string, unknown>"

    json_content = content.get("application/json") or {}
    if not isinstance(json_content, dict):
        return "Record<string, unknown>"

    schema = json_content.get("schema") or {}
    if not isinstance(schema, dict):
        return "Record<string, unknown>"

    if "$ref" in schema:
        return _resolve_ref(str(schema["$ref"]))

    return "Record<string, unknown>"


def _build_function_block(
    func_name: str,
    path: str,
    method: str,
    response_type: str,
    body_type: str | None,
    path_params: list[tuple[str, str]],
) -> str:
    """Render a single TypeScript fetch function block."""
    ts_path = re.sub(r"\{(\w+)\}", r"${\1}", path)

    param_parts: list[str] = []
    for pname, ptype in path_params:
        param_parts.append(f"{pname}: {ptype}")
    if body_type is not None:
        param_parts.append(f"body: {body_type}")
    params_str = ", ".join(param_parts)

    lines: list[str] = [
        f"export async function {func_name}({params_str}): Promise<{response_type}> {{",
    ]

    if body_type is not None:
        lines += [
            f"  const res = await fetch(`${{API_BASE_URL}}{ts_path}`, {{",
            f'    method: "{method.upper()}",',
            '    headers: { "Content-Type": "application/json" },',
            "    body: JSON.stringify(body),",
            "  });",
        ]
    else:
        lines.append(f'  const res = await fetch(`${{API_BASE_URL}}{ts_path}`, {{ method: "{method.upper()}" }});')

    lines += [
        "  if (!res.ok) throw new ApiError(res.status, await res.text());",
        "  return res.json();",
        "}",
    ]
    return "\n".join(lines)


def _extract_path_params(path: str, operation: dict[str, Any]) -> list[tuple[str, str]]:
    """Return ``[(name, ts_type), ...]`` for path parameters in the given path."""
    param_names = re.findall(r"\{(\w+)\}", path)
    if not param_names:
        return []

    parameters = operation.get("parameters") or []
    param_type_map: dict[str, str] = {}
    if isinstance(parameters, list):
        for p in parameters:
            if isinstance(p, dict) and p.get("in") == "path":
                name = str(p.get("name") or "")
                schema = p.get("schema") or {}
                ts_type = _openapi_type_to_ts(schema) if isinstance(schema, dict) else "string"
                if ts_type in ("any", "unknown"):
                    ts_type = "string | number"
                param_type_map[name] = ts_type

    return [(name, param_type_map.get(name, "string | number")) for name in param_names]


def generate_api_client(openapi_json: str) -> str:
    """Generate a TypeScript fetch API client from an OpenAPI spec JSON string.

    For each path+method in ``paths``, emits a typed ``async`` function that:

    * uses ``API_BASE_URL`` (from ``process.env.NEXT_PUBLIC_API_BASE_URL``),
    * throws ``ApiError`` on non-OK responses,
    * accepts a typed ``body`` parameter for POST / PUT / PATCH requests,
    * accepts path-parameter arguments derived from ``{param}`` placeholders.

    The output always includes the ``ApiError`` class definition and the
    ``API_BASE_URL`` constant regardless of whether the spec has any paths.

    Returns an error comment line when the input is not valid JSON.
    Pure Python — no subprocess, no npx.
    """
    try:
        spec = json.loads(openapi_json)
    except (json.JSONDecodeError, ValueError):
        return "// Error: invalid JSON input\n"

    if not isinstance(spec, dict):
        return "// Error: spec root must be a JSON object\n"

    paths: dict = spec.get("paths") or {}
    if not isinstance(paths, dict):
        paths = {}

    function_blocks: list[str] = []
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in _ALL_HTTP_METHODS:
                continue
            if not isinstance(operation, dict):
                continue

            func_name = _path_to_function_name(method, path)
            fallback_response = func_name[0].upper() + func_name[1:] + "Response"
            response_type = _extract_response_type(operation, fallback=fallback_response)
            path_params = _extract_path_params(path, operation)

            has_body = method.lower() in _HTTP_METHODS_WITH_BODY
            body_type: str | None = _extract_body_type(operation) if has_body else None

            function_blocks.append(
                _build_function_block(func_name, path, method, response_type, body_type, path_params)
            )

    parts = [_API_CLIENT_PREAMBLE] + function_blocks
    return "\n\n".join(parts) + "\n"


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

    # Reuse already-parsed spec to avoid double json.loads
    body = generate_typescript_types(json.dumps(spec))
    return header + body


async def type_generator_node(state: dict[str, Any], config=None) -> dict:
    api_contract = str(state.get("api_contract") or "").strip()
    if not api_contract:
        return {
            "generated_types": {},
            "phase": "type_generation_skipped",
        }
    dts = generate_api_dts(api_contract)
    client = generate_api_client(api_contract)
    frontend_code = dict(state.get("frontend_code") or {})
    frontend_code["src/types/api.d.ts"] = dts
    frontend_code["src/lib/api-client.ts"] = client
    return {
        "frontend_code": frontend_code,
        "generated_types": {
            "dts_path": "src/types/api.d.ts",
            "client_path": "src/lib/api-client.ts",
        },
        "phase": "types_generated",
    }
