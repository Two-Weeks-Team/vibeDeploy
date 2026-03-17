from __future__ import annotations

from agent.nodes.pydantic_generator import generate_pydantic_models
from agent.nodes.type_generator import generate_api_client, generate_api_dts

_TS_TYPES_KEY = "src/types/api.d.ts"
_TS_CLIENT_KEY = "src/lib/api.ts"
_PY_SCHEMAS_KEY = "schemas.py"


def inject_types_into_state(state: dict) -> dict:
    api_contract: str | None = state.get("api_contract")
    if not api_contract or not api_contract.strip():
        return {}

    ts_types = generate_api_dts(api_contract)
    ts_client = generate_api_client(api_contract)

    try:
        py_schemas = generate_pydantic_models(api_contract)
    except Exception:
        # generate_pydantic_models raises json.JSONDecodeError on invalid JSON input
        py_schemas = "# Error: could not generate Pydantic models from api_contract\n"

    frontend_code = dict(state.get("frontend_code") or {})
    backend_code = dict(state.get("backend_code") or {})

    frontend_code[_TS_TYPES_KEY] = ts_types
    frontend_code[_TS_CLIENT_KEY] = ts_client
    backend_code[_PY_SCHEMAS_KEY] = py_schemas

    return {
        "frontend_code": frontend_code,
        "backend_code": backend_code,
    }
