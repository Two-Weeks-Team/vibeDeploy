from ..state import VibeDeployState


async def deployer(state: VibeDeployState) -> dict:
    _ = state
    return {
        "deploy_result": {
            "app_id": "stub-app-id",
            "live_url": "https://example.ondigitalocean.app",
            "github_repo": "https://github.com/example/vibedeploy-stub",
            "status": "deployed",
        },
        "phase": "deployed",
    }
