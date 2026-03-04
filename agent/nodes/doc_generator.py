import json
import re

from langchain_gradient import ChatGradient

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


async def doc_generator(state: VibeDeployState) -> dict:
    idea = state.get("idea", {})
    council_analysis = state.get("council_analysis", {})
    scoring = state.get("scoring", {})

    llm = ChatGradient(
        model="anthropic-claude-4.6-sonnet",
        temperature=0.3,
        max_tokens=4000,
    )

    context = _build_context(idea, council_analysis, scoring)

    prd = await _generate_markdown_doc(llm, PRD_SYSTEM_PROMPT, context)
    tech_spec = await _generate_markdown_doc(llm, TECH_SPEC_SYSTEM_PROMPT, context)
    api_spec = await _generate_markdown_doc(llm, API_SPEC_SYSTEM_PROMPT, context)
    db_schema = await _generate_markdown_doc(llm, DB_SCHEMA_SYSTEM_PROMPT, context)
    app_spec_yaml = await _generate_app_spec_yaml_doc(llm, context, idea)

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


async def _generate_markdown_doc(llm: ChatGradient, doc_system_prompt: str, context: str) -> str:
    response = await llm.ainvoke(
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
        ]
    )

    parsed = _parse_json_response(response.content, {"content": ""})
    content = parsed.get("content", "")
    return content if isinstance(content, str) else ""


async def _generate_app_spec_yaml_doc(llm: ChatGradient, context: str, idea: dict) -> str:
    app_name = _slugify(idea.get("name") or idea.get("tagline") or "vibedeploy-app")
    repo_placeholder = f"https://github.com/example/{app_name}.git"
    baseline_spec = build_app_spec(app_name, repo_placeholder)

    response = await llm.ainvoke(
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
        ]
    )

    parsed = _parse_json_response(response.content, {"content": ""})
    content = parsed.get("content", "")
    return content if isinstance(content, str) else ""


def _slugify(value: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9\s-]", "", value).strip().lower()
    clean = re.sub(r"[\s_]+", "-", clean)
    clean = re.sub(r"-+", "-", clean)
    return clean or "vibedeploy-app"


def _parse_json_response(content: str, default: dict) -> dict:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\n?", "", content)
        content = re.sub(r"\n?```$", "", content)

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        result = dict(default)
        result["raw_response"] = content[:500]
        return result
