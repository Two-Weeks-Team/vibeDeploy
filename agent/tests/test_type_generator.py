import json

import pytest

from agent.nodes.type_generator import generate_api_dts, generate_typescript_types

SIMPLE_SPEC = {
    "openapi": "3.1.0",
    "info": {"title": "Test API", "version": "2.0.0"},
    "paths": {},
    "components": {
        "schemas": {
            "User": {
                "type": "object",
                "required": ["id", "name"],
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "active": {"type": "boolean"},
                    "score": {"type": "number"},
                },
            }
        }
    },
}


def _spec_json(**overrides) -> str:
    spec = json.loads(json.dumps(SIMPLE_SPEC))
    spec.update(overrides)
    return json.dumps(spec)


def _make_spec(schemas: dict) -> str:
    return json.dumps(
        {
            "openapi": "3.1.0",
            "info": {"title": "MyApp", "version": "1.0.0"},
            "paths": {},
            "components": {"schemas": schemas},
        }
    )


def test_valid_spec_produces_interface():
    result = generate_typescript_types(json.dumps(SIMPLE_SPEC))
    assert "export interface User {" in result
    assert "}" in result


def test_string_type_mapped():
    result = generate_typescript_types(json.dumps(SIMPLE_SPEC))
    assert "name?: string" in result or "name: string" in result


def test_integer_maps_to_number():
    result = generate_typescript_types(json.dumps(SIMPLE_SPEC))
    assert "id?: number" in result or "id: number" in result


def test_number_maps_to_number():
    result = generate_typescript_types(json.dumps(SIMPLE_SPEC))
    assert "score?: number" in result or "score: number" in result


def test_boolean_maps_to_boolean():
    result = generate_typescript_types(json.dumps(SIMPLE_SPEC))
    assert "active?: boolean" in result or "active: boolean" in result


def test_required_fields_have_no_optional_marker():
    result = generate_typescript_types(json.dumps(SIMPLE_SPEC))
    assert "id: number" in result
    assert "name: string" in result
    assert "id?: number" not in result
    assert "name?: string" not in result


def test_optional_fields_have_question_mark():
    result = generate_typescript_types(json.dumps(SIMPLE_SPEC))
    assert "active?: boolean" in result


def test_empty_schemas_returns_comment():
    spec = json.dumps(
        {
            "openapi": "3.1.0",
            "info": {"title": "Empty", "version": "1.0.0"},
            "paths": {},
            "components": {"schemas": {}},
        }
    )
    result = generate_typescript_types(spec)
    assert result.startswith("//")


def test_no_components_returns_comment():
    spec = json.dumps({"openapi": "3.1.0", "info": {"title": "x", "version": "1"}, "paths": {}})
    result = generate_typescript_types(spec)
    assert result.startswith("//")


def test_invalid_json_returns_error_comment():
    result = generate_typescript_types("not valid json {{{")
    assert result.startswith("//")
    assert "Error" in result


def test_array_type_produces_bracket_notation():
    spec = _make_spec(
        {
            "PostList": {
                "type": "object",
                "properties": {
                    "items": {"type": "array", "items": {"type": "string"}},
                },
            }
        }
    )
    result = generate_typescript_types(spec)
    assert "string[]" in result


def test_array_of_integers():
    spec = _make_spec(
        {
            "IdList": {
                "type": "object",
                "properties": {
                    "ids": {"type": "array", "items": {"type": "integer"}},
                },
            }
        }
    )
    result = generate_typescript_types(spec)
    assert "number[]" in result


def test_nested_object_rendered_inline():
    spec = _make_spec(
        {
            "Order": {
                "type": "object",
                "properties": {
                    "address": {
                        "type": "object",
                        "properties": {
                            "street": {"type": "string"},
                            "zip": {"type": "string"},
                        },
                    }
                },
            }
        }
    )
    result = generate_typescript_types(spec)
    assert "address?" in result
    assert "street" in result


def test_ref_resolved_to_name():
    spec = _make_spec(
        {
            "Cart": {
                "type": "object",
                "properties": {
                    "user": {"$ref": "#/components/schemas/User"},
                },
            },
            "User": {
                "type": "object",
                "properties": {"id": {"type": "integer"}},
            },
        }
    )
    result = generate_typescript_types(spec)
    assert "User" in result
    assert "Cart" in result


def test_multiple_schemas_all_emitted():
    spec = _make_spec(
        {
            "Alpha": {"type": "object", "properties": {"x": {"type": "string"}}},
            "Beta": {"type": "object", "properties": {"y": {"type": "integer"}}},
            "Gamma": {"type": "object", "properties": {"z": {"type": "boolean"}}},
        }
    )
    result = generate_typescript_types(spec)
    assert "export interface Alpha {" in result
    assert "export interface Beta {" in result
    assert "export interface Gamma {" in result


def test_schema_with_no_properties_uses_index_signature():
    spec = _make_spec({"Opaque": {"type": "object"}})
    result = generate_typescript_types(spec)
    assert "[key: string]: unknown" in result


def test_generate_api_dts_contains_header_comment():
    result = generate_api_dts(json.dumps(SIMPLE_SPEC))
    assert result.startswith("/**")
    assert "DO NOT EDIT" in result


def test_generate_api_dts_includes_title_and_version():
    result = generate_api_dts(json.dumps(SIMPLE_SPEC))
    assert "Test API" in result
    assert "2.0.0" in result


def test_generate_api_dts_includes_interfaces():
    result = generate_api_dts(json.dumps(SIMPLE_SPEC))
    assert "export interface User {" in result


def test_generate_api_dts_invalid_json_returns_error_comment():
    result = generate_api_dts("{{bad json}}")
    assert result.startswith("//")


def test_no_subprocess_used():
    import agent.nodes.type_generator as mod

    subprocess_attrs = [a for a in dir(mod) if "subprocess" in a.lower() or "popen" in a.lower()]
    assert subprocess_attrs == []

    result = generate_typescript_types(json.dumps(SIMPLE_SPEC))
    assert "export interface" in result


def test_oneof_produces_union_type():
    spec = _make_spec(
        {
            "Flexible": {
                "type": "object",
                "properties": {
                    "value": {
                        "oneOf": [{"type": "string"}, {"type": "integer"}],
                    }
                },
            }
        }
    )
    result = generate_typescript_types(spec)
    assert "string | number" in result


@pytest.mark.parametrize(
    ("openapi_type", "expected_ts"),
    [
        ("string", "string"),
        ("integer", "number"),
        ("number", "number"),
        ("boolean", "boolean"),
    ],
)
def test_primitive_type_mapping(openapi_type: str, expected_ts: str):
    spec = _make_spec(
        {
            "Prim": {
                "type": "object",
                "properties": {"field": {"type": openapi_type}},
            }
        }
    )
    result = generate_typescript_types(spec)
    assert f"field?: {expected_ts}" in result
