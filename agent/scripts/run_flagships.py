from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

AGENT_DIR = ROOT / "agent"
load_dotenv(AGENT_DIR / ".env.test")
load_dotenv(AGENT_DIR / ".env", override=True)


def _normalize_base_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/api"):
        return normalized
    if "ondigitalocean.app" in normalized or normalized.startswith("http"):
        return f"{normalized}/api"
    return normalized


def _parse_event(line: str) -> dict | None:
    if not line.startswith("data: "):
        return None
    try:
        return json.loads(line[6:])
    except json.JSONDecodeError:
        return None


async def _stream_run(client: httpx.AsyncClient, base_url: str, payload: dict) -> dict:
    summary = _new_summary(payload)
    started_at = time.time()
    async with client.stream("POST", f"{base_url}/run", json=payload, timeout=900.0) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            event = _parse_event(line)
            if event:
                _record_event(summary, event)
    summary["duration_sec"] = round(time.time() - started_at, 1)
    return summary


async def _stream_run_direct(payload: dict) -> dict:
    from agent.pipeline_runtime import stream_action_session

    summary = _new_summary(payload)
    started_at = time.time()
    async for chunk in stream_action_session(payload):
        for line in str(chunk).splitlines():
            event = _parse_event(line)
            if event:
                _record_event(summary, event)
    summary["duration_sec"] = round(time.time() - started_at, 1)
    return summary


def _new_summary(payload: dict) -> dict:
    summary = {
        "thread_id": payload["thread_id"],
        "selected_flagship": payload.get("selected_flagship"),
        "verdict": None,
        "deployment": None,
        "artifact_fidelity": None,
        "events": [],
        "errors": [],
        "code_eval_results": [],
        "codegen_warnings": [],
        "duration_sec": 0.0,
    }
    return summary


def _record_event(summary: dict, event: dict) -> None:
    summary["events"].append(event.get("type"))
    if event.get("type") == "council.verdict":
        summary["verdict"] = {
            "final_score": event.get("final_score"),
            "decision": event.get("decision"),
        }
    elif event.get("type") == "session.completed":
        result = event.get("result") if isinstance(event.get("result"), dict) else {}
        deployment = result.get("deployment") if isinstance(result.get("deployment"), dict) else {}
        if deployment:
            summary["deployment"] = {
                "live_url": deployment.get("liveUrl") or deployment.get("live_url"),
                "github_repo": deployment.get("githubRepo") or deployment.get("github_repo"),
                "status": deployment.get("status"),
                "local_url": deployment.get("localUrl") or deployment.get("local_url"),
                "local_frontend_url": deployment.get("localFrontendUrl") or deployment.get("local_frontend_url"),
                "local_backend_url": deployment.get("localBackendUrl") or deployment.get("local_backend_url"),
                "local_app_dir": deployment.get("localAppDir") or deployment.get("local_app_dir"),
            }
    elif event.get("type") == "deploy.complete":
        summary["deployment"] = {
            "live_url": event.get("live_url"),
            "github_repo": event.get("github_repo"),
            "status": event.get("status"),
            "local_url": event.get("local_url"),
            "local_frontend_url": event.get("local_frontend_url"),
            "local_backend_url": event.get("local_backend_url"),
            "local_app_dir": event.get("local_app_dir"),
        }
    elif event.get("type") == "code_eval.result":
        summary["code_eval_results"].append(
            {
                "iteration": event.get("iteration"),
                "passed": event.get("passed"),
                "match_rate": event.get("match_rate"),
                "completeness": event.get("completeness"),
                "consistency": event.get("consistency"),
                "runnability": event.get("runnability"),
                "artifact_fidelity": event.get("artifact_fidelity"),
                "blockers": event.get("blockers", []),
            }
        )
    elif event.get("type") == "code_gen.warning":
        summary["codegen_warnings"].append(event.get("message"))
    elif "error" in str(event.get("type") or ""):
        summary["errors"].append(str(event.get("error") or "")[:300])


async def main() -> None:
    from agent.flagships import build_flagship_payload, load_flagship_registry

    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080", help="Gateway base URL")
    parser.add_argument("--output", default="/tmp/vibedeploy-flagships.json", help="Where to write the summary JSON")
    parser.add_argument("--slug", action="append", default=[], help="Only run the given flagship slug (repeatable)")
    parser.add_argument("--mode", choices=["http", "direct"], default="http", help="Execution mode")
    args = parser.parse_args()

    base_url = _normalize_base_url(args.base_url)
    registry = load_flagship_registry()
    selected_slugs = {value.strip().lower() for value in args.slug if value.strip()}
    if selected_slugs:
        registry = [item for item in registry if str(item.get("slug") or "").strip().lower() in selected_slugs]
        if not registry:
            raise SystemExit(f"No registry entries matched: {', '.join(sorted(selected_slugs))}")
    results: list[dict] = []

    if args.mode == "direct":
        for entry in registry:
            thread_id = f"{entry['slug']}-{uuid.uuid4().hex[:8]}"
            payload = build_flagship_payload(entry, thread_id=thread_id)
            print(f"[flagship] {entry['slug']} -> {thread_id}")
            result = await _stream_run_direct(payload)
            result["artifact_fidelity"] = _inspect_local_artifacts(payload, result)
            results.append({"slug": entry["slug"], "payload": payload, "result": result})
    else:
        async with httpx.AsyncClient() as client:
            for entry in registry:
                thread_id = f"{entry['slug']}-{uuid.uuid4().hex[:8]}"
                payload = build_flagship_payload(entry, thread_id=thread_id)
                print(f"[flagship] {entry['slug']} -> {thread_id}")
                result = await _stream_run(client, base_url, payload)
                result["artifact_fidelity"] = _inspect_local_artifacts(payload, result)
                results.append({"slug": entry["slug"], "payload": payload, "result": result})

    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2, ensure_ascii=False)
    print(args.output)


def _inspect_local_artifacts(payload: dict, result: dict) -> dict | None:
    deployment = result.get("deployment") or {}
    local_app_dir = str(deployment.get("local_app_dir") or "").strip()
    contract = payload.get("flagship_contract") if isinstance(payload.get("flagship_contract"), dict) else {}
    if not local_app_dir or not contract:
        return None

    base_dir = Path(local_app_dir)
    if not base_dir.exists():
        return None

    files_to_check = [
        base_dir / "web/src/app/page.tsx",
        base_dir / "web/src/app/page.jsx",
        base_dir / "routes.py",
        base_dir / "README.md",
    ]
    text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore") for path in files_to_check if path.exists()
    ).lower()
    required_objects = [str(value).strip() for value in contract.get("required_objects", []) if str(value).strip()]
    required_results = [str(value).strip() for value in contract.get("required_results", []) if str(value).strip()]

    object_hits = [item for item in required_objects if _phrase_present(item, text)]
    result_hits = [item for item in required_results if _phrase_present(item, text)]
    return {
        "required_object_hits": object_hits,
        "required_result_hits": result_hits,
        "required_object_misses": [item for item in required_objects if item not in object_hits],
        "required_result_misses": [item for item in required_results if item not in result_hits],
        "passed": len(object_hits) >= max(2, len(required_objects) - 1)
        and len(result_hits) >= max(2, len(required_results) - 1),
    }


def _phrase_present(phrase: str, haystack: str) -> bool:
    tokens = [token for token in phrase.lower().replace("-", " ").split() if token]
    if not tokens:
        return False
    if len(tokens) == 1:
        return tokens[0] in haystack
    hits = sum(1 for token in tokens if token in haystack)
    return hits >= max(2, len(tokens) - 1)


if __name__ == "__main__":
    asyncio.run(main())
