"""Tests for agent/nodes/contract_validator.py — Issue #174."""

from __future__ import annotations

import asyncio
import json

from agent.nodes.contract_validator import (
    _build_repair_instructions,
    _extract_pydantic_models,
    _parse_spec_schemas,
    compare_endpoints,
    compare_schemas,
    extract_fastapi_routes,
    validate_contract,
    validate_with_timeout,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

SIMPLE_SPEC = json.dumps(
    {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "1.0"},
        "paths": {
            "/api/users": {"get": {}, "post": {}},
            "/api/users/{id}": {"get": {}, "delete": {}},
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "email": {"type": "string", "format": "email"},
                        "name": {"type": "string"},
                    },
                },
                "CreateUserRequest": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string"},
                        "name": {"type": "string"},
                    },
                },
            }
        },
    }
)

MATCHING_CODE = {
    "main.py": (
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n\n"
        '@app.get("/api/users")\n'
        "def list_users(): pass\n\n"
        '@app.post("/api/users")\n'
        "def create_user(): pass\n\n"
        '@app.get("/api/users/{id}")\n'
        "def get_user(id: int): pass\n\n"
        '@app.delete("/api/users/{id}")\n'
        "def delete_user(id: int): pass\n"
    ),
    "schemas.py": (
        "from pydantic import BaseModel\n\n"
        "class User(BaseModel):\n"
        "    id: int\n"
        "    email: str\n"
        "    name: str\n\n"
        "class CreateUserRequest(BaseModel):\n"
        "    email: str\n"
        "    name: str\n"
    ),
}


# ── extract_fastapi_routes ────────────────────────────────────────────────────


def test_extract_routes_basic():
    code = '@app.get("/items")\ndef list_items(): pass'
    routes = extract_fastapi_routes(code)
    assert routes == [{"method": "GET", "path": "/items"}]


def test_extract_routes_multiple_methods():
    code = (
        '@app.get("/items")\ndef get(): pass\n'
        '@router.post("/items")\ndef post(): pass\n'
        '@app.delete("/items/{id}")\ndef delete(): pass\n'
    )
    routes = extract_fastapi_routes(code)
    assert {"method": "GET", "path": "/items"} in routes
    assert {"method": "POST", "path": "/items"} in routes
    assert {"method": "DELETE", "path": "/items/{id}"} in routes


def test_extract_routes_empty():
    assert extract_fastapi_routes("def plain_function(): pass") == []


# ── _parse_spec_schemas ───────────────────────────────────────────────────────


def test_parse_spec_schemas_happy_path():
    schemas = _parse_spec_schemas(SIMPLE_SPEC)
    assert "User" in schemas
    assert "email" in schemas["User"]
    assert "name" in schemas["User"]
    assert "CreateUserRequest" in schemas


def test_parse_spec_schemas_no_components():
    spec = json.dumps({"openapi": "3.0.0", "paths": {}})
    assert _parse_spec_schemas(spec) == {}


def test_parse_spec_schemas_invalid_json():
    assert _parse_spec_schemas("{not valid json}") == {}


# ── _extract_pydantic_models ──────────────────────────────────────────────────


def test_extract_pydantic_models_basic():
    code = "from pydantic import BaseModel\n\nclass Item(BaseModel):\n    name: str\n    price: float\n"
    models = _extract_pydantic_models({"schemas.py": code})
    assert "Item" in models
    assert "name" in models["Item"]
    assert "price" in models["Item"]


def test_extract_pydantic_models_prefers_schemas_py():
    schemas_code = "from pydantic import BaseModel\n\nclass A(BaseModel):\n    x: int\n"
    models_code = "from pydantic import BaseModel\n\nclass B(BaseModel):\n    y: str\n"
    models = _extract_pydantic_models({"schemas.py": schemas_code, "models.py": models_code})
    assert "A" in models
    assert "B" not in models  # schemas.py takes priority


def test_extract_pydantic_models_no_pydantic():
    code = "class PlainClass:\n    x = 1\n"
    models = _extract_pydantic_models({"main.py": code})
    assert models == {}


# ── compare_schemas ───────────────────────────────────────────────────────────


def test_compare_schemas_no_mismatches():
    expected = {"User": {"id": "integer", "name": "string"}}
    actual = {"User": {"id": "int", "name": "str", "extra_field": "str"}}
    mismatches = compare_schemas(expected, actual)
    assert mismatches == []


def test_compare_schemas_missing_field():
    expected = {"User": {"id": "integer", "email": "string"}}
    actual = {"User": {"id": "int"}}  # missing email
    mismatches = compare_schemas(expected, actual)
    assert len(mismatches) == 1
    assert mismatches[0]["field"] == "email"
    assert mismatches[0]["schema"] == "User"


def test_compare_schemas_missing_model():
    expected = {"MissingModel": {"id": "integer"}}
    actual = {}
    mismatches = compare_schemas(expected, actual)
    assert len(mismatches) == 1
    assert mismatches[0]["field"] is None
    assert "MissingModel" in mismatches[0]["issue"]


def test_compare_schemas_empty_expected():
    assert compare_schemas({}, {"User": {"id": "int"}}) == []


# ── compare_endpoints ─────────────────────────────────────────────────────────


def test_compare_endpoints_all_match():
    spec = [{"method": "GET", "path": "/api/users"}, {"method": "POST", "path": "/api/users"}]
    code = [{"method": "GET", "path": "/api/users"}, {"method": "POST", "path": "/api/users"}]
    result = compare_endpoints(spec, code)
    assert result["passed"] is True
    assert result["matched"] == 2
    assert result["missing"] == []


def test_compare_endpoints_missing():
    spec = [{"method": "GET", "path": "/api/users"}, {"method": "POST", "path": "/api/users"}]
    code = [{"method": "GET", "path": "/api/users"}]
    result = compare_endpoints(spec, code)
    assert result["passed"] is False
    assert "POST /api/users" in result["missing"]


def test_compare_endpoints_extra_allowed():
    spec = [{"method": "GET", "path": "/api/users"}]
    code = [{"method": "GET", "path": "/api/users"}, {"method": "GET", "path": "/health"}]
    result = compare_endpoints(spec, code)
    assert result["passed"] is True
    assert "GET /health" in result["extra"]


def test_compare_endpoints_empty_spec_empty_code():
    result = compare_endpoints([], [])
    assert result["passed"] is True


# ── validate_contract (full integration) ─────────────────────────────────────


def test_validate_contract_passes():
    result = validate_contract(SIMPLE_SPEC, MATCHING_CODE)
    assert result["passed"] is True
    assert result["schema_mismatches"] == []
    assert result["repair_instructions"] == []


def test_validate_contract_missing_endpoint():
    incomplete_code = {
        "main.py": (
            'from fastapi import FastAPI\napp = FastAPI()\n\n@app.get("/api/users")\ndef list_users(): pass\n'
            # missing POST, GET/:id, DELETE/:id
        ),
        "schemas.py": MATCHING_CODE["schemas.py"],
    }
    result = validate_contract(SIMPLE_SPEC, incomplete_code)
    assert result["passed"] is False
    assert len(result["missing"]) > 0
    # repair instructions should tell code_generator to add the missing endpoints
    endpoint_repairs = [r for r in result["repair_instructions"] if r["action"] == "add_endpoint"]
    assert len(endpoint_repairs) > 0


def test_validate_contract_missing_schema_field():
    code_missing_field = {
        "main.py": MATCHING_CODE["main.py"],
        "schemas.py": (
            "from pydantic import BaseModel\n\n"
            "class User(BaseModel):\n"
            "    id: int\n"
            "    name: str\n"
            # missing email
            "\nclass CreateUserRequest(BaseModel):\n"
            "    email: str\n"
            "    name: str\n"
        ),
    }
    result = validate_contract(SIMPLE_SPEC, code_missing_field)
    assert result["passed"] is False
    assert any(m["field"] == "email" and m["schema"] == "User" for m in result["schema_mismatches"])
    field_repairs = [r for r in result["repair_instructions"] if r["action"] == "add_field"]
    assert any(r["field"] == "email" and r["schema"] == "User" for r in field_repairs)


def test_validate_contract_missing_model():
    code_no_schema = {
        "main.py": MATCHING_CODE["main.py"],
        "schemas.py": (
            "from pydantic import BaseModel\n\nclass User(BaseModel):\n    id: int\n    email: str\n    name: str\n"
            # CreateUserRequest is absent
        ),
    }
    result = validate_contract(SIMPLE_SPEC, code_no_schema)
    assert result["passed"] is False
    model_repairs = [r for r in result["repair_instructions"] if r["action"] == "add_model"]
    assert any(r["schema"] == "CreateUserRequest" for r in model_repairs)


def test_validate_contract_invalid_json():
    result = validate_contract("{bad json}", {"main.py": ""})
    # Should not raise; empty spec → vacuously passes endpoint check (0 endpoints), no schemas
    assert isinstance(result, dict)
    assert "passed" in result


def test_validate_contract_result_shape():
    """Ensure the result always has the expected keys."""
    result = validate_contract(SIMPLE_SPEC, MATCHING_CODE)
    for key in ("passed", "total_endpoints", "matched", "missing", "extra", "schema_mismatches", "repair_instructions"):
        assert key in result, f"Key '{key}' missing from result"


# ── _build_repair_instructions ────────────────────────────────────────────────


def test_build_repair_instructions_empty():
    ep_result = {"passed": True, "missing": [], "extra": []}
    assert _build_repair_instructions(ep_result, []) == []


def test_build_repair_instructions_endpoint():
    ep_result = {"passed": False, "missing": ["POST /api/items"], "extra": []}
    instructions = _build_repair_instructions(ep_result, [])
    assert len(instructions) == 1
    assert instructions[0]["action"] == "add_endpoint"
    assert instructions[0]["path"] == "/api/items"
    assert instructions[0]["method"] == "POST"


def test_build_repair_instructions_field():
    ep_result = {"passed": True, "missing": [], "extra": []}
    mismatches = [{"schema": "Item", "field": "price", "issue": "Field 'price' missing from model 'Item'"}]
    instructions = _build_repair_instructions(ep_result, mismatches)
    assert len(instructions) == 1
    assert instructions[0]["action"] == "add_field"
    assert instructions[0]["schema"] == "Item"
    assert instructions[0]["field"] == "price"


def test_build_repair_instructions_missing_model():
    ep_result = {"passed": True, "missing": [], "extra": []}
    mismatches = [{"schema": "Ghost", "field": None, "issue": "Pydantic model 'Ghost' not found"}]
    instructions = _build_repair_instructions(ep_result, mismatches)
    assert instructions[0]["action"] == "add_model"
    assert instructions[0]["schema"] == "Ghost"


# ── validate_with_timeout ─────────────────────────────────────────────────────


def test_validate_with_timeout_success():
    result = asyncio.run(validate_with_timeout(SIMPLE_SPEC, MATCHING_CODE, timeout=10.0))
    assert result["passed"] is True


def test_validate_with_timeout_result_shape():
    result = asyncio.run(validate_with_timeout(SIMPLE_SPEC, MATCHING_CODE))
    for key in ("passed", "total_endpoints", "matched", "missing", "extra", "schema_mismatches", "repair_instructions"):
        assert key in result


def test_validate_with_timeout_timeout_triggers(monkeypatch):
    """Simulate timeout by patching asyncio.wait_for to raise TimeoutError."""
    import agent.nodes.contract_validator as cv_module

    async def fake_wait_for(coro, timeout):  # noqa: RUF029
        raise asyncio.TimeoutError

    monkeypatch.setattr(asyncio, "wait_for", fake_wait_for)
    result = asyncio.run(cv_module.validate_with_timeout(SIMPLE_SPEC, MATCHING_CODE, timeout=0.001))
    assert result["passed"] is False
    assert any("timed out" in e.lower() for e in result.get("errors", []))


def test_validate_with_timeout_custom_timeout_message(monkeypatch):
    import agent.nodes.contract_validator as cv_module

    async def fake_wait_for(coro, timeout):  # noqa: RUF029
        raise asyncio.TimeoutError

    monkeypatch.setattr(asyncio, "wait_for", fake_wait_for)
    result = asyncio.run(cv_module.validate_with_timeout(SIMPLE_SPEC, MATCHING_CODE, timeout=5.0))
    assert "5.0s" in result["errors"][0]
