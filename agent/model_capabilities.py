import json
import os
from pathlib import Path
from typing import Any

import httpx

DO_INFERENCE_BASE_URL = "https://inference.do-ai.run/v1"
DEFAULT_MODEL = os.getenv("VIBEDEPLOY_MODEL", "anthropic-claude-4.6-sonnet")

_RESPONSES_MODELS = {
    "openai-gpt-5.4",
    "openai-gpt-5.3-codex",
    "openai-gpt-5.2",
}
_CHAT_COMPLETIONS_MODELS = {
    "anthropic-claude-opus-4.6",
    "anthropic-claude-4.6-sonnet",
    "openai-gpt-oss-120b",
}

MODEL_PROBE_CANDIDATES: list[dict[str, str]] = [
    {"model": "anthropic-claude-4.6-sonnet", "endpoint": "chat"},
    {"model": "anthropic-claude-opus-4.6", "endpoint": "chat"},
    {"model": "openai-gpt-5.4", "endpoint": "responses"},
    {"model": "openai-gpt-5.3-codex", "endpoint": "responses"},
    {"model": "openai-gpt-5.2", "endpoint": "responses"},
    {"model": "openai-gpt-oss-120b", "endpoint": "chat"},
]


def capability_report_path() -> Path:
    env_override = os.getenv("VIBEDEPLOY_MODEL_CAPABILITY_REPORT", "").strip()
    if env_override:
        return Path(env_override)
    return Path(__file__).resolve().parent / ".gradient" / "model_capabilities.json"


def is_responses_model(model: str) -> bool:
    return model.strip().lower() in _RESPONSES_MODELS


def model_endpoint_type(model: str) -> str:
    normalized = model.strip().lower()
    if normalized in _RESPONSES_MODELS:
        return "responses"
    if normalized in _CHAT_COMPLETIONS_MODELS:
        return "chat"
    if normalized.startswith("openai-gpt-5."):
        return "responses"
    return "chat"


def load_model_capability_report() -> dict[str, Any]:
    path = capability_report_path()
    if not path.exists():
        return {
            "selected_model": DEFAULT_MODEL,
            "selected_endpoint": model_endpoint_type(DEFAULT_MODEL),
            "probed": False,
            "candidates": [],
        }

    try:
        payload = json.loads(path.read_text())
    except Exception:
        return {
            "selected_model": DEFAULT_MODEL,
            "selected_endpoint": model_endpoint_type(DEFAULT_MODEL),
            "probed": False,
            "candidates": [],
        }

    if not isinstance(payload, dict):
        return {
            "selected_model": DEFAULT_MODEL,
            "selected_endpoint": model_endpoint_type(DEFAULT_MODEL),
            "probed": False,
            "candidates": [],
        }

    selected_model = str(payload.get("selected_model") or DEFAULT_MODEL)
    payload.setdefault("selected_model", selected_model)
    payload.setdefault("selected_endpoint", model_endpoint_type(selected_model))
    payload.setdefault("probed", False)
    payload.setdefault("candidates", [])
    return payload


def selected_runtime_model(default: str = DEFAULT_MODEL) -> str:
    report = load_model_capability_report()
    selected = str(report.get("selected_model") or default).strip()
    return selected or default


def write_model_capability_report(report: dict[str, Any]) -> Path:
    path = capability_report_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return path


async def _probe_anthropic_direct(timeout_seconds: float) -> dict[str, Any] | None:
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not anthropic_key:
        return None

    headers = {
        "x-api-key": anthropic_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 32,
        "messages": [{"role": "user", "content": "Reply with READY only."}],
    }
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
            response = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            if response.status_code == 200:
                return {
                    "model": "anthropic-claude-4.6-sonnet",
                    "endpoint": "chat",
                    "status_code": 200,
                    "ok": True,
                    "body_preview": response.text[:500],
                    "route": "anthropic_direct",
                }
            return {
                "model": "anthropic-claude-4.6-sonnet",
                "endpoint": "chat",
                "status_code": response.status_code,
                "ok": False,
                "body_preview": response.text[:500],
                "route": "anthropic_direct",
            }
    except Exception as exc:
        return {
            "model": "anthropic-claude-4.6-sonnet",
            "endpoint": "chat",
            "status_code": None,
            "ok": False,
            "body_preview": f"{type(exc).__name__}: {exc}",
            "route": "anthropic_direct",
        }


async def probe_model_capabilities(
    api_key: str | None = None,
    *,
    timeout_seconds: float = 90.0,
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    selected_model = DEFAULT_MODEL
    selected_endpoint = model_endpoint_type(DEFAULT_MODEL)

    anthropic_result = await _probe_anthropic_direct(timeout_seconds)
    if anthropic_result:
        candidates.append(anthropic_result)
        if anthropic_result["ok"]:
            selected_model = anthropic_result["model"]
            selected_endpoint = anthropic_result["endpoint"]
            report = {
                "selected_model": selected_model,
                "selected_endpoint": selected_endpoint,
                "probed": True,
                "candidates": candidates,
            }
            write_model_capability_report(report)
            return report

    token = (
        api_key or os.getenv("GRADIENT_MODEL_ACCESS_KEY", "") or os.getenv("DIGITALOCEAN_INFERENCE_KEY", "")
    ).strip()
    if not token:
        report = {
            "selected_model": DEFAULT_MODEL,
            "selected_endpoint": model_endpoint_type(DEFAULT_MODEL),
            "probed": False,
            "error": "missing_digitalocean_inference_key",
            "candidates": candidates,
        }
        write_model_capability_report(report)
        return report

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
        for item in MODEL_PROBE_CANDIDATES:
            model = item["model"]
            endpoint = item["endpoint"]
            if _is_anthropic_model_name(model):
                continue
            if endpoint == "responses":
                url = f"{DO_INFERENCE_BASE_URL}/responses"
                payload = {
                    "model": model,
                    "input": "Reply with READY only.",
                }
            else:
                url = f"{DO_INFERENCE_BASE_URL}/chat/completions"
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": "Reply with READY only."}],
                    "max_completion_tokens": 256,
                }

            try:
                response = await client.post(url, headers=headers, json=payload)
                success = response.status_code == 200
                body = response.text[:500]
            except Exception as exc:
                response = None
                success = False
                body = f"{type(exc).__name__}: {exc}"

            candidate = {
                "model": model,
                "endpoint": endpoint,
                "status_code": response.status_code if response is not None else None,
                "ok": success,
                "body_preview": body,
            }
            candidates.append(candidate)

            if success:
                selected_model = model
                selected_endpoint = endpoint
                break

    report = {
        "selected_model": selected_model,
        "selected_endpoint": selected_endpoint,
        "probed": True,
        "candidates": candidates,
    }
    write_model_capability_report(report)
    return report


def _is_anthropic_model_name(model: str) -> bool:
    normalized = (model or "").strip().lower()
    return "claude" in normalized or normalized.startswith("anthropic")
