import json

from agent.nodes.contract_validator import (
    compare_endpoints,
    extract_fastapi_routes,
    validate_contract,
)

SAMPLE_SPEC = {
    "openapi": "3.1.0",
    "info": {"title": "Test API", "version": "1.0.0"},
    "paths": {
        "/api/items": {
            "get": {"summary": "List items", "responses": {"200": {"description": "ok"}}},
            "post": {"summary": "Create item", "responses": {"200": {"description": "ok"}}},
        },
        "/api/items/{id}": {
            "put": {"summary": "Update item", "responses": {"200": {"description": "ok"}}},
            "delete": {"summary": "Delete item", "responses": {"200": {"description": "ok"}}},
        },
    },
    "components": {"schemas": {}},
}

MATCHING_ROUTES_PY = """\
from fastapi import APIRouter

router = APIRouter()

@router.get("/api/items")
async def list_items():
    return []

@router.post("/api/items")
async def create_item():
    return {}

@router.put("/api/items/{id}")
async def update_item(id: str):
    return {}

@router.delete("/api/items/{id}")
async def delete_item(id: str):
    return {}
"""

PARTIAL_ROUTES_PY = """\
from fastapi import APIRouter

router = APIRouter()

@router.get("/api/items")
async def list_items():
    return []

@router.post("/api/items")
async def create_item():
    return {}
"""

EXTRA_ROUTES_PY = """\
from fastapi import FastAPI

app = FastAPI()

@app.get("/api/items")
async def list_items():
    return []

@app.post("/api/items")
async def create_item():
    return {}

@app.put("/api/items/{id}")
async def update_item(id: str):
    return {}

@app.delete("/api/items/{id}")
async def delete_item(id: str):
    return {}

@app.get("/api/health")
async def health():
    return {"status": "ok"}
"""


class TestExtractFastapiRoutes:
    def test_extracts_app_decorator_routes(self):
        code = '@app.get("/api/items")\nasync def f(): ...\n'
        routes = extract_fastapi_routes(code)
        assert routes == [{"method": "GET", "path": "/api/items"}]

    def test_extracts_router_decorator_routes(self):
        code = '@router.post("/api/users")\nasync def f(): ...\n'
        routes = extract_fastapi_routes(code)
        assert routes == [{"method": "POST", "path": "/api/users"}]

    def test_extracts_multiple_methods(self):
        code = (
            '@app.get("/a")\ndef g(): ...\n'
            '@app.post("/b")\ndef h(): ...\n'
            '@app.put("/c")\ndef i(): ...\n'
            '@app.delete("/d")\ndef j(): ...\n'
        )
        routes = extract_fastapi_routes(code)
        assert len(routes) == 4
        methods = {r["method"] for r in routes}
        assert methods == {"GET", "POST", "PUT", "DELETE"}

    def test_empty_code_returns_empty_list(self):
        assert extract_fastapi_routes("") == []

    def test_malformed_code_returns_empty_list(self):
        assert extract_fastapi_routes("this is not python @@@") == []

    def test_method_is_uppercased(self):
        code = '@app.get("/api/x")\ndef f(): ...\n'
        routes = extract_fastapi_routes(code)
        assert routes[0]["method"] == "GET"

    def test_extracts_patch_method(self):
        code = '@app.patch("/api/items/{id}")\nasync def f(): ...\n'
        routes = extract_fastapi_routes(code)
        assert routes == [{"method": "PATCH", "path": "/api/items/{id}"}]


class TestCompareEndpoints:
    def test_all_matched_returns_passed(self):
        spec = [{"method": "GET", "path": "/api/x"}, {"method": "POST", "path": "/api/x"}]
        code = [{"method": "GET", "path": "/api/x"}, {"method": "POST", "path": "/api/x"}]
        result = compare_endpoints(spec, code)
        assert result["passed"] is True
        assert result["matched"] == 2
        assert result["missing"] == []
        assert result["extra"] == []
        assert result["total_endpoints"] == 2

    def test_missing_endpoint_fails(self):
        spec = [{"method": "GET", "path": "/api/x"}, {"method": "POST", "path": "/api/x"}]
        code = [{"method": "GET", "path": "/api/x"}]
        result = compare_endpoints(spec, code)
        assert result["passed"] is False
        assert result["matched"] == 1
        assert "POST /api/x" in result["missing"]
        assert result["extra"] == []

    def test_extra_endpoint_detected(self):
        spec = [{"method": "GET", "path": "/api/x"}]
        code = [{"method": "GET", "path": "/api/x"}, {"method": "DELETE", "path": "/api/x"}]
        result = compare_endpoints(spec, code)
        assert result["passed"] is True
        assert "DELETE /api/x" in result["extra"]

    def test_empty_spec_empty_code_passes(self):
        result = compare_endpoints([], [])
        assert result["passed"] is True
        assert result["total_endpoints"] == 0
        assert result["matched"] == 0

    def test_empty_spec_with_extra_code_endpoints(self):
        result = compare_endpoints([], [{"method": "GET", "path": "/api/x"}])
        assert result["passed"] is False
        assert "GET /api/x" in result["extra"]


class TestValidateContract:
    def test_all_endpoints_match_passes(self):
        spec_json = json.dumps(SAMPLE_SPEC)
        backend = {"routes.py": MATCHING_ROUTES_PY}
        result = validate_contract(spec_json, backend)
        assert result["passed"] is True
        assert result["total_endpoints"] == 4
        assert result["matched"] == 4
        assert result["missing"] == []

    def test_missing_endpoint_fails_with_details(self):
        spec_json = json.dumps(SAMPLE_SPEC)
        backend = {"routes.py": PARTIAL_ROUTES_PY}
        result = validate_contract(spec_json, backend)
        assert result["passed"] is False
        assert result["matched"] == 2
        assert len(result["missing"]) == 2
        assert "PUT /api/items/{id}" in result["missing"]
        assert "DELETE /api/items/{id}" in result["missing"]

    def test_extra_endpoint_detected(self):
        spec_json = json.dumps(SAMPLE_SPEC)
        backend = {"routes.py": EXTRA_ROUTES_PY}
        result = validate_contract(spec_json, backend)
        assert result["passed"] is True
        assert "GET /api/health" in result["extra"]

    def test_fallback_to_main_py_when_no_routes_py(self):
        spec = {
            "openapi": "3.1.0",
            "info": {"title": "T", "version": "1.0"},
            "paths": {"/api/ping": {"get": {"responses": {"200": {"description": "ok"}}}}},
        }
        code = '@app.get("/api/ping")\ndef ping(): return {}\n'
        result = validate_contract(json.dumps(spec), {"main.py": code})
        assert result["passed"] is True
        assert result["matched"] == 1

    def test_empty_spec_empty_backend_passes(self):
        empty_spec = json.dumps({"openapi": "3.1.0", "info": {"title": "T", "version": "1.0"}, "paths": {}})
        result = validate_contract(empty_spec, {})
        assert result["passed"] is True
        assert result["total_endpoints"] == 0

    def test_malformed_json_spec_returns_no_endpoints(self):
        result = validate_contract("NOT JSON {{{", {"routes.py": MATCHING_ROUTES_PY})
        assert result["total_endpoints"] == 0
        assert result["matched"] == 0

    def test_malformed_backend_code_handled_gracefully(self):
        spec_json = json.dumps(SAMPLE_SPEC)
        result = validate_contract(spec_json, {"routes.py": "@@@not valid python@@@"})
        assert result["passed"] is False
        assert result["matched"] == 0
        assert len(result["missing"]) == 4

    def test_searches_all_py_files_when_no_routes_or_main(self):
        spec = {
            "openapi": "3.1.0",
            "info": {"title": "T", "version": "1.0"},
            "paths": {"/api/z": {"get": {"responses": {"200": {"description": "ok"}}}}},
        }
        backend = {
            "other.py": '@app.get("/api/z")\ndef z(): ...\n',
            "requirements.txt": "fastapi\n",
        }
        result = validate_contract(json.dumps(spec), backend)
        assert result["matched"] == 1

    def test_deduplicates_routes_from_code(self):
        spec = {
            "openapi": "3.1.0",
            "info": {"title": "T", "version": "1.0"},
            "paths": {"/api/x": {"get": {"responses": {"200": {"description": "ok"}}}}},
        }
        code = '@app.get("/api/x")\ndef a(): ...\n@app.get("/api/x")\ndef b(): ...\n'
        result = validate_contract(json.dumps(spec), {"routes.py": code})
        assert result["matched"] == 1
        assert result["passed"] is True

    def test_result_contains_all_required_keys(self):
        result = validate_contract("{}", {})
        assert set(result.keys()) == {"passed", "total_endpoints", "matched", "missing", "extra"}
