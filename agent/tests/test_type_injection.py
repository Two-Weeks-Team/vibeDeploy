import ast
import json

from agent.nodes.type_injection import inject_types_into_state

MINIMAL_SPEC = json.dumps(
    {
        "openapi": "3.1.0",
        "info": {"title": "TestApp", "version": "1.0.0"},
        "paths": {
            "/items": {
                "get": {
                    "summary": "List items",
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Item"}}},
                        }
                    },
                },
                "post": {
                    "summary": "Create item",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ItemRequest"}}},
                    },
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Item"}}},
                        }
                    },
                },
            }
        },
        "components": {
            "schemas": {
                "Item": {
                    "type": "object",
                    "required": ["id", "name"],
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "active": {"type": "boolean"},
                    },
                },
                "ItemRequest": {
                    "type": "object",
                    "required": ["name"],
                    "properties": {
                        "name": {"type": "string"},
                    },
                },
            }
        },
    }
)


def test_valid_contract_injects_three_files():
    result = inject_types_into_state({"api_contract": MINIMAL_SPEC})
    assert "frontend_code" in result
    assert "backend_code" in result
    assert "src/types/api.d.ts" in result["frontend_code"]
    assert "src/lib/api.ts" in result["frontend_code"]
    assert "schemas.py" in result["backend_code"]


def test_missing_api_contract_is_noop():
    result = inject_types_into_state({})
    assert result == {}


def test_none_api_contract_is_noop():
    result = inject_types_into_state({"api_contract": None})
    assert result == {}


def test_empty_string_api_contract_is_noop():
    result = inject_types_into_state({"api_contract": ""})
    assert result == {}


def test_whitespace_only_api_contract_is_noop():
    result = inject_types_into_state({"api_contract": "   \n\t  "})
    assert result == {}


def test_frontend_code_key_is_ts_types():
    result = inject_types_into_state({"api_contract": MINIMAL_SPEC})
    dts = result["frontend_code"]["src/types/api.d.ts"]
    assert "export interface Item {" in dts or "DO NOT EDIT" in dts


def test_frontend_code_key_is_api_client():
    result = inject_types_into_state({"api_contract": MINIMAL_SPEC})
    client = result["frontend_code"]["src/lib/api.ts"]
    assert "ApiError" in client
    assert "fetch" in client


def test_backend_code_key_is_schemas_py():
    result = inject_types_into_state({"api_contract": MINIMAL_SPEC})
    schemas = result["backend_code"]["schemas.py"]
    assert "class Item(BaseModel):" in schemas
    assert "from pydantic import BaseModel" in schemas


def test_existing_frontend_code_preserved():
    existing = {"some/existing/file.ts": "const x = 1;"}
    result = inject_types_into_state({"api_contract": MINIMAL_SPEC, "frontend_code": existing})
    assert result["frontend_code"]["some/existing/file.ts"] == "const x = 1;"
    assert "src/types/api.d.ts" in result["frontend_code"]


def test_existing_backend_code_preserved():
    existing = {"main.py": "print('hello')"}
    result = inject_types_into_state({"api_contract": MINIMAL_SPEC, "backend_code": existing})
    assert result["backend_code"]["main.py"] == "print('hello')"
    assert "schemas.py" in result["backend_code"]


def test_generated_ts_types_contains_header():
    result = inject_types_into_state({"api_contract": MINIMAL_SPEC})
    dts = result["frontend_code"]["src/types/api.d.ts"]
    assert "Auto-generated" in dts or "DO NOT EDIT" in dts or "export interface" in dts


def test_generated_ts_client_has_api_base_url():
    result = inject_types_into_state({"api_contract": MINIMAL_SPEC})
    client = result["frontend_code"]["src/lib/api.ts"]
    assert "API_BASE_URL" in client


def test_generated_pydantic_passes_ast_parse():
    result = inject_types_into_state({"api_contract": MINIMAL_SPEC})
    schemas = result["backend_code"]["schemas.py"]
    ast.parse(schemas)


def test_invalid_json_api_contract_returns_error_comment_for_ts():
    result = inject_types_into_state({"api_contract": "{not valid json{{{"})
    dts = result["frontend_code"]["src/types/api.d.ts"]
    assert dts.startswith("//")


def test_invalid_json_api_contract_returns_error_comment_for_pydantic():
    result = inject_types_into_state({"api_contract": "{not valid json{{{"})
    schemas = result["backend_code"]["schemas.py"]
    assert "Error" in schemas or schemas.startswith("#")


def test_no_existing_frontend_code_starts_empty():
    result = inject_types_into_state({"api_contract": MINIMAL_SPEC})
    assert len(result["frontend_code"]) == 2


def test_no_existing_backend_code_starts_empty():
    result = inject_types_into_state({"api_contract": MINIMAL_SPEC})
    assert len(result["backend_code"]) == 1


def test_ts_client_has_get_function():
    result = inject_types_into_state({"api_contract": MINIMAL_SPEC})
    client = result["frontend_code"]["src/lib/api.ts"]
    assert "getItems" in client


def test_ts_client_has_post_function():
    result = inject_types_into_state({"api_contract": MINIMAL_SPEC})
    client = result["frontend_code"]["src/lib/api.ts"]
    assert "postItems" in client
