from __future__ import annotations

import json

import pytest

from agent.graph import create_staged_graph
from agent.nodes.api_contract_generator import api_contract_generator_node, generate_api_contract
from agent.nodes.deploy_gate import deploy_gate, route_after_deploy_gate
from agent.nodes.local_runtime_validator import local_runtime_validator
from agent.nodes.pydantic_generator import pydantic_generator_node
from agent.nodes.scaffold_generator import scaffold_generator_node
from agent.nodes.spec_freeze_gate import spec_freeze_gate
from agent.nodes.type_generator import type_generator_node

BLUEPRINT = {
    "app_name": "demo-app",
    "domain": "health",
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


def test_generated_api_contract_is_valid_json():
    generated = json.loads(generate_api_contract(BLUEPRINT))
    assert generated["openapi"] == "3.1.0"
    assert "/api/plan" in generated["paths"]
