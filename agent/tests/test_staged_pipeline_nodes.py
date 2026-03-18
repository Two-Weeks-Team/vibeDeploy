from __future__ import annotations

import importlib
import json

import pytest

from agent.graph import create_staged_graph
from agent.nodes.api_contract_generator import api_contract_generator_node, generate_api_contract
from agent.nodes.deploy_gate import deploy_gate, route_after_deploy_gate
from agent.nodes.local_runtime_validator import local_runtime_validator
from agent.nodes.per_file_code_generator import backend_generator_node, frontend_generator_node
from agent.nodes.pydantic_generator import pydantic_generator_node
from agent.nodes.scaffold_generator import scaffold_generator_node
from agent.nodes.spec_freeze_gate import spec_freeze_gate
from agent.nodes.type_generator import type_generator_node

BLUEPRINT = {
    "app_name": "demo-app",
    "domain": "health",
    "frontend_files": {
        "src/app/page.tsx": {"purpose": "main page", "imports_from": ["src/lib/api.ts"]},
        "src/lib/api.ts": {"purpose": "typed api client", "imports_from": []},
    },
    "backend_files": {
        "routes.py": {"purpose": "api routes", "imports_from": ["ai_service"]},
        "ai_service.py": {"purpose": "service layer", "imports_from": []},
    },
    "frontend_backend_contract": [
        {
            "frontend_file": "src/lib/api.ts",
            "calls": "GET /api/starter-profiles",
            "backend_file": "routes.py",
            "request_fields": [],
            "response_fields": {"items": {"type": "array"}},
        },
        {
            "frontend_file": "src/lib/api.ts",
            "calls": "POST /api/plan",
            "backend_file": "routes.py",
            "request_fields": ["query", "preferences"],
            "response_fields": {"summary": {"type": "string"}},
        },
    ],
    "design_system": {"visual_direction": "health dashboard"},
}


@pytest.mark.asyncio
async def test_api_contract_and_spec_freeze_happy_path():
    state = {"blueprint": BLUEPRINT}
    contract_result = await api_contract_generator_node(state)
    state.update(contract_result)
    freeze_result = await spec_freeze_gate(state)
    assert freeze_result["spec_frozen"] is True
    assert freeze_result["spec_freeze_errors"] == []


@pytest.mark.asyncio
async def test_spec_freeze_detects_missing_contract():
    result = await spec_freeze_gate({"blueprint": BLUEPRINT, "api_contract": ""})
    assert result["spec_frozen"] is False
    assert "api_contract_missing" in result["spec_freeze_errors"]


@pytest.mark.asyncio
async def test_scaffold_type_and_pydantic_nodes_populate_state():
    state = {"blueprint": BLUEPRINT}
    state.update(await scaffold_generator_node(state))
    state.update(await api_contract_generator_node(state))
    type_result = await type_generator_node(state)
    state.update(type_result)
    pydantic_result = await pydantic_generator_node(state)
    assert "src/types/api.d.ts" in type_result["frontend_code"]
    assert "src/lib/api-client.ts" in type_result["frontend_code"]
    assert "schemas.py" in pydantic_result["backend_code"]


@pytest.mark.asyncio
async def test_backend_and_frontend_generator_nodes_populate_state():
    state = {
        "blueprint": BLUEPRINT,
        "api_contract": generate_api_contract(BLUEPRINT),
        "frontend_code": {"src/app/page.tsx": "existing"},
        "backend_code": {"main.py": "existing"},
    }
    backend_result = await backend_generator_node(state)
    state.update(backend_result)
    frontend_result = await frontend_generator_node(state)
    assert "routes.py" in backend_result["backend_code"]
    assert "src/lib/api.ts" in frontend_result["frontend_code"]
    assert frontend_result["phase"] == "frontend_generated"


@pytest.mark.asyncio
async def test_frontend_generator_uses_llm_when_flag_enabled(monkeypatch):
    async def fake_generate(spec, context):
        return "export default function Page(){ return <main>LLM</main>; }"

    monkeypatch.setenv("VIBEDEPLOY_USE_LLM_PER_FILE_GENERATION", "true")
    monkeypatch.setattr("agent.nodes.per_file_code_generator._generate_file_with_llm", fake_generate)
    state = {
        "blueprint": BLUEPRINT,
        "api_contract": generate_api_contract(BLUEPRINT),
        "frontend_code": {},
        "backend_code": {},
    }
    result = await frontend_generator_node(state)
    assert result["frontend_code"]["src/app/page.tsx"].startswith("export default function Page")


@pytest.mark.asyncio
async def test_local_runtime_validator_fails_without_main():
    result = await local_runtime_validator({"backend_code": {"routes.py": "x=1\n"}})
    assert result["local_runtime_validation"]["passed"] is False
    assert "backend_main_missing" in result["local_runtime_validation"]["errors"]


@pytest.mark.asyncio
async def test_deploy_gate_blocks_skipped_build():
    result = await deploy_gate(
        {
            "spec_frozen": True,
            "wiring_validation": {"passed": True},
            "build_validation": {"passed": True, "skipped": True},
            "local_runtime_validation": {"passed": True},
        }
    )
    assert result["deploy_gate_result"]["passed"] is False
    assert "build_validation_skipped" in result["deploy_gate_result"]["failures"]
    assert route_after_deploy_gate(result) == "__end__"


def test_staged_graph_compiles():
    graph = create_staged_graph()
    assert graph is not None
    if hasattr(graph, "nodes"):
        node_names = set(graph.nodes.keys())
        for expected in ("api_contract_generator", "spec_freeze_gate", "backend_generator", "deploy_gate"):
            assert expected in node_names, f"Missing staged node: {expected}"


def test_generated_api_contract_is_valid_json():
    generated = json.loads(generate_api_contract(BLUEPRINT))
    assert generated["openapi"] == "3.1.0"
    assert "/api/plan" in generated["paths"]


@pytest.mark.asyncio
async def test_api_run_route_works_with_staged_and_llm_flags(app_client, monkeypatch):
    import agent.graph as graph_mod

    monkeypatch.setenv("VIBEDEPLOY_USE_STAGED_PIPELINE", "true")
    monkeypatch.setenv("VIBEDEPLOY_USE_LLM_PER_FILE_GENERATION", "true")
    importlib.reload(graph_mod)

    class MockGraph:
        async def astream_events(self, *args, **kwargs):
            yield {
                "event": "on_chain_end",
                "name": "input_processor",
                "data": {"output": {"phase": "input_processing", "idea": {"title": "Test"}, "idea_summary": "Test"}},
            }
            yield {
                "event": "on_chain_end",
                "name": "doc_generator",
                "data": {"output": {"phase": "doc_generation", "generated_docs": {"prd": "# PRD"}}},
            }

    monkeypatch.setattr(graph_mod, "app", MockGraph())
    resp = await app_client.post("/api/run", json={"prompt": "A meal planner app"})
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
