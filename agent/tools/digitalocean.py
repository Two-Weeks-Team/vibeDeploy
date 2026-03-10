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
    timeout_seconds: int = 420,
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


async def get_deploy_error_logs(app_id: str, deployment_id: str = "") -> str:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            if not deployment_id:
                resp = await client.get(
                    f"{DO_API_BASE}/apps/{app_id}/deployments?per_page=1",
                    headers=_headers(),
                )
                resp.raise_for_status()
                deployments = resp.json().get("deployments", [])
                if not deployments:
                    return ""
                deployment_id = deployments[0]["id"]
                deploy_data = deployments[0]
            else:
                resp = await client.get(
                    f"{DO_API_BASE}/apps/{app_id}/deployments/{deployment_id}",
                    headers=_headers(),
                )
                resp.raise_for_status()
                deploy_data = resp.json().get("deployment", {})

            if deploy_data.get("phase") not in ("ERROR", "FAILED"):
                return ""

            spec = deploy_data.get("spec", {})
            components = [s.get("name", "") for s in spec.get("services", [])]
            components += [s.get("name", "") for s in spec.get("static_sites", [])]
            if not components:
                app_resp = await client.get(f"{DO_API_BASE}/apps/{app_id}", headers=_headers())
                app_resp.raise_for_status()
                app_spec = app_resp.json().get("app", {}).get("spec", {})
                components = [s.get("name", "") for s in app_spec.get("services", [])]

            logs_parts = []
            for comp in components:
                if not comp:
                    continue
                for log_type in ("DEPLOY", "BUILD"):
                    try:
                        log_resp = await client.get(
                            f"{DO_API_BASE}/apps/{app_id}/deployments/{deployment_id}/logs",
                            params={"type": log_type, "component_name": comp},
                            headers=_headers(),
                        )
                        log_resp.raise_for_status()
                        log_data = log_resp.json()
                        urls = log_data.get("historic_urls", [])
                        if urls:
                            content_resp = await client.get(urls[0], follow_redirects=True, timeout=30.0)
                            if content_resp.status_code == 200:
                                text = content_resp.text
                                if not text or len(text) < 100:
                                    continue
                                if log_type == "BUILD" and "build complete" in text.lower():
                                    continue
                                logs_parts.append(f"=== {comp} {log_type} ===\n{text[-2000:]}")
                    except Exception:
                        continue

            combined = "\n\n".join(logs_parts)
            return combined[:4000] if combined else ""
    except Exception:
        return ""


async def redeploy_app(app_id: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{DO_API_BASE}/apps/{app_id}/deployments",
                headers=_headers(),
                json={},
            )
            resp.raise_for_status()
            deployment = resp.json().get("deployment", {})
            return {
                "deployment_id": deployment.get("id", ""),
                "status": "deploying",
            }
    except httpx.HTTPStatusError as e:
        return {"status": "error", "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}


def build_app_spec(
    name: str,
    repo_url: str,
    branch: str = "master",
    has_frontend: bool = False,
) -> dict:
    github_parts = repo_url.replace("https://github.com/", "").replace(".git", "")

    # Build env vars for the generated app from our own env
    db_url = os.getenv("DATABASE_URL", "")
    # Convert to psycopg scheme for generated apps (they use sync psycopg)
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    elif db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif db_url.startswith("postgresql://") and "+psycopg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

    envs = []
    if db_url:
        envs.append({"key": "DATABASE_URL", "value": db_url, "scope": "RUN_TIME", "type": "SECRET"})
        envs.append({"key": "POSTGRES_URL", "value": db_url, "scope": "RUN_TIME", "type": "SECRET"})
    inference_key = os.getenv("DIGITALOCEAN_INFERENCE_KEY", "")
    if inference_key:
        envs.append(
            {"key": "DIGITALOCEAN_INFERENCE_KEY", "value": inference_key, "scope": "RUN_TIME", "type": "SECRET"}
        )
    envs.append({"key": "DO_INFERENCE_MODEL", "value": "openai-gpt-oss-120b", "scope": "RUN_TIME"})

    service: dict = {
        "name": f"{name[:28]}-api",
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
    }
    if envs:
        service["envs"] = envs

    spec: dict = {
        "name": name[:32],
        "region": "nyc",
        "services": [service],
    }

    if has_frontend:
        api_name = f"{name[:28]}-api"
        web_name = f"{name[:28]}-web"
        web_service: dict = {
            "name": web_name,
            "github": {
                "repo": github_parts,
                "branch": branch,
                "deploy_on_push": True,
            },
            "build_command": "npm install && npm run build",
            "run_command": "npm start",
            "http_port": 3000,
            "instance_count": 1,
            "instance_size_slug": "apps-s-1vcpu-0.5gb",
            "source_dir": "/web",
            "environment_slug": "node-js",
        }
        spec["services"].append(web_service)
        spec["ingress"] = {
            "rules": [
                {"match": {"path": {"prefix": "/api"}}, "component": {"name": api_name}},
                {"match": {"path": {"prefix": "/"}}, "component": {"name": web_name}},
            ]
        }

    return spec
