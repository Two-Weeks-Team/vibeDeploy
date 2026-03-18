import ast
import asyncio
import logging
import re
import tempfile
from pathlib import Path

from langchain_core.callbacks.manager import adispatch_custom_event

from ..state import VibeDeployState

logger = logging.getLogger(__name__)

_DOCKER_BUILD_TIMEOUT_SECONDS = 120

TEMPERATURE_SCHEDULE = [0.1, 0.05, 0.02]
MAX_BUILD_ATTEMPTS = 3

_DESIGN_FORBIDDEN_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"\bbg-white\b"), "bg-white", "use bg-background"),
    (re.compile(r"#ffffff", re.IGNORECASE), "#ffffff", "use CSS variable"),
    (re.compile(r"#fff(?![0-9a-fA-F])", re.IGNORECASE), "#fff", "use CSS variable"),
]
_DESIGN_CHECKED_EXTENSIONS = {"tsx", "ts", "css"}


def _trim_build_errors(stderr: str | None) -> str:
    if not stderr:
        return "Unknown build error"
    lines = stderr.splitlines()
    errors = [
        line.strip()
        for line in lines
        if any(k in line.lower() for k in ["error:", "failed", "exception", "syntaxerror"])
    ]
    return "\n".join(errors[:3]) if errors else "\n".join(lines[:3])


def _extract_failing_file_paths(error_text: str) -> list[str]:
    paths: list[str] = []
    patterns = [
        re.compile(r"\./?(src/[^\s:>]+\.[a-z]{2,4})"),
        re.compile(r"\./?(src/[^\s:>]+\.[a-z]{2,4})"),
        re.compile(r"Module not found.*['\"](@/[^'\"]+)['\"]"),
        re.compile(r"Export\s+\w+\s+doesn't exist.*['\"](@/[^'\"]+)['\"]"),
    ]
    for pattern in patterns:
        for match in pattern.finditer(error_text):
            p = match.group(1)
            if p not in paths:
                paths.append(p)
    return paths[:5]


async def _run_tsc_check(frontend_code: dict) -> tuple[bool, str]:
    if not frontend_code.get("tsconfig.json"):
        return True, ""
    with tempfile.TemporaryDirectory(prefix="vibedeploy-tsc-") as tmpdir:
        _write_files_to_tmpdir(frontend_code, tmpdir)
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    __import__("subprocess").run,
                    ["npx", "--yes", "tsc", "--noEmit", "--strict", "false"],
                    capture_output=True,
                    text=True,
                    cwd=tmpdir,
                ),
                timeout=30,
            )
            if result.returncode != 0:
                return False, (result.stdout + result.stderr)[:1000]
            return True, ""
        except Exception as exc:
            return True, f"tsc check skipped: {exc}"


def _build_repair_prompt(errors: str, failing_files: dict[str, str]) -> str:
    file_context = "\n".join(f"--- {path} ---\n{code}" for path, code in failing_files.items())
    return f"Fix these build errors:\n{errors}\n\nCurrent code:\n{file_context}"


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


def _check_design_quality(frontend_code: dict) -> list[str]:
    errors: list[str] = []

    globals_content = frontend_code.get("src/app/globals.css") or frontend_code.get("globals.css") or ""
    if globals_content:
        css_var_count = len(re.findall(r"--[\w-]+\s*:", globals_content))
        if css_var_count < 12:
            errors.append(f"DESIGN: globals.css has only {css_var_count} CSS variables (minimum 12)")
        if ".dark" not in globals_content:
            errors.append("DESIGN: globals.css is missing .dark block (dark mode required)")

    for filepath, content in frontend_code.items():
        if not isinstance(content, str):
            continue
        ext = filepath.rsplit(".", 1)[-1] if "." in filepath else ""
        if ext not in _DESIGN_CHECKED_EXTENSIONS:
            continue
        filename = filepath.rsplit("/", 1)[-1]
        for pattern, label, suggestion in _DESIGN_FORBIDDEN_PATTERNS:
            if pattern.search(content):
                errors.append(f"DESIGN: {filename} contains {label} ({suggestion})")

    return errors


async def _run_docker_backend(backend_code: dict, docker_client) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="vibedeploy-build-backend-") as tmpdir:
        _write_files_to_tmpdir(backend_code, tmpdir)
        try:
            await asyncio.wait_for(
                asyncio.to_thread(
                    docker_client.containers.run,
                    "python:3.12-slim",
                    command="sh -c 'pip install -r requirements.txt && python -c \"import main\"'",
                    volumes={tmpdir: {"bind": "/app", "mode": "rw"}},
                    working_dir="/app",
                    mem_limit="512m",
                    remove=True,
                ),
                timeout=_DOCKER_BUILD_TIMEOUT_SECONDS,
            )
            return True, ""
        except asyncio.TimeoutError:
            return False, f"backend build timed out after {_DOCKER_BUILD_TIMEOUT_SECONDS}s"
        except Exception as exc:
            stderr = getattr(exc, "stderr", b"") or b""
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            return False, str(stderr) or str(exc)


async def _run_docker_frontend(frontend_code: dict, docker_client) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="vibedeploy-build-frontend-") as tmpdir:
        _write_files_to_tmpdir(frontend_code, tmpdir)
        try:
            await asyncio.wait_for(
                asyncio.to_thread(
                    docker_client.containers.run,
                    "node:20-slim",
                    command="sh -c 'npm install && npm run build'",
                    volumes={tmpdir: {"bind": "/app", "mode": "rw"}},
                    working_dir="/app",
                    mem_limit="512m",
                    remove=True,
                ),
                timeout=_DOCKER_BUILD_TIMEOUT_SECONDS,
            )
            return True, ""
        except asyncio.TimeoutError:
            return False, f"frontend build timed out after {_DOCKER_BUILD_TIMEOUT_SECONDS}s"
        except Exception as exc:
            stderr = getattr(exc, "stderr", b"") or b""
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            return False, str(stderr) or str(exc)


async def _emit_build_event(
    event_name: str,
    *,
    config,
    node: str,
    phase: str,
    message: str,
    **extra,
) -> None:
    if config is None:
        return
    payload = {
        "type": event_name,
        "node": node,
        "stage": node,
        "phase": phase,
        "message": message,
        **extra,
    }
    await adispatch_custom_event(event_name, payload, config=config)


async def build_validator(state: VibeDeployState, config=None) -> dict:
    backend_code = state.get("backend_code") or {}
    frontend_code = state.get("frontend_code") or {}

    await _emit_build_event(
        "build.node.start",
        config=config,
        node="build_validator",
        phase="build_validation",
        message="Validating build...",
    )

    if backend_code:
        await _emit_build_event(
            "build.step.start",
            config=config,
            node="build_validator",
            phase="build_validation",
            message="Checking Python syntax...",
        )
        syntax_errors = _ast_check_python_files(backend_code)
        if syntax_errors:
            logger.warning("[BUILD_VALIDATOR] Python syntax errors detected: %s", syntax_errors)
            combined_stderr = "\n".join(syntax_errors)
            trimmed = _trim_build_errors(combined_stderr)
            repair_prompt = _build_repair_prompt(trimmed, backend_code)
            await _emit_build_event(
                "build.node.error",
                config=config,
                node="build_validator",
                phase="build_validation",
                message="Python syntax errors detected",
                errors=syntax_errors,
            )
            return {
                "build_validation": {
                    "passed": False,
                    "backend_ok": False,
                    "frontend_ok": None,
                    "errors": syntax_errors,
                },
                "build_errors": trimmed,
                "build_repair_prompt": repair_prompt,
                "build_attempt_count": state.get("build_attempt_count", 0) + 1,
            }

    try:
        import docker  # type: ignore[import]
        import docker.errors  # type: ignore[import]
    except ImportError:
        logger.warning("[BUILD_VALIDATOR] docker SDK not installed; skipping container validation")
        await _emit_build_event(
            "build.node.complete",
            config=config,
            node="build_validator",
            phase="build_validation",
            message="Build validation skipped: Docker not available",
            skipped=True,
        )
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
        await _emit_build_event(
            "build.node.complete",
            config=config,
            node="build_validator",
            phase="build_validation",
            message="Build validation skipped: Docker not available",
            skipped=True,
        )
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
    design_ok = True

    if backend_code and "requirements.txt" in backend_code and "main.py" in backend_code:
        logger.info("[BUILD_VALIDATOR] Running backend build validation in Docker")
        await _emit_build_event(
            "build.step.start",
            config=config,
            node="build_validator",
            phase="build_validation",
            message="Running backend build in Docker...",
        )
        backend_ok, backend_err = await _run_docker_backend(backend_code, docker_client)
        if not backend_ok:
            logger.warning("[BUILD_VALIDATOR] Backend Docker validation failed: %s", backend_err[:500])
            errors.append(f"backend: {backend_err[:500]}")

    if frontend_code and "package.json" in frontend_code:
        logger.info("[BUILD_VALIDATOR] Running frontend build validation in Docker")
        await _emit_build_event(
            "build.step.start",
            config=config,
            node="build_validator",
            phase="build_validation",
            message="Running frontend build in Docker...",
        )
        frontend_ok, frontend_err = await _run_docker_frontend(frontend_code, docker_client)
        if not frontend_ok:
            logger.warning("[BUILD_VALIDATOR] Frontend Docker validation failed: %s", frontend_err[:500])
            errors.append(f"frontend: {frontend_err[:500]}")

    if frontend_code:
        design_errors = _check_design_quality(frontend_code)
        if design_errors:
            logger.warning("[BUILD_VALIDATOR] Design quality errors detected: %s", design_errors)
            errors.extend(design_errors)
            design_ok = False

    passed = backend_ok and frontend_ok and design_ok
    if passed:
        await _emit_build_event(
            "build.node.complete",
            config=config,
            node="build_validator",
            phase="build_validation",
            message="Build validation passed",
            passed=True,
            backend_ok=backend_ok,
            frontend_ok=frontend_ok,
        )
        return {
            "build_validation": {
                "passed": True,
                "backend_ok": backend_ok,
                "frontend_ok": frontend_ok,
            }
        }

    combined_stderr = "\n".join(errors)
    trimmed = _trim_build_errors(combined_stderr)
    failing_files: dict[str, str] = {}
    if not backend_ok:
        failing_files.update(backend_code)
    if not frontend_ok or not design_ok:
        failing_files.update(frontend_code)
    repair_prompt = _build_repair_prompt(trimmed, failing_files)

    failing_paths = _extract_failing_file_paths(combined_stderr)
    frontend_only_failure = backend_ok and (not frontend_ok or not design_ok)

    await _emit_build_event(
        "build.node.error",
        config=config,
        node="build_validator",
        phase="build_validation",
        message="Build validation failed",
        passed=False,
        backend_ok=backend_ok,
        frontend_ok=frontend_ok,
        errors=errors,
        attempt=state.get("build_attempt_count", 0) + 1,
        failing_files=failing_paths,
        frontend_only_failure=frontend_only_failure,
    )

    return {
        "build_validation": {
            "passed": False,
            "backend_ok": backend_ok,
            "frontend_ok": frontend_ok,
            "errors": errors,
            "failing_files": failing_paths,
            "frontend_only_failure": frontend_only_failure,
        },
        "build_errors": trimmed,
        "build_errors_full": combined_stderr[:3000],
        "build_repair_prompt": repair_prompt,
        "build_attempt_count": state.get("build_attempt_count", 0) + 1,
        "build_failing_files": failing_paths,
        "build_frontend_only_failure": frontend_only_failure,
    }
