import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class FileSpec(BaseModel):
    path: str
    file_type: Literal["page", "component", "api", "route", "service", "config", "style"]
    description: str
    dependencies: list[str] = Field(default_factory=list)


def extract_file_specs(blueprint: dict) -> list[FileSpec]:
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

            file_type = _infer_file_type(path)
            file_specs.append(
                FileSpec(
                    path=str(path),
                    file_type=file_type,
                    description=description,
                    dependencies=dependencies,
                )
            )

    return file_specs


def generate_single_file(spec: FileSpec, context: dict) -> dict[str, str]:
    api_contract = context.get("api_contract")
    design_system = context.get("design_system")
    already_generated = context.get("already_generated")

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

    if isinstance(already_generated, dict):
        _ = len(already_generated)

    return {spec.path: content}


def per_file_code_generator_node(state: dict) -> dict:
    if not os.getenv("VIBEDEPLOY_USE_PER_FILE_CODEGEN", "").strip():
        return {}

    blueprint = state.get("blueprint") if isinstance(state, dict) else {}
    specs = extract_file_specs(blueprint if isinstance(blueprint, dict) else {})

    frontend_manifest = (blueprint or {}).get("frontend_files") if isinstance(blueprint, dict) else {}
    backend_manifest = (blueprint or {}).get("backend_files") if isinstance(blueprint, dict) else {}
    frontend_paths = set(frontend_manifest.keys()) if isinstance(frontend_manifest, dict) else set()
    backend_paths = set(backend_manifest.keys()) if isinstance(backend_manifest, dict) else set()

    frontend_code = dict(state.get("frontend_code") or {})
    backend_code = dict(state.get("backend_code") or {})

    context = {
        "api_contract": state.get("api_contract"),
        "design_system": (blueprint or {}).get("design_system", {}) if isinstance(blueprint, dict) else {},
        "already_generated": {},
    }

    for spec in specs:
        generated = generate_single_file(spec, context)
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
