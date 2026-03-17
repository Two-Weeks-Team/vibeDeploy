import json
import re

import yaml

from ..llm import MODEL_CONFIG, ainvoke_with_retry, content_to_str, get_llm, get_rate_limit_fallback_models
from ..prompts.doc_templates import (
    API_SPEC_SYSTEM_PROMPT,
    APP_SPEC_SYSTEM_PROMPT,
    DB_SCHEMA_SYSTEM_PROMPT,
    DOC_GENERATION_BASE_SYSTEM_PROMPT,
    PRD_SYSTEM_PROMPT,
    TECH_SPEC_SYSTEM_PROMPT,
)
from ..state import VibeDeployState
from ..tools.digitalocean import build_app_spec
from ..utils.json_utils import parse_json_response


async def doc_generator(state: VibeDeployState) -> dict:
    idea = state.get("idea", {})
    council_analysis = state.get("council_analysis", {})
    scoring = state.get("scoring", {})

    doc_model = MODEL_CONFIG["doc_gen"]
    fallback_models = get_rate_limit_fallback_models(doc_model)
    context = _build_context(idea, council_analysis, scoring)
    if _should_use_template_docs(fallback_models):
        return {
            "generated_docs": _build_template_docs(idea),
            "phase": "docs_generated",
        }

    try:
        llm = get_llm(
            model=doc_model,
            temperature=0.3,
            max_tokens=16000,
        )
    except Exception as exc:
        return {
            "generated_docs": {
                "prd": _fallback_markdown_doc("Product Requirements", idea, str(exc)[:200]),
                "tech_spec": _fallback_markdown_doc("Technical Specification", idea, str(exc)[:200]),
                "api_spec": _fallback_markdown_doc("API Specification", idea, str(exc)[:200]),
                "db_schema": _fallback_markdown_doc("Database Schema", idea, str(exc)[:200]),
                "app_spec_yaml": yaml.safe_dump(
                    build_app_spec(
                        _slugify(idea.get("name") or idea.get("tagline") or "vibedeploy-app"),
                        f"https://github.com/example/{_slugify(idea.get('name') or idea.get('tagline') or 'vibedeploy-app')}.git",
                    ),
                    sort_keys=False,
                    allow_unicode=False,
                ),
            },
            "phase": "docs_generated",
        }

    prd = await _generate_markdown_doc(
        llm,
        PRD_SYSTEM_PROMPT,
        context,
        fallback_models,
        fallback_title="Product Requirements",
        idea=idea,
    )
    tech_spec = await _generate_markdown_doc(
        llm,
        TECH_SPEC_SYSTEM_PROMPT,
        context,
        fallback_models,
        fallback_title="Technical Specification",
        idea=idea,
    )
    api_spec = await _generate_markdown_doc(
        llm,
        API_SPEC_SYSTEM_PROMPT,
        context,
        fallback_models,
        fallback_title="API Specification",
        idea=idea,
    )
    db_schema = await _generate_markdown_doc(
        llm,
        DB_SCHEMA_SYSTEM_PROMPT,
        context,
        fallback_models,
        fallback_title="Database Schema",
        idea=idea,
    )
    app_spec_yaml = await _generate_app_spec_yaml_doc(llm, context, idea, fallback_models)

    return {
        "generated_docs": {
            "prd": prd,
            "tech_spec": tech_spec,
            "api_spec": api_spec,
            "db_schema": db_schema,
            "app_spec_yaml": app_spec_yaml,
        },
        "phase": "docs_generated",
    }


def _build_context(idea: dict, council_analysis: dict, scoring: dict) -> str:
    return json.dumps(
        {
            "idea": idea,
            "council_analysis": council_analysis,
            "scoring": scoring,
        },
        indent=2,
        ensure_ascii=False,
    )


async def _generate_markdown_doc(
    llm,
    doc_system_prompt: str,
    context: str,
    fallback_models: list[str],
    *,
    fallback_title: str,
    idea: dict,
) -> str:
    try:
        response = await ainvoke_with_retry(
            llm,
            [
                {
                    "role": "system",
                    "content": (
                        f"{DOC_GENERATION_BASE_SYSTEM_PROMPT}\n\n"
                        f"{doc_system_prompt}\n\n"
                        "Return JSON with one key: 'content' containing the final markdown string."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Create the document from this planning context:\n\n{context}",
                },
            ],
            fallback_models=fallback_models,
        )
        parsed = parse_json_response(content_to_str(response.content), {"content": ""})
        content = parsed.get("content", "")
        if isinstance(content, str) and content.strip():
            return content
    except Exception as exc:
        return _fallback_markdown_doc(fallback_title, idea, str(exc)[:200])

    return _fallback_markdown_doc(fallback_title, idea, "empty_doc_response")


async def _generate_app_spec_yaml_doc(llm, context: str, idea: dict, fallback_models: list[str]) -> str:
    app_name = _slugify(idea.get("name") or idea.get("tagline") or "vibedeploy-app")
    repo_placeholder = f"https://github.com/example/{app_name}.git"
    baseline_spec = build_app_spec(app_name, repo_placeholder)
    try:
        response = await ainvoke_with_retry(
            llm,
            [
                {
                    "role": "system",
                    "content": (
                        f"{DOC_GENERATION_BASE_SYSTEM_PROMPT}\n\n"
                        f"{APP_SPEC_SYSTEM_PROMPT}\n\n"
                        "Return JSON with one key: 'content' containing only YAML."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Planning context:\n"
                        f"{context}\n\n"
                        "Reference baseline app spec dict from vibeDeploy tool pattern:\n"
                        f"{json.dumps(baseline_spec, indent=2, ensure_ascii=False)}"
                    ),
                },
            ],
            fallback_models=fallback_models,
        )
        parsed = parse_json_response(content_to_str(response.content), {"content": ""})
        content = parsed.get("content", "")
        if isinstance(content, str) and content.strip():
            return content
    except Exception:
        pass

    return yaml.safe_dump(baseline_spec, sort_keys=False, allow_unicode=False)


def _fallback_markdown_doc(title: str, idea: dict, reason: str) -> str:
    name = str(idea.get("name") or "Untitled App").strip()
    tagline = str(idea.get("tagline") or "").strip()
    problem = str(idea.get("problem") or "").strip()
    solution = str(idea.get("solution") or "").strip()
    target_users = str(idea.get("target_users") or "").strip()
    features = [str(item).strip() for item in idea.get("key_features", []) if str(item).strip()]

    lines = [f"# {title}", "", f"- App: {name}"]
    if tagline:
        lines.append(f"- Tagline: {tagline}")
    if target_users:
        lines.append(f"- Target Users: {target_users}")
    if problem:
        lines.extend(["", "## Problem", problem])
    if solution:
        lines.extend(["", "## Solution", solution])
    if features:
        lines.extend(["", "## Core Features", *[f"- {feature}" for feature in features[:6]]])
    lines.extend(
        ["", "## Delivery Note", f"- Fallback document generated because doc generation was unavailable: {reason}."]
    )
    return "\n".join(lines).strip()


def _should_use_template_docs(fallback_models: list[str]) -> bool:
    return not fallback_models


def _build_template_docs(idea: dict) -> dict[str, str]:
    app_name = _slugify(idea.get("name") or idea.get("tagline") or "vibedeploy-app")
    repo_placeholder = f"https://github.com/example/{app_name}.git"
    baseline_spec = build_app_spec(app_name, repo_placeholder)
    return {
        "prd": _fallback_markdown_doc("Product Requirements", idea, "template_docs_enabled"),
        "tech_spec": _fallback_markdown_doc("Technical Specification", idea, "template_docs_enabled"),
        "api_spec": _fallback_markdown_doc("API Specification", idea, "template_docs_enabled"),
        "db_schema": _fallback_markdown_doc("Database Schema", idea, "template_docs_enabled"),
        "app_spec_yaml": yaml.safe_dump(baseline_spec, sort_keys=False, allow_unicode=False),
    }


def _slugify(value: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9\s-]", "", value).strip().lower()
    clean = re.sub(r"[\s_]+", "-", clean)
    clean = re.sub(r"-+", "-", clean)
    return clean or "vibedeploy-app"
