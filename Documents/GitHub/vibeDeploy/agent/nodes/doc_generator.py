from ..state import VibeDeployState


async def doc_generator(state: VibeDeployState) -> dict:
    _ = state
    return {
        "generated_docs": {
            "prd": "",
            "tech_spec": "",
            "api_spec": "",
            "db_schema": "",
            "app_spec_yaml": "",
        },
        "phase": "docs_generated",
    }
