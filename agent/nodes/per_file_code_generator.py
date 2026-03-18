import ast
import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from agent.llm import (
    MODEL_CONFIG,
    ainvoke_with_retry,
    content_to_str,
    get_llm,
    llm_auth_route_for_model,
    llm_credentials_available,
)
from agent.nodes.per_file_prompts import build_prompt

logger = logging.getLogger(__name__)

_PYTHON_EXTENSIONS = frozenset({".py"})
_JS_TS_EXTENSIONS = frozenset({".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"})
_MAX_RETRY_ATTEMPTS = 3
_BROKEN_IMPORT_RE = re.compile(r"^\s*import\s+from\s*['\"]", re.MULTILINE)


def _use_llm_per_file_generation() -> bool:
    return os.getenv("VIBEDEPLOY_USE_LLM_PER_FILE_GENERATION", "").strip().lower() in {"1", "true", "yes", "on"}


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


_MAX_PARALLEL_LLM = int(os.environ.get("VIBEDEPLOY_MAX_PARALLEL_LLM", "4"))


async def _generate_tier_parallel(
    specs: list,
    context: dict,
    code_store: dict,
    warnings: list,
    file_type_filter: set[str],
    is_frontend: bool,
) -> None:
    model_key = "code_gen_frontend" if is_frontend else "code_gen_backend"
    model = MODEL_CONFIG.get(model_key, MODEL_CONFIG["code_gen"])
    semaphore = asyncio.Semaphore(_MAX_PARALLEL_LLM)

    async def _generate_one(spec) -> tuple[str, dict[str, str]]:
        async with semaphore:
            if _use_llm_per_file_generation() and spec.file_type in file_type_filter:
                if not llm_credentials_available(model):
                    warnings.append(f"per_file_llm_unavailable:{model}")
                    return spec.path, _generate_file_from_spec(spec, context)
                try:
                    content = await _generate_file_with_llm(spec, context)
                    route = llm_auth_route_for_model(model) or "unknown"
                    target = "frontend" if is_frontend else "backend"
                    warnings.append(f"per_file_{target}_llm_used:{model}:{route}")
                    return spec.path, {spec.path: content}
                except Exception as exc:
                    target = "frontend" if is_frontend else "backend"
                    logger.warning("[PER_FILE_LLM] %s fallback for %s: %s", target, spec.path, str(exc)[:200])
                    warnings.append(f"per_file_{target}_llm_fallback:{spec.path}")
                    return spec.path, _generate_file_from_spec(spec, context)
            else:
                try:
                    return spec.path, _generate_file_from_spec(spec, context)
                except Exception:
                    return spec.path, _generate_file_from_spec(spec, context)

    results = await asyncio.gather(*[_generate_one(spec) for spec in specs])
    for _, generated in results:
        code_store.update(generated)
        context["already_generated"].update(generated)


def _build_generation_context(state: dict) -> dict:
    blueprint = state.get("blueprint") if isinstance(state, dict) else {}
    blueprint = blueprint if isinstance(blueprint, dict) else {}
    wiring = state.get("wiring_validation") or {}
    repair_instructions = wiring.get("repair_instructions") or []
    return {
        "api_contract": state.get("api_contract"),
        "design_system": blueprint.get("design_system", {}),
        "design_system_context": state.get("design_system_context") or {},
        "prompt_strategy": state.get("prompt_strategy") or {},
        "generated_types": state.get("generated_types") or {},
        "pydantic_models": state.get("pydantic_models") or "",
        "frontend_code": dict(state.get("frontend_code") or {}),
        "backend_code": dict(state.get("backend_code") or {}),
        "already_generated": {},
        "repair_instructions": repair_instructions,
        "wiring_missing": wiring.get("missing") or [],
        "wiring_schema_mismatches": wiring.get("schema_mismatches") or [],
        "build_errors": str(state.get("build_errors") or "").strip(),
    }


def _template_key_for_spec(spec: FileSpec) -> str:
    normalized = spec.path.replace("\\", "/")
    if normalized.endswith("page.tsx"):
        return "page.tsx"
    if normalized.endswith("src/lib/api.ts"):
        return "api.ts"
    if normalized.endswith("routes.py"):
        return "routes.py"
    if normalized.endswith("ai_service.py"):
        return "ai_service.py"
    if normalized.endswith(".tsx"):
        return "component.tsx"
    return spec.file_type


def _stringify_context_value(value) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    try:
        return json.dumps(value, ensure_ascii=False, indent=2)
    except TypeError:
        return str(value)


def _prompt_context_for_spec(spec: FileSpec, context: dict) -> dict:
    blueprint_design = context.get("design_system") or {}
    design_system_context = context.get("design_system_context") or {}
    prompt_strategy = context.get("prompt_strategy") or {}
    frontend_code = context.get("frontend_code") or {}
    backend_code = context.get("backend_code") or {}
    template_key = _template_key_for_spec(spec)
    target = "backend" if _is_backend_path(spec.path) else "frontend"
    appendix_key = f"{target}_prompt_appendix"
    contract_note = (
        "Use the generated typed API client at src/lib/api-client.ts where possible. "
        "Do not invent endpoints; only use the OpenAPI contract."
        if target == "frontend"
        else "Implement only endpoints and response shapes defined in the OpenAPI contract."
    )
    context_map = {
        "file_path": spec.path,
        "description": spec.description,
        "design_system": _stringify_context_value(design_system_context or blueprint_design),
        "layout": _stringify_context_value((design_system_context or {}).get("experience_contract") or {}),
        "navigation": _stringify_context_value(
            {
                "dependencies": spec.dependencies,
                "already_generated": list((context.get("already_generated") or {}).keys()),
            }
        ),
        "props_spec": _stringify_context_value({"dependencies": spec.dependencies, "contract_note": contract_note}),
        "api_contract": _stringify_context_value(context.get("api_contract") or ""),
        "types": _stringify_context_value(frontend_code.get("src/types/api.d.ts") or ""),
        "models": _stringify_context_value(backend_code.get("schemas.py") or context.get("pydantic_models") or ""),
    }
    prompt = build_prompt(template_key, context_map)
    appendix = str(prompt_strategy.get(appendix_key) or "").strip()
    if appendix:
        prompt = f"{prompt}\n\nAdditional Strategy:\n{appendix}"

    repair_lines = []
    repair_instructions = context.get("repair_instructions") or []
    wiring_missing = context.get("wiring_missing") or []
    build_errors = context.get("build_errors") or ""

    if target == "frontend" and _is_page_file(spec.path):
        available_exports = context.get("available_exports") or {}
        if available_exports:
            export_lines = []
            for file_path, info in sorted(available_exports.items()):
                module = (
                    "@/" + file_path.replace("src/", "", 1).rsplit(".", 1)[0]
                    if file_path.startswith("src/")
                    else file_path.rsplit(".", 1)[0]
                )
                defaults = info.get("default") or []
                named = info.get("named") or []
                props_map = info.get("props") or {}
                if defaults:
                    sig = props_map.get(defaults[0], "")
                    props_note = f"  // props: {sig}" if sig else "  // default export"
                    export_lines.append(f'  import {defaults[0]} from "{module}";{props_note}')
                if named:
                    for n in named:
                        sig = props_map.get(n, "")
                        props_note = f"  // props: {sig}" if sig else ""
                        export_lines.append(f'  import {{ {n} }} from "{module}";{props_note}')

    if target == "backend" and (repair_instructions or wiring_missing):
        if wiring_missing:
            repair_lines.append(
                "CRITICAL — Previous attempt FAILED contract validation. "
                "These endpoints are MISSING from your code and MUST be added:\n"
                + "\n".join(f"  - {ep}" for ep in wiring_missing)
            )
        for instr in repair_instructions:
            action = instr.get("action", "")
            if action == "add_endpoint":
                repair_lines.append(f"Add route: {instr.get('method', 'GET')} {instr.get('path', '/')}")
            elif action == "add_model":
                repair_lines.append(f"Add Pydantic model: {instr.get('schema', '?')}")
            elif action == "add_field":
                repair_lines.append(f"Add field '{instr.get('field')}' to {instr.get('schema', '?')}")

    if build_errors:
        repair_lines.append(
            "CRITICAL — Previous attempt FAILED build validation. Fix these errors:\n" + build_errors[:1500]
        )

    if repair_lines:
        prompt = f"{prompt}\n\n## Repair Feedback (MUST FIX)\n" + "\n".join(repair_lines)

    return {"template_key": template_key, "target": target, "prompt": prompt}


def _extract_balanced_json_block(raw: str) -> str | None:
    for start_index, char in enumerate(raw):
        if char != "{":
            continue
        stack = ["}"]
        in_string = False
        escaped = False
        for index in range(start_index + 1, len(raw)):
            current = raw[index]
            if in_string:
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == '"':
                    in_string = False
                continue
            if current == '"':
                in_string = True
                continue
            if current == "{":
                stack.append("}")
                continue
            if current == "}":
                if not stack:
                    break
                stack.pop()
                if not stack:
                    return raw[start_index : index + 1]
    return None


def _parse_single_file_payload(raw: str, path: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json|tsx|ts|py)?\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    json_block = _extract_balanced_json_block(cleaned)
    if json_block:
        try:
            parsed = json.loads(json_block)
            if isinstance(parsed, dict):
                if isinstance(parsed.get("content"), str):
                    return parsed["content"]
                files = parsed.get("files")
                if isinstance(files, dict) and isinstance(files.get(path), str):
                    return files[path]
        except json.JSONDecodeError:
            pass
    return cleaned


def _has_truncated_jsx(content: str, path: str) -> bool:
    if not path.endswith((".tsx", ".jsx")):
        return False
    if not content or not content.strip():
        return True
    lines = [ln for ln in content.splitlines() if ln.strip()]
    if not lines:
        return True
    last = lines[-1].strip()
    if last.endswith((";", "}", ")", ">", "/>")):
        return False
    if last.startswith("//") or last.startswith("/*") or last.startswith("*"):
        return False
    return True


async def _generate_file_via_responses_api(
    model: str,
    instructions: str,
    user_prompt: str,
    path: str,
) -> str:
    import openai

    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if not openai_key or openai_key in ("test-key", ""):
        raise ValueError("OPENAI_API_KEY not set for direct responses API call")

    client = openai.AsyncOpenAI(api_key=openai_key)
    for attempt in range(1, 4):
        response = await client.responses.create(
            model=model,
            instructions=instructions,
            input=user_prompt,
            reasoning={"effort": "medium"},
        )
        content = _parse_single_file_payload(response.output_text, path)
        if not _has_truncated_jsx(content, path):
            return content
        logger.warning("[PER_FILE_RESPONSES] truncated JSX in %s (attempt %d), retrying", path, attempt)
        user_prompt = (
            "CRITICAL: Previous output was TRUNCATED. Generate the SAME file but COMPLETE without cutoff.\n\n"
            + user_prompt
        )
    return content


async def _generate_file_with_llm(spec: FileSpec, context: dict) -> str:
    from agent.model_capabilities import model_endpoint_type

    prompt_meta = _prompt_context_for_spec(spec, context)
    target = prompt_meta["target"]
    model_key = "code_gen_backend" if target == "backend" else "code_gen_frontend"
    model = MODEL_CONFIG.get(model_key, MODEL_CONFIG["code_gen"])
    is_page = target == "frontend" and _is_page_file(spec.path)
    available_exports = context.get("available_exports") or {}

    if is_page and available_exports:
        import_rule = (
            "CRITICAL IMPORT RULE: Only import from the exact module paths and export names listed "
            "in the '## Available Component Exports' section below. "
            "Do NOT invent or assume any export that is not explicitly listed there. "
            "If a module exports a default, use `import Name from 'path'`. "
            "If a module exports named, use `import { Name } from 'path'`. "
            "Mixing these up causes build failures."
        )
    else:
        import_rule = ""

    system_content = (
        "Generate exactly one file. Return ONLY the raw file content — no JSON wrapping, no markdown fences, no prose. "
        "Every JSX element MUST be properly closed. File MUST end with closing brace or export statement."
    )
    if import_rule:
        system_content = f"{system_content}\n\n{import_rule}"

    if model_endpoint_type(model) == "responses" or model.startswith("gpt-5"):
        try:
            return await _generate_file_via_responses_api(
                model=model,
                instructions=system_content,
                user_prompt=prompt_meta["prompt"],
                path=spec.path,
            )
        except Exception as exc:
            logger.warning("[PER_FILE_LLM] responses API failed for %s (%s), falling back to LangChain", spec.path, exc)

    llm = get_llm(model=model, temperature=0.1, max_tokens=12000)
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": prompt_meta["prompt"]},
    ]
    response = await ainvoke_with_retry(llm, messages, max_attempts=3)
    return _parse_single_file_payload(content_to_str(response.content), spec.path)


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
    warnings = list(state.get("code_gen_warnings") or [])

    is_retry = bool(context.get("wiring_missing") or context.get("repair_instructions") or context.get("build_errors"))
    build_errors_text = context.get("build_errors") or ""
    if is_retry:
        logger.info(
            "[BACKEND_GEN] Retry with feedback: missing=%s build_errors=%s",
            context.get("wiring_missing") or [],
            bool(build_errors_text),
        )

    for spec in specs:
        if spec.path in backend_code and _should_preserve_existing_file(spec.path):
            continue
        if (
            is_retry
            and spec.path in backend_code
            and spec.file_type not in {"route", "service"}
            and spec.path not in build_errors_text
        ):
            continue
        if _use_llm_per_file_generation() and spec.file_type in {"route", "service", "api"}:
            model = MODEL_CONFIG.get("code_gen_backend", MODEL_CONFIG["code_gen"])
            if not llm_credentials_available(model):
                warnings.append(f"per_file_backend_llm_unavailable:{model}")
                generated = _generate_file_from_spec(spec, context)
            else:
                try:
                    generated = {spec.path: await _generate_file_with_llm(spec, context)}
                    route = llm_auth_route_for_model(model) or "unknown"
                    warnings.append(f"per_file_backend_llm_used:{model}:{route}")
                except Exception as exc:
                    logger.warning("[PER_FILE_LLM] backend fallback for %s: %s", spec.path, str(exc)[:200])
                    warnings.append(f"per_file_backend_llm_fallback:{spec.path}")
                    generated = _generate_file_from_spec(spec, context)
        else:
            try:
                generated = _generate_file_from_spec(spec, context)
            except Exception:
                generated = _generate_file_from_spec(spec, context)
        context["already_generated"].update(generated)
        backend_code.update(generated)
        context["backend_code"] = dict(backend_code)
    return {
        "backend_code": backend_code,
        "phase": "backend_generated",
        "code_gen_warnings": warnings,
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
    warnings = list(state.get("code_gen_warnings") or [])

    is_retry = bool(context.get("wiring_missing") or context.get("repair_instructions") or context.get("build_errors"))
    build_errors_text = context.get("build_errors") or ""
    build_failing_files = list(state.get("build_failing_files") or [])

    def _should_skip(spec) -> bool:
        if spec.path in frontend_code and _should_preserve_existing_file(spec.path):
            return True
        if is_retry and spec.path in frontend_code:
            if build_failing_files:
                normalized = spec.path.replace("./", "").lstrip("/")
                if not any(normalized in fp or fp in normalized for fp in build_failing_files):
                    return True
            elif spec.path not in build_errors_text:
                return True
        return False

    specs_to_generate = [s for s in specs if not _should_skip(s)]

    page_specs = [s for s in specs_to_generate if _is_page_file(s.path)]
    component_specs = [s for s in specs_to_generate if not _is_page_file(s.path)]

    for spec in component_specs:
        generated = _generate_file_from_spec(spec, context)
        frontend_code.update(generated)
        context["already_generated"].update(generated)
    context["frontend_code"] = dict(frontend_code)

    for spec in page_specs:
        all_frontend = dict(context.get("frontend_code") or {})
        all_frontend.update(context["already_generated"])
        component_code = {p: c for p, c in all_frontend.items() if not _is_page_file(p)}
        exports = _extract_component_exports(component_code)
        context["available_exports"] = exports
        logger.info(
            "[FRONTEND_GEN] page.tsx injection: %d files, api_client=%s",
            len(component_code),
            "src/lib/api-client.ts" in component_code,
        )
        if _use_llm_per_file_generation() and spec.file_type in {"page", "component", "api"}:
            model = MODEL_CONFIG.get("code_gen_frontend", MODEL_CONFIG["code_gen"])
            if not llm_credentials_available(model):
                warnings.append(f"per_file_frontend_llm_unavailable:{model}")
                generated = _generate_file_from_spec(spec, context)
            else:
                try:
                    generated = {spec.path: await _generate_file_with_llm(spec, context)}
                    route = llm_auth_route_for_model(model) or "unknown"
                    warnings.append(f"per_file_frontend_llm_used:{model}:{route}")
                except Exception as exc:
                    logger.warning("[PER_FILE_LLM] page fallback for %s: %s", spec.path, str(exc)[:200])
                    warnings.append(f"per_file_frontend_llm_fallback:{spec.path}")
                    generated = _generate_file_from_spec(spec, context)
        else:
            generated = _generate_file_from_spec(spec, context)
        context["already_generated"].update(generated)
        frontend_code.update(generated)
        context["frontend_code"] = dict(frontend_code)

    return {
        "frontend_code": frontend_code,
        "phase": "frontend_generated",
        "code_gen_warnings": warnings,
    }


async def frontend_file_repairer_node(state: dict, config=None) -> dict:
    build_errors_full = state.get("build_errors_full") or state.get("build_errors") or ""
    build_failing_files = list(state.get("build_failing_files") or [])
    frontend_code = dict(state.get("frontend_code") or {})
    blueprint = state.get("blueprint") if isinstance(state, dict) else {}
    blueprint = blueprint if isinstance(blueprint, dict) else {}
    warnings = list(state.get("code_gen_warnings") or [])

    all_specs = {s.path: s for s in extract_file_specs(blueprint) if not _is_backend_path(s.path)}

    context = _build_generation_context(state)
    context["already_generated"].update(frontend_code)
    context["build_errors"] = build_errors_full

    target_paths: list[str] = []
    for fp in build_failing_files:
        normalized = fp.replace("./", "").lstrip("/")
        if normalized in all_specs:
            target_paths.append(normalized)
        else:
            for spec_path in all_specs:
                if normalized in spec_path or spec_path.endswith(normalized.split("/")[-1]):
                    target_paths.append(spec_path)
                    break

    if not target_paths:
        logger.warning("[FILE_REPAIR] No matching specs for failing files: %s", build_failing_files)
        return {"phase": "frontend_generated", "build_failing_files": []}

    logger.info("[FILE_REPAIR] Repairing %d files: %s", len(target_paths), target_paths)

    specs_to_repair = [all_specs[p] for p in target_paths if p in all_specs]
    page_repairs = [s for s in specs_to_repair if _is_page_file(s.path)]
    component_repairs = [s for s in specs_to_repair if not _is_page_file(s.path)]

    for spec in component_repairs:
        generated = _generate_file_from_spec(spec, context)
        frontend_code.update(generated)
        context["already_generated"].update(generated)
    context["frontend_code"] = dict(frontend_code)

    for spec in page_repairs:
        all_fe = dict(context.get("frontend_code") or {})
        all_fe.update(context["already_generated"])
        component_code = {p: c for p, c in all_fe.items() if not _is_page_file(p)}
        context["available_exports"] = _extract_component_exports(component_code)
        if state.get("build_errors"):
            logger.info("[FILE_REPAIR] Using deterministic rescue for %s", spec.path)
            generated = _generate_file_from_spec(spec, context)
            frontend_code.update(generated)
            continue
        if _use_llm_per_file_generation():
            model = MODEL_CONFIG.get("code_gen_frontend", MODEL_CONFIG["code_gen"])
            if llm_credentials_available(model):
                try:
                    content = await _generate_file_with_llm(spec, context)
                    frontend_code[spec.path] = content
                    warnings.append(f"per_file_repair_llm_used:{model}")
                    continue
                except Exception as exc:
                    logger.warning("[FILE_REPAIR] LLM failed for %s: %s", spec.path, exc)
        generated = _generate_file_from_spec(spec, context)
        frontend_code.update(generated)

    return {
        "frontend_code": frontend_code,
        "phase": "frontend_generated",
        "code_gen_warnings": warnings,
        "build_failing_files": [],
    }


def _generate_file_from_spec(spec: FileSpec, context: dict) -> dict[str, str]:
    api_contract = context.get("api_contract")
    design_system = context.get("design_system")

    if spec.file_type == "page":
        content = _page_template(spec.path, spec.description, design_system, api_contract)
    elif spec.file_type == "component":
        content = _component_template(spec.path, spec.description)
    elif spec.file_type == "api":
        content = _api_template(spec.path, spec.description, api_contract)
    elif spec.file_type == "route":
        content = _route_template(spec.path, spec.description, api_contract)
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


def _parse_api_contract(api_contract: object) -> dict:
    if isinstance(api_contract, str) and api_contract.strip():
        try:
            parsed = json.loads(api_contract)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    if isinstance(api_contract, dict):
        return api_contract
    return {}


def _schema_properties(spec: dict, schema_ref: str | None) -> dict[str, dict]:
    if not schema_ref:
        return {}
    schema_name = schema_ref.split("/")[-1]
    components = spec.get("components") or {}
    schemas = components.get("schemas") or {} if isinstance(components, dict) else {}
    schema = schemas.get(schema_name) or {}
    if not isinstance(schema, dict):
        return {}
    properties = schema.get("properties") or {}
    return properties if isinstance(properties, dict) else {}


def _contract_operations(api_contract: object) -> list[dict[str, object]]:
    spec = _parse_api_contract(api_contract)
    paths = spec.get("paths") or {}
    operations: list[dict[str, object]] = []
    if not isinstance(paths, dict):
        return operations
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"} or not isinstance(operation, dict):
                continue
            req_schema_ref = None
            req_body = operation.get("requestBody") or {}
            if isinstance(req_body, dict):
                content = req_body.get("content") or {}
                if isinstance(content, dict):
                    app_json = content.get("application/json") or {}
                    if isinstance(app_json, dict):
                        schema = app_json.get("schema") or {}
                        if isinstance(schema, dict) and "$ref" in schema:
                            req_schema_ref = str(schema["$ref"])
            resp_schema_ref = None
            responses = operation.get("responses") or {}
            if isinstance(responses, dict):
                ok = responses.get("200") or next(iter(responses.values()), {})
                if isinstance(ok, dict):
                    content = ok.get("content") or {}
                    if isinstance(content, dict):
                        app_json = content.get("application/json") or {}
                        if isinstance(app_json, dict):
                            schema = app_json.get("schema") or {}
                            if isinstance(schema, dict) and "$ref" in schema:
                                resp_schema_ref = str(schema["$ref"])
            operations.append(
                {
                    "method": method.upper(),
                    "path": str(path),
                    "request_fields": list(_schema_properties(spec, req_schema_ref).keys()),
                    "response_fields": list(_schema_properties(spec, resp_schema_ref).keys()),
                }
            )
    return operations


def _pick_ops(api_contract: object) -> tuple[dict | None, dict | None, dict | None]:
    ops = _contract_operations(api_contract)
    get_op = next((op for op in ops if op["method"] == "GET"), None)
    insights_op = next((op for op in ops if op["method"] == "POST" and "insight" in str(op["path"]).lower()), None)
    primary_post = next(
        (op for op in ops if op["method"] == "POST" and (insights_op is None or op["path"] != insights_op["path"])),
        None,
    )
    return get_op, primary_post, insights_op


def _page_template(path: str, description: str, design_system: dict | None, api_contract: object) -> str:
    visual_direction = "product-focused interface"
    if isinstance(design_system, dict):
        candidate = design_system.get("visual_direction")
        if isinstance(candidate, str) and candidate.strip():
            visual_direction = candidate.strip()
    get_op, primary_post, insights_op = _pick_ops(api_contract)
    return (
        '"use client";\n\n'
        'import { useEffect, useState } from "react";\n'
        'import Hero from "@/components/Hero";\n'
        'import WorkspacePanel from "@/components/WorkspacePanel";\n'
        'import InsightPanel from "@/components/InsightPanel";\n'
        'import CollectionPanel from "@/components/CollectionPanel";\n'
        'import StatePanel from "@/components/StatePanel";\n'
        'import { fetchItems, createPlan, fetchInsights } from "@/lib/api";\n\n'
        "type Plan = { summary?: string; items?: unknown[]; score?: number };\n"
        "type Insights = { insights?: string[]; next_actions?: string[]; highlights?: string[] } | null;\n\n"
        "export default function Page() {\n"
        '  const [query, setQuery] = useState("");\n'
        '  const [preferences, setPreferences] = useState("");\n'
        "  const [collection, setCollection] = useState<unknown[]>([]);\n"
        "  const [plan, setPlan] = useState<Plan | null>(null);\n"
        "  const [insights, setInsights] = useState<Insights>(null);\n"
        "  const [loading, setLoading] = useState(false);\n"
        '  const [error, setError] = useState("");\n\n'
        "  useEffect(() => {\n"
        "    let active = true;\n"
        "    fetchItems()\n"
        "      .then((data) => { if (active) setCollection(Array.isArray(data) ? data : (data.items ?? [])); })\n"
        '      .catch((err) => { if (active) setError(err instanceof Error ? err.message : "Failed to load starter data"); });\n'
        "    return () => { active = false; };\n"
        "  }, []);\n\n"
        "  async function handleGenerate() {\n"
        "    setLoading(true);\n"
        '    setError("");\n'
        "    try {\n"
        '      const generated = await createPlan({ query: query || "meal plan", preferences });\n'
        "      setPlan(generated);\n"
        "      try {\n"
        '        const nextInsights = await fetchInsights((generated.summary ?? query) || "meal plan", preferences || query || "meal plan");\n'
        "        setInsights(nextInsights);\n"
        "      } catch {\n"
        "        setInsights(null);\n"
        "      }\n"
        "    } catch (err) {\n"
        '      setError(err instanceof Error ? err.message : "Failed to generate plan");\n'
        "    } finally {\n"
        "      setLoading(false);\n"
        "    }\n"
        "  }\n\n"
        "  return (\n"
        '    <main className="min-h-screen bg-background text-foreground">\n'
        '      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-6 py-10">\n'
        f'        <Hero title="{description}" subtitle="{visual_direction}" />\n'
        "        <StatePanel loading={loading} error={error} />\n"
        '        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">\n'
        "          <WorkspacePanel query={query} preferences={preferences} onQueryChange={setQuery} onPreferencesChange={setPreferences} onGenerate={handleGenerate} loading={loading} />\n"
        '          <InsightPanel summary={plan?.summary ?? "Generate a complete plan to see today\'s five-meal spread."} items={plan?.items ?? []} score={plan?.score ?? 0} insights={insights} />\n'
        "        </div>\n"
        "        <CollectionPanel items={collection} />\n"
        "      </div>\n"
        "    </main>\n"
        "  );\n"
        "}\n"
    )


def _component_template(path: str, description: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized.endswith("/Hero.tsx"):
        return (
            "type HeroProps = { title: string; subtitle: string };\n\n"
            "export default function Hero({ title, subtitle }: HeroProps) {\n"
            "  return (\n"
            '    <section className="rounded-3xl border border-border bg-card/80 p-8 shadow-card">\n'
            '      <p className="text-xs uppercase tracking-[0.3em] text-muted-foreground">Dietitian Folio</p>\n'
            '      <h1 className="mt-3 font-[--font-display] text-4xl font-semibold">{title}</h1>\n'
            '      <p className="mt-3 max-w-3xl text-lg text-muted-foreground">{subtitle}</p>\n'
            "    </section>\n"
            "  );\n"
            "}\n"
        )
    if normalized.endswith("/WorkspacePanel.tsx"):
        return (
            "type Props = { query: string; preferences: string; onQueryChange: (value: string) => void; onPreferencesChange: (value: string) => void; onGenerate: () => void; loading: boolean };\n\n"
            "export default function WorkspacePanel({ query, preferences, onQueryChange, onPreferencesChange, onGenerate, loading }: Props) {\n"
            "  return (\n"
            '    <section className="rounded-2xl border border-border bg-card/80 p-6 shadow-card">\n'
            '      <h2 className="font-[--font-display] text-xl font-semibold">Meal Plan Inputs</h2>\n'
            '      <div className="mt-4 space-y-4">\n'
            '        <label className="block text-sm">\n'
            '          <span className="mb-2 block text-muted-foreground">Goal and body profile</span>\n'
            '          <textarea value={query} onChange={(e) => onQueryChange(e.target.value)} className="min-h-28 w-full rounded-xl border border-border bg-background px-3 py-2" placeholder="72kg, fat loss, moderate activity, no shellfish" />\n'
            "        </label>\n"
            '        <label className="block text-sm">\n'
            '          <span className="mb-2 block text-muted-foreground">Cuisine and pantry preferences</span>\n'
            '          <input value={preferences} onChange={(e) => onPreferencesChange(e.target.value)} className="h-11 w-full rounded-xl border border-border bg-background px-3" placeholder="Korean bowls, 20-minute prep, grocery budget friendly" />\n'
            "        </label>\n"
            '        <button type="button" onClick={onGenerate} disabled={loading} className="inline-flex h-11 items-center rounded-xl bg-primary px-5 font-medium text-primary-foreground disabled:opacity-60">{loading ? "Generating…" : "Generate Meal Plan"}</button>\n'
            "      </div>\n"
            "    </section>\n"
            "  );\n"
            "}\n"
        )
    if normalized.endswith("/StatePanel.tsx"):
        return (
            "type Props = { loading: boolean; error: string };\n\n"
            "export default function StatePanel({ loading, error }: Props) {\n"
            '  if (loading) return <div className="rounded-xl border border-border bg-card/70 px-4 py-3 text-sm text-muted-foreground">Generating your meal plan…</div>;\n'
            '  if (error) return <div className="rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</div>;\n'
            "  return null;\n"
            "}\n"
        )
    if normalized.endswith("/InsightPanel.tsx"):
        return (
            "type Meal = { day?: number; slot?: string; title?: string; prep_minutes?: number; calories?: number; protein_g?: number; carbs_g?: number; fats_g?: number; ingredients?: string[] };\n"
            "type Props = { summary: string; items: unknown[]; score: number; insights: { insights?: string[]; next_actions?: string[]; highlights?: string[] } | null };\n\n"
            "export default function InsightPanel({ summary, items, score, insights }: Props) {\n"
            "  return (\n"
            '    <section className="rounded-2xl border border-border bg-card/80 p-6 shadow-card">\n'
            '      <div className="flex items-center justify-between">\n'
            '        <h2 className="font-[--font-display] text-xl font-semibold">Five-Meal Day</h2>\n'
            '        <span className="rounded-full bg-muted px-3 py-1 text-xs text-muted-foreground">Score {score}</span>\n'
            "      </div>\n"
            '      <p className="mt-3 text-sm text-muted-foreground">{summary}</p>\n'
            '      <div className="mt-4 space-y-3">\n'
            '        {items.length === 0 ? <div className="rounded-xl border border-dashed border-border px-4 py-6 text-sm text-muted-foreground">Generate a plan to preview meals.</div> : items.map((raw, idx) => { const item = raw as Meal; return (\n'
            '          <article key={idx} className="rounded-xl border border-border bg-background/60 p-4">\n'
            '            <div className="flex items-center justify-between gap-3">\n'
            '              <h3 className="font-medium">{item.slot ?? `Meal ${idx + 1}`} · {item.title ?? "Meal"}</h3>\n'
            '              <span className="text-xs text-muted-foreground">{item.calories ?? 0} kcal</span>\n'
            "            </div>\n"
            '            <p className="mt-2 text-xs text-muted-foreground">P {item.protein_g ?? 0}g · C {item.carbs_g ?? 0}g · F {item.fats_g ?? 0}g · {item.prep_minutes ?? 0} min</p>\n'
            '            {item.ingredients?.length ? <p className="mt-2 text-sm text-muted-foreground">{item.ingredients.join(", ")}</p> : null}\n'
            "          </article>\n"
            "        ); })}\n"
            "      </div>\n"
            '      {insights?.highlights?.length ? <div className="mt-4 text-sm text-muted-foreground">{insights.highlights.join(" • ")}</div> : null}\n'
            "    </section>\n"
            "  );\n"
            "}\n"
        )
    if normalized.endswith("/CollectionPanel.tsx"):
        return (
            "type Item = { id?: string | number; name?: string; updated_at?: string };\n"
            "type Props = { items: unknown[] };\n\n"
            "export default function CollectionPanel({ items }: Props) {\n"
            "  return (\n"
            '    <section className="rounded-2xl border border-border bg-card/80 p-6 shadow-card">\n'
            '      <h2 className="font-[--font-display] text-xl font-semibold">Starter Profiles</h2>\n'
            '      <div className="mt-4 grid gap-3 md:grid-cols-3">\n'
            "        {items.map((raw, idx) => { const item = raw as Item; return (\n"
            '          <article key={item.id ?? idx} className="rounded-xl border border-border bg-background/60 p-4">\n'
            '            <div className="font-medium">{item.name ?? `Profile ${idx + 1}`}</div>\n'
            '            {item.updated_at ? <div className="mt-1 text-sm text-muted-foreground">{item.updated_at}</div> : null}\n'
            "          </article>\n"
            "        ); })}\n"
            "      </div>\n"
            "    </section>\n"
            "  );\n"
            "}\n"
        )
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
    get_op, primary_post, insights_op = _pick_ops(api_contract)
    get_path = str((get_op or {}).get("path") or "/api/items")
    plan_path = str((primary_post or {}).get("path") or "/api/plan")
    insights_path = str((insights_op or {}).get("path") or "/api/insights")
    return (
        'const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";\n\n'
        "async function request(path: string, init?: RequestInit) {\n"
        "  const res = await fetch(`${API_BASE_URL}${path}`, init);\n"
        "  if (!res.ok) throw new Error(await res.text() || `Request failed: ${res.status}`);\n"
        "  return res.json();\n"
        "}\n\n"
        f'export async function fetchItems() {{ return request("{get_path}"); }}\n\n'
        f'export async function createPlan(payload: {{ query: string; preferences: string }}) {{ return request("{plan_path}", {{ method: "POST", headers: {{ "Content-Type": "application/json" }}, body: JSON.stringify(payload) }}); }}\n\n'
        f'export async function fetchInsights(selection: string, context: string) {{ return request("{insights_path}", {{ method: "POST", headers: {{ "Content-Type": "application/json" }}, body: JSON.stringify({{ selection, context }}) }}); }}\n'
    )


def _route_template(path: str, description: str, api_contract: object) -> str:
    operations = _contract_operations(api_contract)
    lines = [
        "from typing import Any\n",
        "from fastapi import APIRouter, Body\n",
        "from ai_service import build_insight_payload, build_plan_payload, starter_profiles\n\n",
        "router = APIRouter()\n\n",
        '@router.get("/health")\n',
        "async def health() -> dict[str, str]:\n",
        f'    return {{"status": "ok", "detail": "{description}"}}\n\n',
    ]
    for idx, op in enumerate(operations):
        method = str(op["method"]).lower()
        route_path = str(op["path"])
        func_name = f"route_{idx}_{method}"
        if method == "get":
            lines.extend(
                [
                    f'@router.get("{route_path}")\n',
                    f"async def {func_name}() -> dict[str, Any]:\n",
                    '    return {"items": starter_profiles()}\n\n',
                ]
            )
        elif "insight" in route_path:
            lines.extend(
                [
                    f'@router.post("{route_path}")\n',
                    f"async def {func_name}(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:\n",
                    "    return build_insight_payload(str(payload.get('selection', 'meal plan')), str(payload.get('context', '')))\n\n",
                ]
            )
        else:
            lines.extend(
                [
                    f'@router.post("{route_path}")\n',
                    f"async def {func_name}(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:\n",
                    "    return build_plan_payload(str(payload.get('query', 'meal plan')), str(payload.get('preferences', '')))\n\n",
                ]
            )
    return "".join(lines)


def _service_template(path: str, description: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized.endswith("ai_service.py"):
        return (
            "from typing import Any\n\n"
            "def starter_profiles() -> list[dict[str, Any]]:\n"
            "    return [\n"
            '        {"id": "ava", "name": "Ava Chen", "updated_at": "fat-loss · 68kg"},\n'
            '        {"id": "marcus", "name": "Marcus Reed", "updated_at": "muscle-gain · 82kg"},\n'
            '        {"id": "priya", "name": "Priya Nair", "updated_at": "maintenance · 59kg"},\n'
            "    ]\n\n"
            "def build_plan_payload(query: str, preferences: str) -> dict[str, Any]:\n"
            "    seed = (preferences or query or 'meal plan').strip()\n"
            "    meals = [\n"
            '        {"day": 1, "slot": "Breakfast", "title": f"{seed} oats bowl", "prep_minutes": 10, "calories": 520, "protein_g": 38, "carbs_g": 54, "fats_g": 16, "ingredients": ["oats", "greek yogurt", "berries"]},\n'
            '        {"day": 1, "slot": "Lunch", "title": "Chicken rice bowl", "prep_minutes": 20, "calories": 640, "protein_g": 46, "carbs_g": 58, "fats_g": 20, "ingredients": ["chicken breast", "rice", "spinach"]},\n'
            '        {"day": 1, "slot": "Snack", "title": "Protein yogurt cup", "prep_minutes": 5, "calories": 280, "protein_g": 24, "carbs_g": 18, "fats_g": 10, "ingredients": ["greek yogurt", "nuts", "banana"]},\n'
            '        {"day": 1, "slot": "Dinner", "title": "Salmon sweet potato plate", "prep_minutes": 25, "calories": 690, "protein_g": 44, "carbs_g": 48, "fats_g": 28, "ingredients": ["salmon", "sweet potato", "broccoli"]},\n'
            '        {"day": 1, "slot": "Late Snack", "title": "Cottage cheese berries", "prep_minutes": 4, "calories": 240, "protein_g": 22, "carbs_g": 16, "fats_g": 8, "ingredients": ["cottage cheese", "berries"]},\n'
            "    ]\n"
            '    return {"summary": f"Generated a five-meal day for {query or \'your goal\'}", "items": meals, "score": 84}\n\n'
            "def build_insight_payload(selection: str, context: str) -> dict[str, Any]:\n"
            "    return {\n"
            '        "insights": ["Protein is distributed across five meals", "Prep time stays under 25 minutes"],\n'
            '        "next_actions": ["Swap lunch if you need vegetarian options", "Export the grocery list for shopping"],\n'
            '        "highlights": [f"Focus: {selection or \'meal plan\'}", f"Preferences: {context or \'none\'}"],\n'
            "    }\n"
        )
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
        payload = {
            "name": "generated-app",
            "private": True,
            "description": description,
            "scripts": {"dev": "next dev", "build": "next build", "start": "next start", "lint": "next lint"},
            "dependencies": {"next": "15.5.12", "react": "19.0.0", "react-dom": "19.0.0"},
            "devDependencies": {
                "typescript": "5.7.3",
                "tailwindcss": "3.4.17",
                "postcss": "8.4.49",
                "autoprefixer": "10.4.20",
                "@types/react": "19.0.7",
                "@types/node": "20.17.12",
            },
        }
        return json.dumps(payload, indent=2)
    if normalized.endswith("requirements.txt"):
        return "fastapi==0.115.0\nuvicorn[standard]==0.30.0\npydantic==2.9.0\npython-dotenv==1.0.1\n"
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


def _is_page_file(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return "page.tsx" in normalized or "page.ts" in normalized


def _extract_props_signature(content: str, component_name: str) -> str:
    pattern = re.compile(
        rf"(?:type|interface)\s+{re.escape(component_name)}Props\s*(?:=\s*\{{([^}}]{{1,400}})\}}|\{{([^}}]{{1,400}})\}})",
        re.DOTALL,
    )
    match = pattern.search(content)
    if match:
        body = (match.group(1) or match.group(2) or "").strip()
        props = []
        for line in body.splitlines():
            line = line.strip().rstrip(";,")
            if line and ":" in line and not line.startswith("//"):
                props.append(line)
        if props:
            return "{ " + "; ".join(props[:6]) + " }"
    return ""


def _extract_component_exports(code: dict[str, str]) -> dict[str, dict[str, list[str] | dict[str, str]]]:
    exports_by_file: dict[str, dict] = {}
    default_pattern = re.compile(r"export\s+default\s+(?:function|class|const)?\s*(\w+)")
    named_pattern = re.compile(r"export\s+(?:function|class|const|type|interface|enum)\s+(\w+)")
    reexport_pattern = re.compile(r"export\s+\{([^}]+)\}")
    for path, content in code.items():
        if not path.endswith((".tsx", ".ts", ".js", ".jsx")):
            continue
        default_exports: list[str] = []
        named_exports: list[str] = []
        props_signatures: dict[str, str] = {}
        for match in default_pattern.finditer(content):
            if match.group(1):
                default_exports.append(match.group(1))
        for match in named_pattern.finditer(content):
            named_exports.append(match.group(1))
        for match in reexport_pattern.finditer(content):
            for item in match.group(1).split(","):
                stripped = item.split(" as ")[0].strip()
                if stripped:
                    named_exports.append(stripped)
        for name in default_exports + named_exports:
            sig = _extract_props_signature(content, name)
            if sig:
                props_signatures[name] = sig
        if default_exports or named_exports:
            exports_by_file[path] = {
                "default": default_exports,
                "named": named_exports,
                "props": props_signatures,
            }
    return exports_by_file


def _should_preserve_existing_file(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    return normalized in {
        "src/app/layout.tsx",
        "src/app/globals.css",
        "package.json",
        "tsconfig.json",
        "next.config.js",
        "next.config.ts",
        "postcss.config.js",
        "next-env.d.ts",
        "src/types/api.d.ts",
        "src/lib/api-client.ts",
        "main.py",
        "models.py",
        "requirements.txt",
        "schemas.py",
    }


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
