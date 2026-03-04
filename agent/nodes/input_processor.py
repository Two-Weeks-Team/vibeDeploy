from ..state import VibeDeployState


async def input_processor(state: VibeDeployState) -> dict:
    """Parse input (text or YouTube URL) and structurize idea."""
    # TODO: Implement in issue #3
    return {
        "input_type": "text",
        "idea": {
            "summary": state.get("raw_input", ""),
            "features": [],
            "target_users": "",
        },
        "idea_summary": state.get("raw_input", ""),
        "phase": "input_processed",
    }
