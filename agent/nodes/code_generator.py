import asyncio
import json
import logging
import re

from ..llm import MODEL_CONFIG, ainvoke_with_retry, get_llm, get_rate_limit_fallback_models
from ..prompts.code_templates import (
    BACKEND_SYSTEM_PROMPT,
    CODE_GENERATION_BASE_SYSTEM_PROMPT,
    FRONTEND_SYSTEM_PROMPT,
)
from ..state import VibeDeployState

logger = logging.getLogger(__name__)

# Minimum expected file counts for validation
_MIN_FRONTEND_FILES = 3  # At least package.json + 2 source files
_MIN_BACKEND_FILES = 2  # At least main.py + requirements.txt


async def code_generator(state: VibeDeployState) -> dict:
    generated_docs = state.get("generated_docs", {})
    idea = state.get("idea", {})
    blueprint = state.get("blueprint", {}) or {}
    code_eval_result = state.get("code_eval_result")
    frontend_model = MODEL_CONFIG.get("code_gen_frontend", MODEL_CONFIG["code_gen"])
    backend_model = MODEL_CONFIG.get("code_gen_backend", MODEL_CONFIG["code_gen"])

    frontend_llm = get_llm(
        model=frontend_model,
        temperature=0.3,
        max_tokens=8000,
    )
    backend_llm = get_llm(
        model=backend_model,
        temperature=0.3,
        max_tokens=8000,
    )

    context = json.dumps(
        {
            "idea": idea,
            "generated_docs": generated_docs,
            "blueprint": blueprint,
        },
        indent=2,
        ensure_ascii=False,
    )

    eval_feedback = _build_eval_feedback(code_eval_result)

    frontend_code = await _generate_frontend_files(
        frontend_llm,
        context,
        eval_feedback=eval_feedback,
        fallback_models=get_rate_limit_fallback_models(frontend_model),
    )
    await asyncio.sleep(8)
    backend_code = await _generate_backend_files(
        backend_llm,
        context,
        eval_feedback=eval_feedback,
        fallback_models=get_rate_limit_fallback_models(backend_model),
    )

    generation_warnings = []

    if len(frontend_code) < _MIN_FRONTEND_FILES:
        warning = (
            f"Frontend generation produced {len(frontend_code)} files "
            f"(expected >= {_MIN_FRONTEND_FILES}). "
            f"Files: {list(frontend_code.keys()) if frontend_code else '(none)'}"
        )
        logger.warning("[CODE_GEN] %s", warning)
        generation_warnings.append(warning)

        logger.info("[CODE_GEN] Retrying frontend generation (attempt 2)...")
        frontend_code = await _generate_frontend_files(
            frontend_llm,
            context,
            retry=True,
            fallback_models=get_rate_limit_fallback_models(frontend_model),
        )

        if len(frontend_code) < _MIN_FRONTEND_FILES:
            retry_warning = (
                f"Frontend retry also produced {len(frontend_code)} files. "
                "Frontend will be omitted — backend-only deployment."
            )
            logger.warning("[CODE_GEN] %s", retry_warning)
            generation_warnings.append(retry_warning)

    if len(backend_code) < _MIN_BACKEND_FILES:
        warning = (
            f"Backend generation produced {len(backend_code)} files "
            f"(expected >= {_MIN_BACKEND_FILES}). "
            f"Files: {list(backend_code.keys()) if backend_code else '(none)'}"
        )
        logger.warning("[CODE_GEN] %s", warning)
        generation_warnings.append(warning)

    logger.info(
        "[CODE_GEN] Result: frontend=%d files, backend=%d files, warnings=%d",
        len(frontend_code),
        len(backend_code),
        len(generation_warnings),
    )

    return {
        "frontend_code": frontend_code,
        "backend_code": backend_code,
        "phase": "code_generated",
        "code_gen_warnings": generation_warnings,
    }


async def _generate_frontend_files(
    llm,
    context: str,
    retry: bool = False,
    eval_feedback: str | None = None,
    fallback_models: list[str] | None = None,
) -> dict[str, str]:
    extra_instruction = ""
    if retry:
        extra_instruction = (
            "\n\nCRITICAL: Your previous response could not be parsed as valid JSON. "
            'You MUST return ONLY a valid JSON object like: {"files": {"path": "content", ...}}. '
            "No markdown, no explanation — ONLY the JSON object."
        )
    if eval_feedback:
        extra_instruction += f"\n\nPREVIOUS EVALUATION FEEDBACK (fix these issues):\n{eval_feedback}"

    response = await ainvoke_with_retry(
        llm,
        [
            {
                "role": "system",
                "content": (
                    f"{CODE_GENERATION_BASE_SYSTEM_PROMPT}\n\n"
                    f"{FRONTEND_SYSTEM_PROMPT}\n\n"
                    "Return JSON object with exactly one top-level key: 'files'. "
                    "EVERY files[path] value must be a string containing the full file contents. "
                    "For JSON files like package.json or tsconfig.json, embed the file body as a JSON string, "
                    "not as a nested object."
                    f"{extra_instruction}"
                ),
            },
            {
                "role": "user",
                "content": f"Generate frontend files from this product context:\n\n{context}",
            },
        ],
        fallback_models=fallback_models,
    )

    parsed = _parse_json_response(response.content, {"files": {}}, label="frontend")
    files = parsed.get("files", {})
    return _normalize_frontend_files(_normalize_files_dict(files))


async def _generate_backend_files(
    llm,
    context: str,
    eval_feedback: str | None = None,
    fallback_models: list[str] | None = None,
) -> dict[str, str]:
    extra_instruction = ""
    if eval_feedback:
        extra_instruction = f"\n\nPREVIOUS EVALUATION FEEDBACK (fix these issues):\n{eval_feedback}"

    response = await ainvoke_with_retry(
        llm,
        [
            {
                "role": "system",
                "content": (
                    f"{CODE_GENERATION_BASE_SYSTEM_PROMPT}\n\n"
                    f"{BACKEND_SYSTEM_PROMPT}\n\n"
                    "Return JSON object with exactly one top-level key: 'files'. "
                    "EVERY files[path] value must be a string containing the full file contents. "
                    "For JSON files, return the file body as a JSON string, not as a nested object."
                    f"{extra_instruction}"
                ),
            },
            {
                "role": "user",
                "content": (
                    "Generate backend files from this product context. "
                    "AI features must be integral to business endpoints:\n\n"
                    f"{context}"
                ),
            },
        ],
        fallback_models=fallback_models,
    )

    parsed = _parse_json_response(response.content, {"files": {}}, label="backend")
    files = parsed.get("files", {})
    return _normalize_files_dict(files)


def _build_eval_feedback(code_eval_result: dict | None) -> str | None:
    if not code_eval_result or code_eval_result.get("passed", False):
        return None
    parts: list[str] = []
    if code_eval_result.get("fix_instructions"):
        parts.append(code_eval_result["fix_instructions"])
    if code_eval_result.get("missing_frontend"):
        parts.append(f"Missing frontend files: {', '.join(code_eval_result['missing_frontend'])}")
    if code_eval_result.get("missing_backend"):
        parts.append(f"Missing backend files: {', '.join(code_eval_result['missing_backend'])}")
    return "\n".join(parts) if parts else None


def _normalize_files_dict(files: object) -> dict[str, str]:
    if not isinstance(files, dict):
        return {}

    normalized: dict[str, str] = {}
    for key, value in files.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, str):
            normalized[key] = value
        elif isinstance(value, (dict, list)):
            normalized[key] = json.dumps(value, indent=2, ensure_ascii=False)
    return normalized


def _normalize_frontend_files(files: dict[str, str]) -> dict[str, str]:
    normalized = dict(files)

    if any(path.startswith("src/") for path in normalized):
        normalized = _normalize_frontend_import_aliases(normalized)
        normalized = _normalize_frontend_invalid_next_imports(normalized)
        normalized = _normalize_frontend_use_client_directives(normalized)
        normalized = _normalize_frontend_state_types(normalized)
        normalized = _normalize_frontend_component_exports(normalized)
        normalized.setdefault(
            "next-env.d.ts",
            '/// <reference types="next" />\n/// <reference types="next/image-types/global" />\n\n// This file is auto-generated by Next.js.\n',
        )

        normalized["tsconfig.json"] = _normalize_next_tsconfig(normalized.get("tsconfig.json", ""))
        normalized["next.config.js"] = _normalize_next_config(normalized.get("next.config.js", ""))
        normalized["tailwind.config.ts"] = _normalize_tailwind_config(normalized.get("tailwind.config.ts", ""))
        normalized["postcss.config.js"] = _normalize_postcss_config(normalized.get("postcss.config.js", ""))

    return normalized


def _normalize_frontend_import_aliases(files: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for path, content in files.items():
        if path.startswith("src/") or path.endswith((".ts", ".tsx", ".js", ".jsx")):
            normalized[path] = content.replace("@/src/", "@/")
        else:
            normalized[path] = content
    return normalized


def _normalize_frontend_component_exports(files: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for path, content in files.items():
        updated = content
        if path.startswith("src/components/") and path.endswith(".tsx") and "export default" not in content:
            match = re.search(r"export\s+function\s+([A-Z][A-Za-z0-9_]*)\s*\(", content)
            if not match:
                match = re.search(r"export\s+const\s+([A-Z][A-Za-z0-9_]*)\s*=", content)
            if match:
                component_name = match.group(1)
                updated = f"{content.rstrip()}\n\nexport default {component_name}\n"
        normalized[path] = updated
    return normalized


def _normalize_frontend_invalid_next_imports(files: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for path, content in files.items():
        updated = content
        if path.endswith((".ts", ".tsx")):
            updated = re.sub(
                r"^import\s+\{\s*API\s*\}\s+from\s+['\"]next/app['\"]\s*;?\n",
                "",
                updated,
                flags=re.MULTILINE,
            )
        normalized[path] = updated
    return normalized


def _normalize_frontend_use_client_directives(files: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    client_signal = re.compile(
        r"\b(useState|useEffect|useRef|useReducer|useTransition|useDeferredValue)\b|"
        r"\bstartTransition\b|"
        r"on[A-Z][A-Za-z]+\s*=|"
        r"\bdocument\.|\bwindow\.",
    )

    for path, content in files.items():
        updated = content
        stripped = content.lstrip()
        if path.endswith(".tsx") and not stripped.startswith('"use client"') and not stripped.startswith("'use client'"):
            if client_signal.search(content):
                updated = f'"use client";\n\n{content.lstrip()}'
        normalized[path] = updated
    return normalized


def _normalize_frontend_state_types(files: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for path, content in files.items():
        updated = content
        if path.endswith((".ts", ".tsx")):
            updated = re.sub(r"(?<!<)useState\(\s*\[\s*\]\s*\)", "useState<any[]>([])", updated)
            updated = re.sub(
                r"(?<!<)React\.useState\(\s*\[\s*\]\s*\)",
                "React.useState<any[]>([])",
                updated,
            )
            updated = re.sub(r"(?<!<)useState\(\s*\{\s*\}\s*\)", "useState<Record<string, any>>({})", updated)
            updated = re.sub(
                r"(?<!<)React\.useState\(\s*\{\s*\}\s*\)",
                "React.useState<Record<string, any>>({})",
                updated,
            )
            updated = re.sub(r"(?<!<)useState\(\s*null\s*\)", "useState<any>(null)", updated)
            updated = re.sub(r"(?<!<)React\.useState\(\s*null\s*\)", "React.useState<any>(null)", updated)
            updated = re.sub(r"(?<!<)useState\(\s*undefined\s*\)", "useState<any>(undefined)", updated)
            updated = re.sub(
                r"(?<!<)React\.useState\(\s*undefined\s*\)",
                "React.useState<any>(undefined)",
                updated,
            )
        normalized[path] = updated
    return normalized


def _normalize_next_tsconfig(raw: str) -> str:
    default = {
        "compilerOptions": {
            "target": "ES2022",
            "module": "ESNext",
            "lib": ["DOM", "DOM.Iterable", "ES2022"],
            "allowJs": False,
            "skipLibCheck": True,
            "strict": True,
            "forceConsistentCasingInFileNames": True,
            "noEmit": True,
            "esModuleInterop": True,
            "moduleResolution": "bundler",
            "resolveJsonModule": True,
            "isolatedModules": True,
            "jsx": "preserve",
            "baseUrl": ".",
            "paths": {"@/*": ["./src/*"]},
            "incremental": True,
            "plugins": [{"name": "next"}],
        },
        "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
        "exclude": ["node_modules"],
    }

    try:
        parsed = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        parsed = {}

    compiler_options = parsed.get("compilerOptions", {}) if isinstance(parsed, dict) else {}
    if not isinstance(compiler_options, dict):
        compiler_options = {}

    merged_compiler = {**default["compilerOptions"], **compiler_options}
    merged_compiler["baseUrl"] = "."
    merged_compiler["moduleResolution"] = "bundler"
    merged_compiler["jsx"] = "preserve"
    merged_compiler["paths"] = {"@/*": ["./src/*"]}
    if not isinstance(merged_compiler.get("lib"), list):
        merged_compiler["lib"] = default["compilerOptions"]["lib"]

    plugins = merged_compiler.get("plugins", [])
    if not isinstance(plugins, list):
        plugins = []
    if not any(isinstance(plugin, dict) and plugin.get("name") == "next" for plugin in plugins):
        plugins.append({"name": "next"})
    merged_compiler["plugins"] = plugins

    include = parsed.get("include", []) if isinstance(parsed, dict) else []
    if not isinstance(include, list):
        include = []
    include_items = []
    for item in default["include"] + include:
        if item not in include_items:
            include_items.append(item)

    exclude = parsed.get("exclude", default["exclude"]) if isinstance(parsed, dict) else default["exclude"]
    if not isinstance(exclude, list):
        exclude = default["exclude"]

    normalized = {
        "compilerOptions": merged_compiler,
        "include": include_items,
        "exclude": exclude,
    }
    return json.dumps(normalized, indent=2)


def _normalize_next_config(raw: str) -> str:
    if raw.strip() and "serverComponents" not in raw and "swcMinify" not in raw:
        return raw

    return (
        "module.exports = {\n"
        "  reactStrictMode: true,\n"
        "};\n"
    )


def _normalize_tailwind_config(raw: str) -> str:
    if "./src/**/*.{js,ts,jsx,tsx,mdx}" in raw:
        return raw

    return (
        "import type { Config } from 'tailwindcss';\n\n"
        "const config: Config = {\n"
        "  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],\n"
        "  theme: {\n"
        "    extend: {},\n"
        "  },\n"
        "  plugins: [],\n"
        "};\n\n"
        "export default config;\n"
    )


def _normalize_postcss_config(raw: str) -> str:
    if "module.exports" in raw and "plugins" in raw:
        return raw

    return (
        "module.exports = {\n"
        "  plugins: {\n"
        "    tailwindcss: {},\n"
        "    autoprefixer: {},\n"
        "  },\n"
        "};\n"
    )


def _parse_json_response(content, default: dict, label: str = "unknown") -> dict:
    from ..llm import content_to_str

    raw_content = content_to_str(content).strip()
    cleaned = raw_content
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning(
            "[CODE_GEN] %s: Direct JSON parse failed (response length: %d chars)",
            label,
            len(raw_content),
        )

    json_match = re.search(r"\{[\s\S]*\}", cleaned)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            logger.warning(
                "[CODE_GEN] %s: Regex JSON extraction also failed",
                label,
            )

    logger.error(
        "[CODE_GEN] %s: All JSON parse attempts failed. Returning default. Response preview: %.200s",
        label,
        raw_content,
    )
    result = dict(default)
    result["raw_response"] = raw_content[:500]
    return result
