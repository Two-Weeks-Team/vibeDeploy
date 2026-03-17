import json

from agent.nodes.pydantic_generator import generate_pydantic_models, validate_pydantic_output

SIMPLE_SPEC = json.dumps(
    {
        "openapi": "3.1.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {},
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "required": ["id", "name"],
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                    },
                }
            }
        },
    }
)

ALL_TYPES_SPEC = json.dumps(
    {
        "openapi": "3.1.0",
        "info": {"title": "Types API", "version": "1.0.0"},
        "paths": {},
        "components": {
            "schemas": {
                "AllTypes": {
                    "type": "object",
                    "required": ["s", "i", "n", "b"],
                    "properties": {
                        "s": {"type": "string"},
                        "i": {"type": "integer"},
                        "n": {"type": "number"},
                        "b": {"type": "boolean"},
                        "arr": {"type": "array", "items": {"type": "string"}},
                        "obj": {"type": "object"},
                    },
                }
            }
        },
    }
)


def test_valid_spec_produces_output():
    result = generate_pydantic_models(SIMPLE_SPEC)
    assert result.strip() != ""


def test_output_contains_basemodel_import():
    result = generate_pydantic_models(SIMPLE_SPEC)
    assert "from pydantic import BaseModel" in result


def test_output_contains_class_definition():
    result = generate_pydantic_models(SIMPLE_SPEC)
    assert "class User(BaseModel):" in result


def test_ast_parse_passes_for_valid_spec():
    result = generate_pydantic_models(SIMPLE_SPEC)
    assert validate_pydantic_output(result) is True


def test_ast_parse_passes_for_all_types():
    result = generate_pydantic_models(ALL_TYPES_SPEC)
    assert validate_pydantic_output(result) is True


def test_all_primitive_types_mapped():
    result = generate_pydantic_models(ALL_TYPES_SPEC)
    assert ": str" in result
    assert ": int" in result
    assert ": float" in result
    assert ": bool" in result


def test_array_type_mapped():
    result = generate_pydantic_models(ALL_TYPES_SPEC)
    assert "list[str]" in result


def test_object_type_mapped():
    result = generate_pydantic_models(ALL_TYPES_SPEC)
    assert "dict[str, Any]" in result


def test_required_fields_not_optional():
    result = generate_pydantic_models(SIMPLE_SPEC)
    lines = result.splitlines()
    id_lines = [line for line in lines if "id:" in line]
    name_lines = [line for line in lines if "name:" in line and "class" not in line]
    assert any("Optional" not in line for line in id_lines)
    assert any("Optional" not in line for line in name_lines)


def test_non_required_fields_are_optional():
    result = generate_pydantic_models(SIMPLE_SPEC)
    assert "Optional[str]" in result
    assert "= None" in result


def test_empty_components_produces_header_only():
    spec = json.dumps(
        {"openapi": "3.1.0", "info": {"title": "x", "version": "1"}, "paths": {}, "components": {"schemas": {}}}
    )
    result = generate_pydantic_models(spec)
    assert "from pydantic import BaseModel" in result
    assert "class " not in result


def test_missing_components_key_produces_header_only():
    spec = json.dumps({"openapi": "3.1.0", "info": {"title": "x", "version": "1"}, "paths": {}})
    result = generate_pydantic_models(spec)
    assert "from pydantic import BaseModel" in result
    assert "class " not in result


def test_ref_type_resolved_to_class_name():
    spec = json.dumps(
        {
            "openapi": "3.1.0",
            "info": {"title": "Ref API", "version": "1.0.0"},
            "paths": {},
            "components": {
                "schemas": {
                    "Address": {
                        "type": "object",
                        "properties": {"street": {"type": "string"}},
                    },
                    "Person": {
                        "type": "object",
                        "required": ["address"],
                        "properties": {
                            "address": {"$ref": "#/components/schemas/Address"},
                        },
                    },
                }
            },
        }
    )
    result = generate_pydantic_models(spec)
    assert "class Address(BaseModel):" in result
    assert "class Person(BaseModel):" in result
    assert ": Address" in result


def test_nested_array_of_refs():
    spec = json.dumps(
        {
            "openapi": "3.1.0",
            "info": {"title": "Array Ref API", "version": "1.0.0"},
            "paths": {},
            "components": {
                "schemas": {
                    "Tag": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                    },
                    "Post": {
                        "type": "object",
                        "properties": {
                            "tags": {"type": "array", "items": {"$ref": "#/components/schemas/Tag"}},
                        },
                    },
                }
            },
        }
    )
    result = generate_pydantic_models(spec)
    assert validate_pydantic_output(result) is True
    assert "list[Tag]" in result


def test_schema_with_no_properties_produces_pass():
    spec = json.dumps(
        {
            "openapi": "3.1.0",
            "info": {"title": "Empty Schema API", "version": "1.0.0"},
            "paths": {},
            "components": {
                "schemas": {
                    "Empty": {"type": "object"},
                }
            },
        }
    )
    result = generate_pydantic_models(spec)
    assert "pass" in result
    assert validate_pydantic_output(result) is True


def test_multiple_schemas_all_present():
    spec = json.dumps(
        {
            "openapi": "3.1.0",
            "info": {"title": "Multi API", "version": "1.0.0"},
            "paths": {},
            "components": {
                "schemas": {
                    "Alpha": {"type": "object", "properties": {"x": {"type": "string"}}},
                    "Beta": {"type": "object", "properties": {"y": {"type": "integer"}}},
                    "Gamma": {"type": "object", "properties": {"z": {"type": "boolean"}}},
                }
            },
        }
    )
    result = generate_pydantic_models(spec)
    assert "class Alpha(BaseModel):" in result
    assert "class Beta(BaseModel):" in result
    assert "class Gamma(BaseModel):" in result
    assert validate_pydantic_output(result) is True


def test_validate_pydantic_output_true_for_valid_code():
    assert validate_pydantic_output("x = 1\n") is True


def test_validate_pydantic_output_false_for_syntax_error():
    assert validate_pydantic_output("def foo(:\n    pass\n") is False


def test_no_subprocess_usage():
    import agent.nodes.pydantic_generator as mod

    assert not hasattr(mod, "subprocess"), "subprocess must not be imported"
