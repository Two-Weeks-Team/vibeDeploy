from __future__ import annotations

import json
from pathlib import Path

REGISTRY_PATH = Path(__file__).resolve().parent / "flagship_registry.json"


def load_flagship_registry() -> list[dict]:
    payload = json.loads(REGISTRY_PATH.read_text())
    if not isinstance(payload, list):
        raise ValueError("flagship registry must be a list")
    return [item for item in payload if isinstance(item, dict)]


def get_flagship(slug: str) -> dict:
    normalized = slug.strip().lower()
    for item in load_flagship_registry():
        if str(item.get("slug") or "").strip().lower() == normalized:
            return item
    raise KeyError(f"unknown flagship slug: {slug}")


def build_flagship_payload(item: dict, *, thread_id: str) -> dict:
    product_brief = str(item.get("product_brief") or "").strip()
    domain = str(item.get("domain") or "").strip()
    visual_metaphor = str(item.get("visual_metaphor") or "").strip()
    forbidden_patterns = [str(value).strip() for value in item.get("forbidden_patterns", []) if str(value).strip()]
    required_objects = [str(value).strip() for value in item.get("required_objects", []) if str(value).strip()]
    required_results = [str(value).strip() for value in item.get("required_results", []) if str(value).strip()]
    acceptance_checks = [str(value).strip() for value in item.get("acceptance_checks", []) if str(value).strip()]

    constraint_lines = [
        f"Target domain: {domain}.",
        f"Visual metaphor: {visual_metaphor}.",
        "This must become a distinctive, consumer-grade, fully working web service.",
        "Avoid placeholder scaffolds, raw object dumps, fake credibility claims, and generic admin dashboards.",
        "Keep the MVP hackathon-realistic in a single FastAPI + Next.js codebase with simple persistence.",
        "Prefer transcript, URL, and structured AI analysis over heavy media processing, binary uploads, worker fleets, or third-party partner dependencies.",
        "Do not invent awards, coverage, user counts, partnership claims, benchmark numbers, or validation statistics.",
    ]
    if forbidden_patterns:
        constraint_lines.append("Forbidden patterns: " + "; ".join(forbidden_patterns) + ".")
    if required_objects:
        constraint_lines.append("Required visible product objects: " + "; ".join(required_objects) + ".")
    if required_results:
        constraint_lines.append("Required real outputs or saved artifacts: " + "; ".join(required_results) + ".")
    if acceptance_checks:
        constraint_lines.append("Acceptance checks: " + "; ".join(acceptance_checks) + ".")

    return {
        "action": "evaluate",
        "thread_id": thread_id,
        "selected_flagship": str(item.get("slug") or "").strip(),
        "flagship_contract": {
            "slug": str(item.get("slug") or "").strip(),
            "domain": domain,
            "visual_metaphor": visual_metaphor,
            "forbidden_patterns": forbidden_patterns,
            "required_objects": required_objects,
            "required_results": required_results,
            "acceptance_checks": acceptance_checks,
        },
        "prompt": product_brief,
        "youtube_url": str(item.get("youtube_url") or "").strip(),
        "reference_urls": [str(value).strip() for value in item.get("reference_urls", []) if str(value).strip()],
        "constraints": "\n".join(constraint_lines),
    }
