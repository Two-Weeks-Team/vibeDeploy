import asyncio
import os

import httpx

DO_API_BASE = "https://api.digitalocean.com/v2"


def _headers() -> dict:
    token = os.getenv("DIGITALOCEAN_API_TOKEN")
    if not token:
        raise ValueError("DIGITALOCEAN_API_TOKEN not set")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


async def deploy_to_digitalocean(repo_url: str, app_spec: dict) -> dict:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{DO_API_BASE}/apps",
                headers=_headers(),
                json={"spec": app_spec},
            )
            response.raise_for_status()
            data = response.json()

            app = data.get("app", {})
            return {
                "app_id": app.get("id", ""),
                "status": "deploying",
                "default_ingress": app.get("default_ingress", ""),
            }

    except httpx.HTTPStatusError as e:
        return {"app_id": "", "status": "error", "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except ValueError as e:
        return {"app_id": "", "status": "error", "error": str(e)}
    except Exception as e:
        return {"app_id": "", "status": "error", "error": str(e)[:200]}


async def wait_for_deployment(
    app_id: str,
    timeout_seconds: int = 300,
    poll_interval: int = 10,
) -> str:
    if not app_id:
        return ""

    elapsed = 0
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            while elapsed < timeout_seconds:
                response = await client.get(
                    f"{DO_API_BASE}/apps/{app_id}",
                    headers=_headers(),
                )
                response.raise_for_status()
                app = response.json().get("app", {})
                active_deployment = app.get("active_deployment", {})
                phase = active_deployment.get("phase", "UNKNOWN")

                if phase == "ACTIVE":
                    return app.get("live_url", app.get("default_ingress", ""))

                if phase in ("ERROR", "CANCELED"):
                    return ""

                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

        return ""

    except Exception:
        return ""


async def get_app_status(app_id: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{DO_API_BASE}/apps/{app_id}",
                headers=_headers(),
            )
            response.raise_for_status()
            app = response.json().get("app", {})

            return {
                "app_id": app.get("id", ""),
                "phase": app.get("active_deployment", {}).get("phase", "UNKNOWN"),
                "live_url": app.get("live_url", ""),
                "default_ingress": app.get("default_ingress", ""),
                "updated_at": app.get("updated_at", ""),
            }

    except Exception as e:
        return {"app_id": app_id, "phase": "ERROR", "error": str(e)[:200]}


def build_app_spec(
    name: str,
    repo_url: str,
    branch: str = "main",
) -> dict:
    github_parts = repo_url.replace("https://github.com/", "").replace(".git", "")

    return {
        "name": name,
        "region": "nyc",
        "services": [
            {
                "name": f"{name}-api",
                "github": {
                    "repo": github_parts,
                    "branch": branch,
                    "deploy_on_push": True,
                },
                "build_command": "pip install -r requirements.txt",
                "run_command": "uvicorn main:app --host 0.0.0.0 --port 8080",
                "http_port": 8080,
                "instance_count": 1,
                "instance_size_slug": "apps-s-1vcpu-0.5gb",
                "source_dir": "/",
            },
        ],
        "static_sites": [
            {
                "name": f"{name}-web",
                "github": {
                    "repo": github_parts,
                    "branch": branch,
                    "deploy_on_push": True,
                },
                "build_command": "npm install && npm run build",
                "output_dir": ".next",
                "source_dir": "/web",
                "environment_slug": "node-js",
            },
        ],
    }
