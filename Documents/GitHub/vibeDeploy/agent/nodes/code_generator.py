from ..state import VibeDeployState


async def code_generator(state: VibeDeployState) -> dict:
    _ = state
    return {
        "frontend_code": {},
        "backend_code": {},
        "phase": "code_generated",
    }
