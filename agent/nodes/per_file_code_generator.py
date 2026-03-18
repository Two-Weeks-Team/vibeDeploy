import ast
import json
import logging
import os
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_PYTHON_EXTENSIONS = frozenset({".py"})
_JS_TS_EXTENSIONS = frozenset({".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"})
_MAX_RETRY_ATTEMPTS = 3
_BROKEN_IMPORT_RE = re.compile(r"^\s*import\s+from\s*['\"]", re.MULTILINE)


class FileSpec(BaseModel):
    path: str
    file_type: Literal["page", "component", "api", "route", "service", "config", "style"]
    description: str
    dependencies: list[str] = Field(default_factory=list)


def extract_file_specs(blueprint: dict | None) -> list[FileSpec]:
    if not isinstance(blueprint, dict):
        return []

    file_specs: list[FileSpec] = []
    for section in ("frontend_files", "backend_files"):
        files = blueprint.get(section)
        if not isinstance(files, dict):
            continue

        for path, meta in files.items():
            description = "Generated file"
            dependencies: list[str] = []

            if isinstance(meta, dict):
                purpose = meta.get("purpose")
                if isinstance(purpose, str) and purpose.strip():
                    description = purpose.strip()
                imports_from = meta.get("imports_from")
                if isinstance(imports_from, list):
                    dependencies = [dep for dep in imports_from if isinstance(dep, str) and dep.strip()]
            elif isinstance(meta, str) and meta.strip():
                description = meta.strip()

            file_specs.append(
                FileSpec(
                    path=str(path),
                    file_type=_infer_file_type(str(path)),
                    description=description,
                    dependencies=dependencies,
                )
            )

    return file_specs


def validate_generated_file(path: str, content: str) -> dict[str, str | bool]:
    ext = _file_extension(path)
    if ext in _PYTHON_EXTENSIONS:
        return _validate_python(content)
    if ext in _JS_TS_EXTENSIONS:
        return _validate_js_ts(content)
    return {"passed": True, "error": ""}


def validate_generated_files(files: dict[str, str]) -> dict[str, dict[str, str | bool]]:
    return {path: validate_generated_file(path, content) for path, content in files.items()}


def generate_single_file(spec_or_path, context_or_factory, *, max_retries: int = _MAX_RETRY_ATTEMPTS):
    if isinstance(spec_or_path, FileSpec) and isinstance(context_or_factory, dict):
        return _generate_file_from_spec(spec_or_path, context_or_factory)
    if isinstance(spec_or_path, str) and callable(context_or_factory):
        return _generate_file_with_validation(spec_or_path, context_or_factory, max_retries=max_retries)
    raise TypeError("Unsupported generate_single_file arguments")


def generate_files_with_validation(files: dict[str, str], *, max_retries: int = _MAX_RETRY_ATTEMPTS) -> dict:
    final_files: dict[str, str] = {}
    validation_results: dict[str, dict[str, str | bool]] = {}
    retry_metadata: dict[str, dict[str, int | bool]] = {}

    for path, content in files.items():
        initial_result = validate_generated_file(path, content)
        if initial_result["passed"]:
            final_files[path] = content
            validation_results[path] = initial_result
            retry_metadata[path] = {"attempts": 1, "used_fallback": False}
            continue

        outcome = _generate_file_with_validation(path, lambda c=content: c, max_retries=max_retries)
        final_files[path] = outcome["content"]
        validation_results[path] = outcome["validation"]
        retry_metadata[path] = {"attempts": outcome["attempts"], "used_fallback": outcome["used_fallback"]}

    return {
        "files": final_files,
        "validation_results": validation_results,
        "retry_metadata": retry_metadata,
    }


def per_file_code_generator_node(state: dict) -> dict:
    if not os.getenv("VIBEDEPLOY_USE_PER_FILE_CODEGEN", "").strip():
        return {}

    blueprint = state.get("blueprint") if isinstance(state, dict) else {}
    blueprint = blueprint if isinstance(blueprint, dict) else {}
    specs = extract_file_specs(blueprint)

    frontend_manifest = blueprint.get("frontend_files") if isinstance(blueprint.get("frontend_files"), dict) else {}
    backend_manifest = blueprint.get("backend_files") if isinstance(blueprint.get("backend_files"), dict) else {}
    frontend_paths = set(frontend_manifest.keys())
    backend_paths = set(backend_manifest.keys())

    frontend_code = dict(state.get("frontend_code") or {})
    backend_code = dict(state.get("backend_code") or {})

    context = {
        "api_contract": state.get("api_contract"),
        "design_system": blueprint.get("design_system", {}),
        "already_generated": {},
    }

    for spec in specs:
        generated = _generate_file_from_spec(spec, context)
        context["already_generated"].update(generated)

        if spec.path in backend_paths:
            backend_code.update(generated)
        elif spec.path in frontend_paths:
            frontend_code.update(generated)
        elif _is_backend_path(spec.path):
            backend_code.update(generated)
        else:
            frontend_code.update(generated)

    return {
        "frontend_code": frontend_code,
        "backend_code": backend_code,
        "phase": "code_generated",
    }


def _build_generation_context(state: dict) -> dict:
    blueprint = state.get("blueprint") if isinstance(state, dict) else {}
    blueprint = blueprint if isinstance(blueprint, dict) else {}
    return {
        "api_contract": state.get("api_contract"),
        "design_system": blueprint.get("design_system", {}),
        "already_generated": {},
    }


async def backend_generator_node(state: dict, config=None) -> dict:
    blueprint = state.get("blueprint") if isinstance(state, dict) else {}
    blueprint = blueprint if isinstance(blueprint, dict) else {}
    specs = [
        spec
        for spec in extract_file_specs(blueprint)
        if spec.path in (blueprint.get("backend_files") or {}) or _is_backend_path(spec.path)
    ]
    backend_code = dict(state.get("backend_code") or {})
    context = _build_generation_context(state)
    for spec in specs:
        generated = _generate_file_from_spec(spec, context)
        context["already_generated"].update(generated)
        backend_code.update(generated)
    return {
        "backend_code": backend_code,
        "phase": "backend_generated",
    }


async def frontend_generator_node(state: dict, config=None) -> dict:
    blueprint = state.get("blueprint") if isinstance(state, dict) else {}
    blueprint = blueprint if isinstance(blueprint, dict) else {}
    frontend_manifest = blueprint.get("frontend_files") or {}
    specs = [
        spec
        for spec in extract_file_specs(blueprint)
        if spec.path in frontend_manifest and not _is_backend_path(spec.path)
    ]
    frontend_code = dict(state.get("frontend_code") or {})
    context = _build_generation_context(state)
    context["already_generated"].update(frontend_code)
    for spec in specs:
        generated = _generate_file_from_spec(spec, context)
        context["already_generated"].update(generated)
        frontend_code.update(generated)
    return {
        "frontend_code": frontend_code,
        "phase": "frontend_generated",
    }


def _generate_file_from_spec(spec: FileSpec, context: dict) -> dict[str, str]:
    api_contract = context.get("api_contract")
    design_system = context.get("design_system")

    if spec.file_type == "page":
        content = _page_template(spec.path, spec.description, design_system)
    elif spec.file_type == "component":
        content = _component_template(spec.path, spec.description)
    elif spec.file_type == "api":
        content = _api_template(spec.path, spec.description, api_contract)
    elif spec.file_type == "route":
        content = _route_template(spec.path, spec.description)
    elif spec.file_type == "service":
        content = _service_template(spec.path, spec.description)
    elif spec.file_type == "config":
        content = _config_template(spec.path, spec.description, design_system)
    else:
        content = _style_template(spec.description)

    return {spec.path: content}


def _generate_file_with_validation(path: str, content_factory, *, max_retries: int = _MAX_RETRY_ATTEMPTS) -> dict:
    last_result: dict[str, str | bool] = {"passed": False, "error": "max_retries=0"}
    content = ""

    for attempt in range(1, max_retries + 1):
        try:
            content = content_factory()
        except Exception as exc:  # noqa: BLE001
            last_result = {"passed": False, "error": f"content_factory raised: {exc}"}
            logger.warning("[PER_FILE_CODEGEN] attempt %d/%d factory error for %s: %s", attempt, max_retries, path, exc)
            continue

        result = validate_generated_file(path, content)
        if result["passed"]:
            return {
                "content": content,
                "validation": result,
                "attempts": attempt,
                "used_fallback": False,
            }

        last_result = result
        logger.warning(
            "[PER_FILE_CODEGEN] attempt %d/%d validation failed for %s: %s",
            attempt,
            max_retries,
            path,
            result["error"],
        )

    return {
        "content": _fallback_content(path),
        "validation": last_result,
        "attempts": max_retries,
        "used_fallback": True,
    }


def _infer_file_type(path: str) -> Literal["page", "component", "api", "route", "service", "config", "style"]:
    normalized = str(path).replace("\\", "/").lower()
    file_name = Path(normalized).name

    if file_name in {"page.tsx", "page.jsx"}:
        return "page"
    if normalized.endswith(".module.css") or normalized.endswith(".css") or normalized.endswith(".scss"):
        return "style"
    if "/components/" in normalized and normalized.endswith((".tsx", ".jsx", ".ts", ".js")):
        return "component"
    if file_name in {"routes.py", "route.py"} or "router" in file_name:
        return "route"
    if "service" in file_name:
        return "service"
    if "api" in file_name or normalized.endswith("src/lib/api.ts") or normalized.endswith("src/lib/api.js"):
        return "api"
    if file_name in {
        "package.json",
        "requirements.txt",
        "pyproject.toml",
        "tsconfig.json",
        "next.config.js",
        "next.config.ts",
    }:
        return "config"
    if normalized.endswith(".py"):
        return "service"
    if normalized.endswith((".tsx", ".jsx", ".ts", ".js")):
        return "component"
    return "config"


def _to_identifier(path: str) -> str:
    stem = Path(path).stem
    parts = [part for part in stem.replace("-", "_").split("_") if part]
    if not parts:
        return "Generated"
    return "".join(part[:1].upper() + part[1:] for part in parts)


def _page_template(path: str, description: str, design_system: dict | None) -> str:
    visual_direction = "product-focused interface"
    if isinstance(design_system, dict):
        candidate = design_system.get("visual_direction")
        if isinstance(candidate, str) and candidate.strip():
            visual_direction = candidate.strip()

    return (
        "export default function Page() {\n"
        "  return (\n"
        "    <main>\n"
        f"      <h1>{description}</h1>\n"
        f"      <p>{visual_direction}</p>\n"
        "    </main>\n"
        "  );\n"
        "}\n"
    )


def _component_template(path: str, description: str) -> str:
    component_name = _to_identifier(path)
    return (
        f"type {component_name}Props = {{\n"
        "  title?: string;\n"
        "};\n\n"
        f'export function {component_name}({{ title = "{description}" }}: {component_name}Props) {{\n'
        "  return <section>{title}</section>;\n"
        "}\n\n"
        f"export default {component_name};\n"
    )


def _api_template(path: str, description: str, api_contract: object) -> str:
    contract_hint = ""
    if isinstance(api_contract, str) and api_contract.strip():
        contract_hint = api_contract.strip().splitlines()[0]

    return (
        'import { NextResponse } from "next/server";\n\n'
        "export async function POST(request: Request) {\n"
        "  const body = await request.json();\n"
        "  return NextResponse.json({\n"
        f'    message: "{description}",\n'
        f'    contract: "{contract_hint}",\n'
        "    body,\n"
        "  });\n"
        "}\n"
    )


def _route_template(path: str, description: str) -> str:
    return (
        "from fastapi import APIRouter\n\n"
        "router = APIRouter()\n\n"
        '@router.get("/health")\n'
        "async def health() -> dict[str, str]:\n"
        f'    return {{"status": "ok", "detail": "{description}"}}\n'
    )


def _service_template(path: str, description: str) -> str:
    class_name = _to_identifier(path) + "Service"
    return (
        f"class {class_name}:\n"
        f'    """{description}"""\n\n'
        "    def execute(self) -> dict[str, str]:\n"
        '        return {"status": "stub"}\n'
    )


def _config_template(path: str, description: str, design_system: dict | None) -> str:
    normalized = path.lower()
    if normalized.endswith("package.json"):
        payload = {"name": "generated-app", "private": True, "description": description}
        return json.dumps(payload, indent=2)
    if normalized.endswith("requirements.txt"):
        return "fastapi\nuvicorn\n"
    if normalized.endswith((".json", ".toml")):
        payload = {"description": description}
        if isinstance(design_system, dict) and design_system.get("typography"):
            payload["typography"] = str(design_system["typography"])
        return json.dumps(payload, indent=2)
    return f'export const config = {{ description: "{description}" }};\n'


def _style_template(description: str) -> str:
    return f'.container {{\n  display: block;\n}}\n\n.title {{\n  content: "{description}";\n}}\n'


def _is_backend_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    return normalized.endswith(".py") or normalized == "requirements.txt"


def _file_extension(path: str) -> str:
    dot = path.rfind(".")
    return "" if dot == -1 else path[dot:].lower()


def _validate_python(content: str) -> dict[str, str | bool]:
    if not content.strip():
        return {"passed": True, "error": ""}
    try:
        ast.parse(content)
        return {"passed": True, "error": ""}
    except SyntaxError as exc:
        return {"passed": False, "error": f"SyntaxError: {exc}"}


def _validate_js_ts(content: str) -> dict[str, str | bool]:
    if not content.strip():
        return {"passed": True, "error": ""}
    balance_error = _check_bracket_balance(content)
    if balance_error:
        return {"passed": False, "error": balance_error}
    import_error = _check_import_export_basics(content)
    if import_error:
        return {"passed": False, "error": import_error}
    return {"passed": True, "error": ""}


def _check_bracket_balance(content: str) -> str:
    stack: list[str] = []
    close_to_open = {")": "(", "}": "{", "]": "["}
    open_chars = frozenset("({[")
    close_chars = frozenset(")}]")

    in_single_quote = False
    in_double_quote = False
    in_template = False
    in_line_comment = False
    in_block_comment = False

    i = 0
    n = len(content)
    while i < n:
        ch = content[i]

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            if ch == "*" and i + 1 < n and content[i + 1] == "/":
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue

        if in_single_quote:
            if ch == "\\" and i + 1 < n:
                i += 2
                continue
            if ch == "'":
                in_single_quote = False
            i += 1
            continue

        if in_double_quote:
            if ch == "\\" and i + 1 < n:
                i += 2
                continue
            if ch == '"':
                in_double_quote = False
            i += 1
            continue

        if in_template:
            if ch == "\\" and i + 1 < n:
                i += 2
                continue
            if ch == "`":
                in_template = False
            i += 1
            continue

        if ch == "/" and i + 1 < n:
            if content[i + 1] == "/":
                in_line_comment = True
                i += 2
                continue
            if content[i + 1] == "*":
                in_block_comment = True
                i += 2
                continue

        if ch == "'":
            in_single_quote = True
            i += 1
            continue
        if ch == '"':
            in_double_quote = True
            i += 1
            continue
        if ch == "`":
            in_template = True
            i += 1
            continue

        if ch in open_chars:
            stack.append(ch)
        elif ch in close_chars:
            expected_open = close_to_open[ch]
            if not stack or stack[-1] != expected_open:
                return f"Unbalanced bracket: unexpected '{ch}' at position {i}"
            stack.pop()

        i += 1

    if stack:
        return f"Unbalanced bracket: unclosed '{stack[-1]}'"
    return ""


def _check_import_export_basics(content: str) -> str:
    if _BROKEN_IMPORT_RE.search(content):
        return "Invalid import: missing binding before 'from' (e.g. 'import from \"module\"')"
    return ""


def _fallback_content(path: str) -> str:
    ext = _file_extension(path)
    tag = "//" if ext in _JS_TS_EXTENSIONS else "#"
    return f"{tag} vibedeploy-fallback: validation failed after max retries\n{tag} path: {path}\n"
