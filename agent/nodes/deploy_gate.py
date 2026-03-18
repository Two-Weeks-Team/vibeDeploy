from __future__ import annotations


async def deploy_gate(state: dict, config=None) -> dict:
    build_validation = state.get("build_validation") or {}
    wiring_validation = state.get("wiring_validation") or {}
    runtime_validation = state.get("local_runtime_validation") or {}
    spec_frozen = bool(state.get("spec_frozen"))

    failures: list[str] = []
    if not spec_frozen:
        failures.append("spec_not_frozen")
    if not wiring_validation.get("passed"):
        failures.append("wiring_validation_failed")
    if not build_validation.get("passed"):
        failures.append("build_validation_failed")
    if build_validation.get("skipped"):
        failures.append("build_validation_skipped")
    if not runtime_validation.get("passed"):
        failures.append("local_runtime_failed")

    passed = not failures
    return {
        "deploy_gate_result": {"passed": passed, "failures": failures},
        "phase": "deploy_gate_passed" if passed else "deploy_gate_blocked",
        "error": "; ".join(failures) if failures else None,
    }


def route_after_deploy_gate(state: dict) -> str:
    result = state.get("deploy_gate_result") or {}
    return "deployer" if result.get("passed") else "__end__"
