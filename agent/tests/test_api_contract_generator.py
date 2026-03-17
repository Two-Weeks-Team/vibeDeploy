import json

import pytest
from pydantic import ValidationError

from agent.nodes.api_contract_generator import (
    OpenAPISpec,
    generate_api_contract,
    validate_openapi_spec,
)

SAMPLE_BLUEPRINT = {
    "app_name": "queue-bite",
    "frontend_backend_contract": [
        {
            "method": "GET",
            "path": "/api/queues",
            "description": "List all queues",
            "request_body": None,
            "response_body": {"queues": {"type": "array", "items": {"type": "object"}}},
        },
        {
            "method": "POST",
            "path": "/api/queues",
            "description": "Create a new queue",
            "request_body": {"name": {"type": "string"}, "capacity": {"type": "integer"}},
            "response_body": {"id": {"type": "string"}, "status": {"type": "string"}},
        },
        {
            "method": "GET",
            "path": "/api/wait-time",
            "description": "AI-predicted wait time",
            "request_body": None,
            "response_body": {"minutes": {"type": "integer"}, "confidence": {"type": "number"}},
        },
    ],
}


def test_generate_produces_valid_json():
    result = generate_api_contract(SAMPLE_BLUEPRINT)
    parsed = json.loads(result)
    assert isinstance(parsed, dict)


def test_openapi_model_validates_valid_spec():
    spec = OpenAPISpec(
        openapi="3.1.0",
        info={"title": "Test API", "version": "1.0.0"},
        paths={"/api/items": {"get": {"responses": {"200": {"description": "ok"}}}}},
        components={"schemas": {}},
    )
    assert spec.openapi == "3.1.0"
    assert "title" in spec.info


def test_openapi_model_default_openapi_version():
    spec = OpenAPISpec(info={"title": "x", "version": "1"}, paths={})
    assert spec.openapi == "3.1.0"


def test_openapi_model_rejects_missing_info():
    with pytest.raises((ValidationError, Exception)):
        OpenAPISpec.model_validate({"paths": {}})


def test_all_contract_endpoints_appear_in_paths():
    result = generate_api_contract(SAMPLE_BLUEPRINT)
    spec = json.loads(result)
    for item in SAMPLE_BLUEPRINT["frontend_backend_contract"]:
        assert item["path"] in spec["paths"], f"{item['path']} missing from paths"


def test_components_schemas_are_populated():
    result = generate_api_contract(SAMPLE_BLUEPRINT)
    spec = json.loads(result)
    assert "components" in spec
    assert "schemas" in spec["components"]
    assert len(spec["components"]["schemas"]) > 0


def test_empty_contract_produces_minimal_valid_spec():
    blueprint = {"app_name": "empty-app", "frontend_backend_contract": []}
    result = generate_api_contract(blueprint)
    spec = json.loads(result)
    assert spec["openapi"] == "3.1.0"
    assert "info" in spec
    assert spec["paths"] == {}


def test_info_section_has_title_and_version():
    result = generate_api_contract(SAMPLE_BLUEPRINT)
    spec = json.loads(result)
    assert "title" in spec["info"]
    assert "version" in spec["info"]
    assert spec["info"]["title"] == "queue-bite"


def test_paths_have_correct_http_methods():
    result = generate_api_contract(SAMPLE_BLUEPRINT)
    spec = json.loads(result)
    assert "get" in spec["paths"]["/api/queues"]
    assert "post" in spec["paths"]["/api/queues"]
    assert "get" in spec["paths"]["/api/wait-time"]


def test_validate_openapi_spec_returns_true_for_valid():
    result = generate_api_contract(SAMPLE_BLUEPRINT)
    assert validate_openapi_spec(result) is True


def test_validate_openapi_spec_returns_false_for_invalid():
    assert validate_openapi_spec("not valid json") is False
    assert validate_openapi_spec('{"something": "else"}') is False


def test_blueprint_native_calls_format():
    blueprint = {
        "app_name": "native-app",
        "frontend_backend_contract": [
            {
                "frontend_file": "src/lib/api.ts",
                "calls": "POST /api/plan",
                "backend_file": "routes.py",
                "request_fields": ["query", "preferences"],
                "response_fields": ["summary", "items"],
            }
        ],
    }
    result = generate_api_contract(blueprint)
    spec = json.loads(result)
    assert "/api/plan" in spec["paths"]
    assert "post" in spec["paths"]["/api/plan"]


def test_post_endpoint_has_request_body():
    result = generate_api_contract(SAMPLE_BLUEPRINT)
    spec = json.loads(result)
    post_op = spec["paths"]["/api/queues"]["post"]
    assert "requestBody" in post_op


def test_get_endpoint_has_no_request_body():
    result = generate_api_contract(SAMPLE_BLUEPRINT)
    spec = json.loads(result)
    get_op = spec["paths"]["/api/queues"]["get"]
    assert "requestBody" not in get_op


def test_no_llm_calls_in_generate(monkeypatch):
    import agent.nodes.api_contract_generator as mod

    original_attrs = [a for a in dir(mod) if "llm" in a.lower() or "invoke" in a.lower()]
    assert original_attrs == [], f"Unexpected LLM-related attributes found: {original_attrs}"

    result = generate_api_contract(SAMPLE_BLUEPRINT)
    assert json.loads(result)["openapi"] == "3.1.0"
