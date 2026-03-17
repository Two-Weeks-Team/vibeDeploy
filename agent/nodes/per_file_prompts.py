from __future__ import annotations

from typing import Any

AVAILABLE_CONTEXT_KEYS = {
    "design_system",
    "layout",
    "navigation",
    "props_spec",
    "api_contract",
    "types",
    "models",
}

PROMPT_TEMPLATES: dict[str, dict[str, Any]] = {
    "page.tsx": {
        "role": "Senior Next.js page engineer",
        "context_keys": ["design_system", "layout", "navigation"],
        "template": (
            "Role: {role}\n"
            "File path: {file_path}\n"
            "Description: {description}\n\n"
            "Relevant context:\n{context_block}\n"
            "Task: Build a production-ready Next.js page using App Router patterns, "
            "accessible semantics, and clear state handling."
        ),
        "max_tokens": 4000,
    },
    "component.tsx": {
        "role": "Senior React component engineer",
        "context_keys": ["design_system", "props_spec"],
        "template": (
            "Role: {role}\n"
            "File path: {file_path}\n"
            "Description: {description}\n\n"
            "Relevant context:\n{context_block}\n"
            "Task: Build a reusable typed component with robust prop ergonomics and "
            "strict design-system consistency."
        ),
        "max_tokens": 3500,
    },
    "api.ts": {
        "role": "Senior TypeScript API client engineer",
        "context_keys": ["api_contract", "types"],
        "template": (
            "Role: {role}\n"
            "File path: {file_path}\n"
            "Description: {description}\n\n"
            "Relevant context:\n{context_block}\n"
            "Task: Build a typed API client module that follows the contract exactly, "
            "including request/response typing and safe error paths."
        ),
        "max_tokens": 3500,
    },
    "routes.py": {
        "role": "Senior FastAPI routing engineer",
        "context_keys": ["api_contract", "models"],
        "template": (
            "Role: {role}\n"
            "File path: {file_path}\n"
            "Description: {description}\n\n"
            "Relevant context:\n{context_block}\n"
            "Task: Build FastAPI routes aligned to the contract, model constraints, "
            "and idiomatic router organization."
        ),
        "max_tokens": 4000,
    },
    "ai_service.py": {
        "role": "Senior AI service integration engineer",
        "context_keys": ["api_contract"],
        "template": (
            "Role: {role}\n"
            "File path: {file_path}\n"
            "Description: {description}\n\n"
            "Relevant context:\n{context_block}\n"
            "Task: Build a minimal AI service implementation that honors the contract "
            "with clear retry/error boundaries and configurable model access."
        ),
        "max_tokens": 3200,
    },
}

_GENERIC_TEMPLATE: dict[str, Any] = {
    "role": "Senior software engineer",
    "context_keys": [],
    "template": (
        "Role: {role}\n"
        "File path: {file_path}\n"
        "Description: {description}\n\n"
        "Relevant context:\n{context_block}\n"
        "Task: Build production-ready code that matches the requested file purpose."
    ),
    "max_tokens": 4000,
}


def get_context_keys_for_type(file_type: str) -> list[str]:
    template = PROMPT_TEMPLATES.get(file_type, _GENERIC_TEMPLATE)
    return list(template["context_keys"])


def build_prompt(file_type: str, context: dict[str, Any]) -> str:
    template = PROMPT_TEMPLATES.get(file_type, _GENERIC_TEMPLATE)
    file_path = str(context.get("file_path", "<unknown-path>"))
    description = str(context.get("description", "<no-description>"))

    lines: list[str] = []
    for key in template["context_keys"]:
        if key in context:
            value = context[key]
            if value is not None and value != "":
                lines.append(f"- {key}: {value}")

    context_block = "\n".join(lines) if lines else "- none"

    return template["template"].format(
        role=template["role"],
        file_path=file_path,
        description=description,
        context_block=context_block,
    )


def estimate_tokens(prompt: str) -> int:
    return len(prompt) // 4
