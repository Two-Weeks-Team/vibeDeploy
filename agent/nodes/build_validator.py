import ast
import logging
import tempfile
from pathlib import Path

from ..state import VibeDeployState

logger = logging.getLogger(__name__)


def _write_files_to_tmpdir(files: dict, tmpdir: str) -> None:
    base = Path(tmpdir)
    for rel_path, content in files.items():
        if not isinstance(rel_path, str) or not isinstance(content, str):
            continue
        target = (base / rel_path).resolve()
        if base.resolve() not in target.parents and target != base.resolve():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def _ast_check_python_files(backend_code: dict) -> list[str]:
    errors = []
    for filename, content in backend_code.items():
        if not filename.endswith(".py") or not isinstance(content, str):
            continue
        try:
            ast.parse(content)
        except SyntaxError as exc:
            errors.append(f"{filename}: SyntaxError at line {exc.lineno}: {exc.msg}")
    return errors


async def _run_docker_backend(backend_code: dict, docker_client) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="vibedeploy-build-backend-") as tmpdir:
        _write_files_to_tmpdir(backend_code, tmpdir)
        try:
            docker_client.containers.run(
                "python:3.12-slim",
                "pip install -r requirements.txt && python -c 'import main'",
                volumes={tmpdir: {"bind": "/app", "mode": "rw"}},
                working_dir="/app",
                mem_limit="512m",
                network_mode="none",
                remove=True,
                command="sh -c 'pip install -r requirements.txt && python -c \"import main\"'",
            )
            return True, ""
        except Exception as exc:
            stderr = getattr(exc, "stderr", b"") or b""
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            return False, str(stderr) or str(exc)


async def _run_docker_frontend(frontend_code: dict, docker_client) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="vibedeploy-build-frontend-") as tmpdir:
        _write_files_to_tmpdir(frontend_code, tmpdir)
        try:
            docker_client.containers.run(
                "node:20-slim",
                "npm install && npm run build",
                volumes={tmpdir: {"bind": "/app", "mode": "rw"}},
                working_dir="/app",
                mem_limit="512m",
                network_mode="none",
                remove=True,
                command="sh -c 'npm install && npm run build'",
            )
            return True, ""
        except Exception as exc:
            stderr = getattr(exc, "stderr", b"") or b""
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            return False, str(stderr) or str(exc)


async def build_validator(state: VibeDeployState) -> dict:
    backend_code = state.get("backend_code") or {}
    frontend_code = state.get("frontend_code") or {}

    if backend_code:
        syntax_errors = _ast_check_python_files(backend_code)
        if syntax_errors:
            logger.warning("[BUILD_VALIDATOR] Python syntax errors detected: %s", syntax_errors)
            return {
                "build_validation": {
                    "passed": False,
                    "backend_ok": False,
                    "frontend_ok": None,
                    "errors": syntax_errors,
                }
            }

    try:
        import docker  # type: ignore[import]
        import docker.errors  # type: ignore[import]
    except ImportError:
        logger.warning("[BUILD_VALIDATOR] docker SDK not installed; skipping container validation")
        return {
            "build_validation": {
                "passed": True,
                "skipped": True,
                "reason": "Docker not available",
            }
        }

    try:
        docker_client = docker.from_env()
        docker_client.ping()
    except Exception as exc:
        logger.warning("[BUILD_VALIDATOR] Docker daemon not reachable (%s); skipping container validation", exc)
        return {
            "build_validation": {
                "passed": True,
                "skipped": True,
                "reason": "Docker not available",
            }
        }

    errors: list[str] = []
    backend_ok = True
    frontend_ok = True

    if backend_code and "requirements.txt" in backend_code and "main.py" in backend_code:
        logger.info("[BUILD_VALIDATOR] Running backend build validation in Docker")
        backend_ok, backend_err = await _run_docker_backend(backend_code, docker_client)
        if not backend_ok:
            logger.warning("[BUILD_VALIDATOR] Backend Docker validation failed: %s", backend_err[:500])
            errors.append(f"backend: {backend_err[:500]}")

    if frontend_code and "package.json" in frontend_code:
        logger.info("[BUILD_VALIDATOR] Running frontend build validation in Docker")
        frontend_ok, frontend_err = await _run_docker_frontend(frontend_code, docker_client)
        if not frontend_ok:
            logger.warning("[BUILD_VALIDATOR] Frontend Docker validation failed: %s", frontend_err[:500])
            errors.append(f"frontend: {frontend_err[:500]}")

    passed = backend_ok and frontend_ok
    if passed:
        return {
            "build_validation": {
                "passed": True,
                "backend_ok": backend_ok,
                "frontend_ok": frontend_ok,
            }
        }

    return {
        "build_validation": {
            "passed": False,
            "backend_ok": backend_ok,
            "frontend_ok": frontend_ok,
            "errors": errors,
        }
    }
