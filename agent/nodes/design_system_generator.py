from __future__ import annotations

from typing import Any


async def design_system_generator(state: dict[str, Any], config=None) -> dict:
    blueprint = state.get("blueprint") or {}
    design_system = blueprint.get("design_system") or {}
    experience_contract = blueprint.get("experience_contract") or {}
    shared_constants = blueprint.get("shared_constants") or {}
    return {
        "design_system_context": {
            "design_system": design_system,
            "experience_contract": experience_contract,
            "shared_constants": shared_constants,
        },
        "design_preset": str((design_system or {}).get("visual_direction") or ""),
        "phase": "design_system_generated",
    }
