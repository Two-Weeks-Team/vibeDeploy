async def deploy_to_digitalocean(repo_url: str, app_spec: str) -> dict:
    _ = (repo_url, app_spec)
    return {"app_id": "stub-app-id"}


async def wait_for_deployment(app_id: str) -> str:
    _ = app_id
    return "https://example.ondigitalocean.app"
