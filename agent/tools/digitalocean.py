import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

import httpx
from gradient_adk.tracing import trace_tool

logger = logging.getLogger(__name__)

DO_API_BASE = "https://api.digitalocean.com/v2"

# TTL for generated apps (default 2 hours). Override via DEPLOY_APP_TTL_HOURS env var.
_DEFAULT_APP_TTL_HOURS = 2
_PROTECTED_APP_NAMES = frozenset({"vibedeploy"})


def _headers() -> dict:
    token = os.getenv("DIGITALOCEAN_API_TOKEN")
    if not token:
        raise ValueError("DIGITALOCEAN_API_TOKEN not set")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


@trace_tool("deploy_to_digitalocean")
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


@trace_tool("wait_for_app_platform_deployment")
async def wait_for_deployment(
    app_id: str,
    timeout_seconds: int = 420,
    poll_interval: int = 10,
    on_phase_change: Callable[[str], Awaitable[None]] | None = None,
) -> str:
    if not app_id:
        return ""

    elapsed = 0
    last_phase = ""
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

                if phase != last_phase:
                    last_phase = phase
                    if on_phase_change is not None:
                        await on_phase_change(phase)

                if phase == "ACTIVE":
                    return app.get("live_url", app.get("default_ingress", ""))

                if phase in ("ERROR", "CANCELED"):
                    return ""

                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

        return ""

    except Exception:
        return ""


async def cleanup_expired_apps() -> dict:
    """Delete generated apps older than the configured TTL. Protects vibedeploy."""
    ttl_hours = max(1, int(os.getenv("DEPLOY_APP_TTL_HOURS", str(_DEFAULT_APP_TTL_HOURS))))
    try:
        apps = await list_apps()
    except Exception:
        return {"status": "error", "error": "failed to list apps"}

    now = datetime.now(timezone.utc)
    deleted = []
    skipped = []

    for app in apps:
        name = app.get("spec", {}).get("name", "")
        app_id = app.get("id", "")
        if not app_id or name in _PROTECTED_APP_NAMES:
            continue
        created_str = app.get("created_at", "")
        if not created_str:
            continue
        try:
            created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        age_hours = (now - created).total_seconds() / 3600
        if age_hours < ttl_hours:
            skipped.append({"name": name, "age_hours": round(age_hours, 1)})
            continue
        logger.info("[TTL] Deleting expired app %s (age=%.1fh, ttl=%dh)", name, age_hours, ttl_hours)
        result = await delete_app(app_id)
        deleted.append({"name": name, "app_id": app_id, "age_hours": round(age_hours, 1), "result": result.get("status")})

    return {"deleted": deleted, "skipped": skipped, "ttl_hours": ttl_hours}


async def _ttl_cleanup_loop(interval_seconds: int = 3600) -> None:
    """Background loop that periodically cleans expired apps."""
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            if not os.getenv("DIGITALOCEAN_API_TOKEN"):
                continue
            result = await cleanup_expired_apps()
            if result.get("deleted"):
                logger.info("[TTL] Cleanup result: %d deleted", len(result["deleted"]))
        except Exception:
            logger.exception("[TTL] Cleanup loop error")


@trace_tool("get_app_platform_status")
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


@trace_tool("list_app_platform_apps")
async def list_apps(per_page: int = 50) -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{DO_API_BASE}/apps",
                params={"per_page": per_page},
                headers=_headers(),
            )
            response.raise_for_status()
            return response.json().get("apps", [])
    except Exception:
        return []


@trace_tool("delete_app_platform_app")
async def delete_app(app_id: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{DO_API_BASE}/apps/{app_id}",
                headers=_headers(),
            )
            response.raise_for_status()
            return {"status": "deleted", "app_id": app_id}
    except httpx.HTTPStatusError as e:
        return {"status": "error", "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}


@trace_tool("get_app_platform_deploy_logs")
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


@trace_tool("redeploy_app_platform_app")
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
    # Use separate credentials for generated apps — NEVER share the host's own DB.
    generated_db_url = os.getenv("GENERATED_APP_DATABASE_URL", "")
    # Apply the same psycopg scheme conversion to generated app DB URL
    if generated_db_url.startswith("postgresql+asyncpg://"):
        generated_db_url = generated_db_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    elif generated_db_url.startswith("postgres://"):
        generated_db_url = generated_db_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif generated_db_url.startswith("postgresql://") and "+psycopg" not in generated_db_url:
        generated_db_url = generated_db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if generated_db_url:
        envs.append({"key": "DATABASE_URL", "value": generated_db_url, "scope": "RUN_TIME", "type": "SECRET"})
        envs.append({"key": "POSTGRES_URL", "value": generated_db_url, "scope": "RUN_TIME", "type": "SECRET"})
    generated_inference_key = os.getenv("GENERATED_APP_INFERENCE_KEY", "")
    if generated_inference_key:
        envs.append({"key": "GRADIENT_MODEL_ACCESS_KEY", "value": generated_inference_key, "scope": "RUN_TIME", "type": "SECRET"})
        envs.append(
            {"key": "DIGITALOCEAN_INFERENCE_KEY", "value": generated_inference_key, "scope": "RUN_TIME", "type": "SECRET"}
        )
    envs.append({"key": "DO_INFERENCE_MODEL", "value": "anthropic-claude-4.6-sonnet", "scope": "RUN_TIME"})

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
            "build_command": "if [ -s package-lock.json ]; then npm ci || npm install; else npm install; fi && npm run build",
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
