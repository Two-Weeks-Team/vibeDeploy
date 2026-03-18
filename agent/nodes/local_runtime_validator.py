from __future__ import annotations

import asyncio
import json
import socket
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request


def _free_port(start: int = 9300) -> int:
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("no_free_port")


def _write_files(base: Path, files: dict[str, str]) -> None:
    for rel_path, content in files.items():
        if not isinstance(content, str):
            continue
        resolved_base = base.resolve()
        resolved_target = (base / rel_path).resolve(strict=False)
        if not resolved_target.is_relative_to(resolved_base):
            raise ValueError(f"Path traversal detected: {rel_path}")
        target = resolved_target
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)


def _http_ok(url: str, timeout: float = 10.0) -> tuple[bool, str]:
    try:
        with request.urlopen(url, timeout=timeout) as resp:
            body = resp.read(500).decode("utf-8", errors="ignore")
            return 200 <= resp.status < 300, body
    except urlerror.URLError as exc:
        return False, str(exc)


def _http_json(url: str, payload: dict[str, Any], timeout: float = 10.0) -> tuple[bool, str]:
    try:
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(500).decode("utf-8", errors="ignore")
            return 200 <= resp.status < 300, body
    except urlerror.URLError as exc:
        return False, str(exc)


async def local_runtime_validator(state: dict[str, Any], config=None) -> dict:
    backend_code = dict(state.get("backend_code") or {})
    api_contract = str(state.get("api_contract") or "")
    errors: list[str] = []
    if "main.py" not in backend_code:
        return {
            "local_runtime_validation": {"passed": False, "errors": ["backend_main_missing"]},
            "phase": "local_runtime_failed",
            "error": "backend_main_missing",
        }

    with tempfile.TemporaryDirectory(prefix="vibedeploy-runtime-") as tmpdir:
        backend_dir = Path(tmpdir) / "backend"
        backend_dir.mkdir(parents=True, exist_ok=True)
        _write_files(backend_dir, backend_code)
        port = _free_port()
        proc = subprocess.Popen(
            [
                "python3",
                "-m",
                "uvicorn",
                "main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=str(backend_dir),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            await asyncio.sleep(4)
            if proc.poll() is not None:
                stderr = (proc.stderr.read() if proc.stderr else "")[:500]
                errors.append(f"backend_process_exited:{stderr}")
            else:
                ok, detail = await asyncio.to_thread(_http_ok, f"http://127.0.0.1:{port}/health")
                if not ok:
                    errors.append(f"backend_health_failed:{detail}")
                if ok and api_contract:
                    try:
                        spec = json.loads(api_contract)
                    except Exception:
                        spec = {}
                    paths = spec.get("paths") if isinstance(spec, dict) else {}
                    if isinstance(paths, dict):
                        for endpoint, methods in list(paths.items())[:3]:
                            if not isinstance(methods, dict):
                                continue
                            if "post" in methods:
                                payload = {"query": "test", "preferences": "test"}
                                if "insight" in endpoint.lower():
                                    payload = {"selection": "test", "context": "test"}
                                post_ok, post_detail = await asyncio.to_thread(
                                    _http_json, f"http://127.0.0.1:{port}{endpoint}", payload
                                )
                                if not post_ok:
                                    errors.append(f"backend_endpoint_failed:{endpoint}:{post_detail}")
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    await asyncio.to_thread(proc.wait, 5)
                except subprocess.TimeoutExpired:
                    proc.kill()

    passed = not errors
    return {
        "local_runtime_validation": {"passed": passed, "errors": errors},
        "phase": "local_runtime_validated" if passed else "local_runtime_failed",
        "error": "; ".join(errors) if errors else None,
    }
