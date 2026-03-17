"""Pydantic model generator from OpenAPI spec — pure Python transformation, no CLI."""

from __future__ import annotations

import ast
import json
import keyword
import re
from typing import Any


def _map_type(schema: dict[str, Any]) -> str:
    if "$ref" in schema:
        return schema["$ref"].split("/")[-1]

    schema_type = schema.get("type", "Any")

    if schema_type == "string":
        return "str"
    if schema_type == "integer":
        return "int"
    if schema_type == "number":
        return "float"
    if schema_type == "boolean":
        return "bool"
    if schema_type == "array":
        items = schema.get("items", {})
        item_type = _map_type(items) if items else "Any"
        return f"list[{item_type}]"
    if schema_type == "object":
        return "dict[str, Any]"
    return "Any"


def _safe_identifier(name: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if clean and clean[0].isdigit():
        clean = "_" + clean
    if keyword.iskeyword(clean) or keyword.issoftkeyword(clean):
        clean = clean + "_"
    return clean or "_Field"


def _generate_class(class_name: str, schema_def: dict[str, Any]) -> list[str]:
    lines: list[str] = [f"class {class_name}(BaseModel):"]
    properties: dict[str, Any] = schema_def.get("properties") or {}
    required_fields: set[str] = set(schema_def.get("required") or [])

    if not properties:
        lines.append("    pass")
    else:
        for field_name, field_schema in properties.items():
            safe_name = _safe_identifier(field_name)
            python_type = _map_type(field_schema)
            if field_name in required_fields:
                lines.append(f"    {safe_name}: {python_type}")
            else:
                lines.append(f"    {safe_name}: Optional[{python_type}] = None")

    return lines


def generate_pydantic_models(openapi_json: str) -> str:
    """Convert OpenAPI components/schemas to Pydantic BaseModel class definitions.

    Args:
        openapi_json: A valid OpenAPI spec JSON string.

    Returns:
        A Python source string with ``from pydantic import BaseModel`` header
        followed by one class per schema.  The result is guaranteed to pass
        ``ast.parse()``.
    """
    data: dict[str, Any] = json.loads(openapi_json)
    schemas: dict[str, Any] = (data.get("components") or {}).get("schemas") or {}

    header = [
        "from __future__ import annotations",
        "",
        "from typing import Any, Optional",
        "",
        "from pydantic import BaseModel",
        "",
    ]

    body: list[str] = []
    for schema_name, schema_def in schemas.items():
        if not isinstance(schema_def, dict):
            continue
        class_name = _safe_identifier(schema_name)
        body.extend(_generate_class(class_name, schema_def))
        body.append("")

    return "\n".join(header + body)


def validate_pydantic_output(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False
