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
_FONT_DEFAULT_WEIGHTS = {
    "Merriweather": ["400", "700"],
    "Playfair_Display": ["400", "700"],
    "Libre_Baskerville": ["400", "700"],
    "Cormorant_Garamond": ["400", "700"],
    "Crimson_Text": ["400", "700"],
    "Lora": ["400", "700"],
    "DM_Serif_Display": ["400"],
    "Baskervville": ["400"],
    "Alegreya": ["400", "700"],
    "Roboto_Slab": ["400", "700"],
}
_BASE_FRONTEND_DEPENDENCIES = {
    "next": "15.5.12",
    "react": "19.0.0",
    "react-dom": "19.0.0",
    "typescript": "5.7.3",
    "tailwindcss": "3.4.17",
    "postcss": "8.4.49",
    "autoprefixer": "10.4.20",
    "@types/react": "19.0.7",
    "@types/node": "20.17.12",
}
_OPTIONAL_FRONTEND_DEPENDENCIES = {
    "@heroicons/react": "2.2.0",
    "chart.js": "4.5.1",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "date-fns": "4.1.0",
    "framer-motion": "^12.34.5",
    "lucide-react": "^0.576.0",
    "qrcode.react": "4.2.0",
    "react-hook-form": "7.71.2",
    "react-markdown": "^10.1.0",
    "react-chartjs-2": "5.3.1",
    "react-syntax-highlighter": "^16.1.1",
    "recharts": "^3.7.0",
    "sonner": "2.0.7",
    "tailwind-merge": "^3.5.0",
    "zod": "4.3.6",
}
_BUILTIN_FRONTEND_PACKAGES = {"next", "react", "react-dom"}
_LEGACY_HEROICON_RENAMES = {
    "CloudUploadIcon": "ArrowUpTrayIcon",
    "CloudDownloadIcon": "ArrowDownTrayIcon",
    "DownloadIcon": "ArrowDownTrayIcon",
    "UploadIcon": "ArrowUpTrayIcon",
    "XIcon": "XMarkIcon",
    "SearchIcon": "MagnifyingGlassIcon",
    "RefreshIcon": "ArrowPathIcon",
    "MenuIcon": "Bars3Icon",
    "SelectorIcon": "ChevronUpDownIcon",
    "LocationMarkerIcon": "MapPinIcon",
    "ExternalLinkIcon": "ArrowTopRightOnSquareIcon",
    "DuplicateIcon": "Square2StackIcon",
    "DotsHorizontalIcon": "EllipsisHorizontalIcon",
    "DotsVerticalIcon": "EllipsisVerticalIcon",
    "TrendingUpIcon": "ArrowTrendingUpIcon",
    "TrendingDownIcon": "ArrowTrendingDownIcon",
}
_REACT_IMPORTABLE_SYMBOLS = {
    "useState",
    "useEffect",
    "useMemo",
    "useCallback",
    "useRef",
    "useReducer",
    "useTransition",
    "useDeferredValue",
    "startTransition",
}
_UI_PRIMITIVE_TEMPLATES = {
    "button": """"use client";

import * as React from "react";

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "default" | "outline" | "ghost";
  size?: "sm" | "md" | "lg";
};

const VARIANT_CLASSES: Record<NonNullable<ButtonProps["variant"]>, string> = {
  default: "bg-primary text-white hover:opacity-90",
  outline: "border border-border text-foreground hover:bg-muted",
  ghost: "text-foreground hover:bg-muted/70",
};

const SIZE_CLASSES: Record<NonNullable<ButtonProps["size"]>, string> = {
  sm: "h-9 px-3 text-sm",
  md: "h-11 px-4 text-sm",
  lg: "h-12 px-5 text-base",
};

export function Button({
  className = "",
  variant = "default",
  size = "md",
  type = "button",
  ...props
}: ButtonProps) {
  const classes = [
    "inline-flex items-center justify-center rounded-md font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:cursor-not-allowed disabled:opacity-50",
    VARIANT_CLASSES[variant],
    SIZE_CLASSES[size],
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return <button type={type} className={classes} {...props} />;
}

export default Button;
""",
    "card": """import * as React from "react";

type DivProps = React.HTMLAttributes<HTMLDivElement>;

export function Card({ className = "", ...props }: DivProps) {
  return <div className={["rounded-xl border border-border bg-card shadow-card", className].filter(Boolean).join(" ")} {...props} />;
}

export function CardHeader({ className = "", ...props }: DivProps) {
  return <div className={["p-6 pb-3", className].filter(Boolean).join(" ")} {...props} />;
}

export function CardTitle({ className = "", ...props }: DivProps) {
  return <div className={["text-lg font-semibold text-foreground", className].filter(Boolean).join(" ")} {...props} />;
}

export function CardDescription({ className = "", ...props }: DivProps) {
  return <div className={["text-sm text-muted", className].filter(Boolean).join(" ")} {...props} />;
}

export function CardContent({ className = "", ...props }: DivProps) {
  return <div className={["p-6 pt-0", className].filter(Boolean).join(" ")} {...props} />;
}

export function CardFooter({ className = "", ...props }: DivProps) {
  return <div className={["p-6 pt-0", className].filter(Boolean).join(" ")} {...props} />;
}
""",
    "input": """"use client";

import * as React from "react";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

export const Input = React.forwardRef<HTMLInputElement, InputProps>(function Input({ className = "", ...props }, ref) {
  return (
    <input
      ref={ref}
      className={["h-11 w-full rounded-md border border-border bg-card px-3 text-sm text-foreground outline-none transition focus:ring-2 focus:ring-primary/40", className].filter(Boolean).join(" ")}
      {...props}
    />
  );
});

export default Input;
""",
    "textarea": """"use client";

import * as React from "react";

export type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>;

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea({ className = "", ...props }, ref) {
  return (
    <textarea
      ref={ref}
      className={["min-h-28 w-full rounded-md border border-border bg-card px-3 py-2 text-sm text-foreground outline-none transition focus:ring-2 focus:ring-primary/40", className].filter(Boolean).join(" ")}
      {...props}
    />
  );
});

export default Textarea;
""",
    "badge": """import * as React from "react";

type BadgeProps = React.HTMLAttributes<HTMLSpanElement>;

export function Badge({ className = "", ...props }: BadgeProps) {
  return <span className={["inline-flex items-center rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-foreground", className].filter(Boolean).join(" ")} {...props} />;
}

export default Badge;
""",
}


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
        max_tokens=12000,
    )
    backend_llm = get_llm(
        model=backend_model,
        temperature=0.3,
        max_tokens=10000,
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
    frontend_code, backend_code = _normalize_cross_stack(frontend_code, backend_code)

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
        frontend_code, backend_code = _normalize_cross_stack(frontend_code, backend_code)

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
                "content": (
                    "Generate frontend files from this product context.\n\n"
                    "### Product Context\n"
                    f"{context}\n\n"
                    "### Execution Notes\n"
                    "- Convert the PRD, tech spec, and blueprint into a visually distinctive product, not a generic dashboard.\n"
                    "- Treat any design_direction, visual_style_hints, ux_highlights, demo_story, and blueprint experience_contract as hard requirements.\n"
                    "- The generated src/app/page.tsx must compose multiple domain components from the blueprint manifest, not only a hero form.\n"
                    "- Build the first-run experience for judges seeing the app for the first time in a live demo.\n"
                ),
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
                    "AI features must be integral to business endpoints.\n\n"
                    "### Product Context\n"
                    f"{context}\n\n"
                    "### Execution Notes\n"
                    "- Preserve the frontend/backend contract exactly for endpoint paths and request field names.\n"
                    "- Preserve the frontend/backend contract for response field names too, so the frontend can safely render returned data.\n"
                    "- Keep routes robust behind DigitalOcean ingress by avoiding APIRouter(prefix='/api').\n"
                ),
            },
        ],
        fallback_models=fallback_models,
    )

    parsed = _parse_json_response(response.content, {"files": {}}, label="backend")
    files = parsed.get("files", {})
    return _normalize_backend_files(_normalize_files_dict(files))


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
        normalized = _normalize_frontend_client_directive_syntax(normalized)
        normalized = _normalize_frontend_use_client_directives(normalized)
        normalized = _normalize_frontend_layout_metadata_boundaries(normalized)
        normalized = _normalize_frontend_react_hook_imports(normalized)
        normalized = _normalize_frontend_state_types(normalized)
        normalized = _normalize_frontend_next_font_weights(normalized)
        normalized = _normalize_frontend_heroicons_imports(normalized)
        normalized = _normalize_frontend_api_base_env(normalized)
        normalized = _normalize_frontend_error_parsing(normalized)
        normalized = _normalize_frontend_api_overloads(normalized)
        normalized = _normalize_frontend_partial_ai_requests(normalized)
        normalized = _normalize_frontend_component_exports(normalized)
        normalized = _normalize_frontend_ui_primitives(normalized)
        normalized.setdefault(
            "next-env.d.ts",
            '/// <reference types="next" />\n/// <reference types="next/image-types/global" />\n\n// This file is auto-generated by Next.js.\n',
        )

        normalized["tsconfig.json"] = _normalize_next_tsconfig(normalized.get("tsconfig.json", ""))
        normalized["next.config.js"] = _normalize_next_config(normalized.get("next.config.js", ""))
        normalized["tailwind.config.ts"] = _normalize_tailwind_config(normalized.get("tailwind.config.ts", ""))
        normalized["postcss.config.js"] = _normalize_postcss_config(normalized.get("postcss.config.js", ""))
        normalized["package.json"] = _normalize_frontend_package_json(normalized)

    return normalized


def _normalize_backend_files(files: dict[str, str]) -> dict[str, str]:
    normalized = dict(files)
    normalized = _normalize_backend_api_routes(normalized)
    normalized = _normalize_backend_database_url_guards(normalized)
    normalized = _normalize_backend_auth_scheme_references(normalized)
    normalized = _normalize_backend_ai_fallbacks(normalized)
    normalized = _normalize_backend_async_ai_calls(normalized)
    if normalized:
        normalized.setdefault(".python-version", "3.13\n")
    return normalized


def _normalize_cross_stack(frontend_files: dict[str, str], backend_files: dict[str, str]) -> tuple[dict[str, str], dict[str, str]]:
    normalized_backend = _normalize_backend_files(backend_files)
    normalized_frontend = _normalize_frontend_request_payloads(frontend_files, normalized_backend)
    return normalized_frontend, normalized_backend


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


def _normalize_frontend_request_payloads(
    frontend_files: dict[str, str],
    backend_files: dict[str, str],
) -> dict[str, str]:
    routes_source = backend_files.get("routes.py", "")
    endpoint_fields = _extract_backend_request_fields(routes_source)
    if not endpoint_fields:
        return frontend_files

    normalized: dict[str, str] = {}
    for path, content in frontend_files.items():
        updated = content
        if path.endswith((".ts", ".tsx", ".js", ".jsx")):
            for endpoint, fields in endpoint_fields.items():
                if len(fields) != 1:
                    continue
                field = fields[0]
                updated = re.sub(
                    rf"({re.escape(endpoint)}[\s\S]*?JSON\.stringify\(\{{\s*)(\w+)(\s*\}}\))",
                    lambda match: (
                        match.group(0)
                        if match.group(2) == field
                        else f"{match.group(1)}{field}: {match.group(2)}{match.group(3)}"
                    ),
                    updated,
                    count=1,
                )
        normalized[path] = updated
    return normalized


def _normalize_backend_auth_scheme_references(files: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}

    for path, content in files.items():
        updated = content
        if path.endswith(".py") and "OAuth2PasswordBearer" in content and "Depends(" in content:
            scheme_names = re.findall(r"^([A-Za-z_][\w]*)\s*=\s*OAuth2PasswordBearer\(", updated, flags=re.MULTILINE)
            if len(scheme_names) == 1:
                scheme_name = scheme_names[0]
                if scheme_name != "auth_scheme" and "Depends(auth_scheme)" in updated:
                    updated = updated.replace("Depends(auth_scheme)", f"Depends({scheme_name})")
                if scheme_name != "oauth_scheme" and "Depends(oauth_scheme)" in updated:
                    updated = updated.replace("Depends(oauth_scheme)", f"Depends({scheme_name})")
        normalized[path] = updated

    return normalized


def _normalize_backend_database_url_guards(files: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    ssl_guard_pattern = re.compile(
        r'if\s+not\s+_raw_url\.startswith\("sqlite"\)\s+and\s+"localhost"\s+not\s+in\s+_raw_url\s+and\s+"127\.0\.0\.1"\s+not\s+in\s+_raw_url\s*:',
        flags=re.MULTILINE,
    )
    replacement = (
        "if (\n"
        '    not _raw_url.startswith("sqlite")\n'
        '    and "localhost" not in _raw_url\n'
        '    and "127.0.0.1" not in _raw_url\n'
        '    and "sslmode=" not in _raw_url.lower()\n'
        "):"
    )

    for path, content in files.items():
        updated = content
        if path.endswith(".py") and "_raw_url" in content and "sslmode=require" in content:
            updated = ssl_guard_pattern.sub(replacement, updated)
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


def _normalize_frontend_client_directive_syntax(files: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for path, content in files.items():
        updated = content
        if path.endswith((".ts", ".tsx", ".js", ".jsx")):
            updated = _canonicalize_use_client_directive(updated)
        normalized[path] = updated
    return normalized


def _canonicalize_use_client_directive(content: str) -> str:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if "use client" not in stripped:
            return content
        normalized = stripped.rstrip(";")
        normalized = normalized.replace('"', "").replace("'", "").strip()
        if normalized != "use client":
            return content
        lines[index] = '"use client";'
        updated = "\n".join(lines)
        if content.endswith("\n"):
            updated += "\n"
        return updated
    return content


def _normalize_frontend_layout_metadata_boundaries(files: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    layout_suffixes = ("src/app/layout.tsx", "src/app/layout.jsx", "app/layout.tsx", "app/layout.jsx")

    for path, content in files.items():
        updated = content
        if path.endswith(layout_suffixes) and (
            "export const metadata" in content or "generateMetadata" in content
        ):
            updated = re.sub(r'^\s*"use client";\n+', "", updated, count=1)
        normalized[path] = updated

    return normalized


def _normalize_frontend_react_hook_imports(files: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for path, content in files.items():
        updated = content
        if path.endswith((".ts", ".tsx", ".js", ".jsx")):
            used_symbols = sorted(symbol for symbol in _REACT_IMPORTABLE_SYMBOLS if re.search(rf"\b{symbol}\b", updated))
            if used_symbols:
                match = re.search(r'import\s+\{(?P<named>[^}]+)\}\s+from\s+[\'"]react[\'"]\s*;?', updated)
                if match:
                    existing = {part.strip() for part in match.group("named").split(",") if part.strip()}
                    merged = ", ".join(sorted(existing | set(used_symbols)))
                    updated = f"{updated[:match.start()]}import {{ {merged} }} from \"react\";{updated[match.end():]}"
                elif 'from "react"' not in updated and "from 'react'" not in updated:
                    updated = f'import {{ {", ".join(used_symbols)} }} from "react";\n{updated}'
        normalized[path] = updated
    return normalized


def _normalize_frontend_heroicons_imports(files: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    import_pattern = re.compile(
        r"import\s+\{(?P<body>[^}]+)\}\s+from\s+['\"]@heroicons/react/24/(?P<variant>solid|outline)['\"]\s*;?"
    )

    for path, content in files.items():
        updated = content
        if path.endswith((".ts", ".tsx", ".js", ".jsx")) and "@heroicons/react/24/" in content:

            def repl(match: re.Match[str]) -> str:
                items = [item.strip() for item in match.group("body").split(",") if item.strip()]
                renamed_items: list[str] = []
                for item in items:
                    normalized_item = _LEGACY_HEROICON_RENAMES.get(item, item)
                    if normalized_item not in renamed_items:
                        renamed_items.append(normalized_item)
                return (
                    f"import {{ {', '.join(renamed_items)} }} "
                    f"from '@heroicons/react/24/{match.group('variant')}';"
                )

            updated = import_pattern.sub(repl, updated)
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


def _normalize_frontend_next_font_weights(files: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}

    for path, content in files.items():
        updated = content
        if path.endswith((".ts", ".tsx")) and "next/font/google" in content:
            imported_fonts = re.findall(
                r"import\s+\{\s*([A-Za-z0-9_]+)\s*\}\s+from\s+['\"]next/font/google['\"]",
                content,
            )
            for font_name in imported_fonts:
                default_weights = _FONT_DEFAULT_WEIGHTS.get(font_name)
                if not default_weights:
                    continue

                pattern = re.compile(rf"{font_name}\(\{{(?P<body>[\s\S]*?)\}}\)")

                def repl(match: re.Match[str]) -> str:
                    body = match.group("body")
                    if "weight" in body:
                        return match.group(0)
                    weight_values = ", ".join(f"'{weight}'" for weight in default_weights)
                    stripped = body.strip()
                    body_suffix = f", {stripped}" if stripped else ""
                    return f"{font_name}({{ weight: [{weight_values}]{body_suffix} }})"

                updated = pattern.sub(repl, updated)
        normalized[path] = updated

    return normalized


def _normalize_frontend_api_base_env(files: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}

    for path, content in files.items():
        updated = content
        if path.endswith((".ts", ".tsx", ".js", ".jsx")) and "NEXT_PUBLIC_API_URL" in content:
            updated = re.sub(
                r"(?<!\()process\.env\.NEXT_PUBLIC_API_URL(?!\s*(?:\|\||\?\?))",
                '(process.env.NEXT_PUBLIC_API_URL || "")',
                updated,
            )
        normalized[path] = updated

    return normalized


def _normalize_frontend_error_parsing(files: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for path, content in files.items():
        updated = content
        if path.endswith("api.ts"):
            pattern = re.compile(
                r"if \(!res\.ok\) \{\s*const err = await res\.json\(\);\s*throw new Error\(([^)]+)\);\s*\}",
                flags=re.DOTALL,
            )

            def repl(match: re.Match[str]) -> str:
                expr = match.group(1)
                literals = re.findall(r'["\']([^"\']+)["\']', expr)
                fallback = literals[-1] if literals else "Request failed"
                return f'if (!res.ok) {{\n    await throwApiError(res, {json.dumps(fallback)});\n  }}'

            updated, replacements = pattern.subn(repl, updated)
            if replacements and "async function throwApiError" not in updated:
                helper = (
                    "async function throwApiError(res: Response, fallback: string): Promise<never> {\n"
                    "  const raw = await res.text();\n"
                    "  const parsed = raw ? safeParseJson(raw) : null;\n"
                    "  const message = parsed?.error?.message ?? parsed?.detail ?? parsed?.message ?? raw ?? fallback;\n"
                    "  throw new Error(message || fallback);\n"
                    "}\n\n"
                    "function safeParseJson(raw: string): any {\n"
                    "  try {\n"
                    "    return JSON.parse(raw);\n"
                    "  } catch {\n"
                    "    return null;\n"
                    "  }\n"
                    "}\n\n"
                )
                import_block = re.match(r"((?:import[^\n]*\n)+)", updated)
                if import_block:
                    updated = f"{import_block.group(1)}\n{helper}{updated[import_block.end():]}"
                else:
                    updated = f"{helper}{updated}"
        normalized[path] = updated
    return normalized


def _normalize_frontend_partial_ai_requests(files: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    pattern = re.compile(
        r"const \[(?P<summary_var>\w+),\s*(?P<tags_var>\w+)\] = await Promise\.all\(\[\s*"
        r"summarize\((?P<arg>[^)]+)\),\s*generateTags\((?P=arg)\)\s*"
        r"\]\);\s*setSummary\((?P=summary_var)\);\s*setTags\((?P=tags_var)\);",
        flags=re.DOTALL,
    )

    for path, content in files.items():
        updated = content
        if path.endswith(".tsx") and "summarize(" in content and "generateTags(" in content and "Promise.all([" in content:
            updated = pattern.sub(
                lambda match: (
                    f'const [summaryResult, tagsResult] = await Promise.allSettled([\n'
                    f'        summarize({match.group("arg")}),\n'
                    f'        generateTags({match.group("arg")}),\n'
                    "      ]);\n"
                    '      if (summaryResult.status === "fulfilled") {\n'
                    "        setSummary(summaryResult.value);\n"
                    "      } else {\n"
                    '        throw new Error(summaryResult.reason?.message ?? "Summarization failed");\n'
                    "      }\n"
                    '      if (tagsResult.status === "fulfilled") {\n'
                    "        setTags(tagsResult.value);\n"
                    "      } else {\n"
                    '        setError(tagsResult.reason?.message ?? "Tag generation failed, but the summary is available.");\n'
                    "        setTags([]);\n"
                    "      }"
                ),
                updated,
            )
        normalized[path] = updated
    return normalized


def _normalize_frontend_api_overloads(files: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    pattern = re.compile(
        r"export async function (?P<name>\w+)\(\s*(?P<params>[\s\S]*?)\)\s*:\s*Promise<(?P<returns>[^>]+)>\s*\{",
        flags=re.MULTILINE,
    )

    for path, content in files.items():
        updated = content
        if path.endswith("api.ts"):
            def repl(match: re.Match[str]) -> str:
                name = match.group("name")
                params = match.group("params")
                returns = [item.strip() for item in match.group("returns").split("|") if item.strip()]
                if "body?:" not in params or len(returns) != 2:
                    return match.group(0)
                if f"export async function {name}(" in updated[: match.start()] and f"{name}(" in updated[: match.start()]:
                    return match.group(0)

                body_match = re.search(r",?\s*body\?\s*:\s*(?P<body_type>[^,\n)]+)", params)
                if not body_match:
                    return match.group(0)

                body_type = body_match.group("body_type").strip()
                required_params = re.sub(r",?\s*body\?\s*:\s*[^,\n)]+", "", params).strip().rstrip(",")
                if not required_params:
                    return match.group(0)

                overloads = (
                    f"export async function {name}({required_params}, body: {body_type}): Promise<{returns[0]}>;\n"
                    f"export async function {name}({required_params}): Promise<{returns[1]}>;\n"
                )
                return overloads + match.group(0)

            updated = pattern.sub(repl, updated)
        normalized[path] = updated
    return normalized


def _normalize_frontend_ui_primitives(files: dict[str, str]) -> dict[str, str]:
    normalized = dict(files)
    for path, content in list(files.items()):
        if not path.endswith((".ts", ".tsx", ".js", ".jsx")):
            continue
        for primitive, template in _UI_PRIMITIVE_TEMPLATES.items():
            import_path = f"@/components/ui/{primitive}"
            target_path = f"src/components/ui/{primitive}.tsx"
            if import_path in content and target_path not in normalized:
                normalized[target_path] = template
    return normalized


def _normalize_frontend_package_json(files: dict[str, str]) -> str:
    raw = files.get("package.json", "")
    try:
        parsed = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        parsed = {}

    if not isinstance(parsed, dict):
        parsed = {}

    dependencies = parsed.get("dependencies", {})
    if not isinstance(dependencies, dict):
        dependencies = {}

    for package_name, version in _BASE_FRONTEND_DEPENDENCIES.items():
        dependencies[package_name] = version

    detected_optional_dependencies = _detect_frontend_external_dependencies(files)
    for package_name, version in _OPTIONAL_FRONTEND_DEPENDENCIES.items():
        if package_name in detected_optional_dependencies or package_name in dependencies:
            dependencies[package_name] = version

    scripts = parsed.get("scripts", {})
    if not isinstance(scripts, dict):
        scripts = {}
    normalized_scripts = {
        "dev": "next dev",
        "build": "next build",
        "start": "next start",
        "lint": "next lint",
        **scripts,
    }

    parsed["name"] = parsed.get("name") or "generated-app"
    parsed["version"] = parsed.get("version") or "0.1.0"
    parsed["private"] = True
    parsed["scripts"] = normalized_scripts
    parsed["dependencies"] = dependencies
    parsed["engines"] = {"node": "22.x"}

    return json.dumps(parsed, indent=2)


def _detect_frontend_external_dependencies(files: dict[str, str]) -> set[str]:
    detected: set[str] = set()
    import_pattern = re.compile(
        r"""(?:from\s+['"](?P<from>[^'"]+)['"]|import\s+['"](?P<bare>[^'"]+)['"]|import\s*\(\s*['"](?P<dynamic>[^'"]+)['"]\s*\)|require\(\s*['"](?P<require>[^'"]+)['"]\s*\))"""
    )

    for path, content in files.items():
        if not path.endswith((".ts", ".tsx", ".js", ".jsx")):
            continue
        for match in import_pattern.finditer(content):
            module_name = (
                match.group("from")
                or match.group("bare")
                or match.group("dynamic")
                or match.group("require")
                or ""
            )
            package_name = _extract_npm_package_name(module_name)
            if not package_name or package_name in _BUILTIN_FRONTEND_PACKAGES:
                continue
            if package_name in _OPTIONAL_FRONTEND_DEPENDENCIES:
                detected.add(package_name)

    return detected


def _extract_npm_package_name(module_name: str) -> str | None:
    if not module_name or module_name.startswith((".", "/", "@/")):
        return None
    if module_name.startswith("next/"):
        return "next"
    if module_name.startswith("react-dom/"):
        return "react-dom"
    if module_name.startswith("@"):
        parts = module_name.split("/")
        return "/".join(parts[:2]) if len(parts) >= 2 else module_name
    return module_name.split("/", 1)[0]


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


def _normalize_backend_api_routes(files: dict[str, str]) -> dict[str, str]:
    normalized = dict(files)

    routes_content = normalized.get("routes.py", "")
    if routes_content:
        normalized["routes.py"] = _strip_api_prefix_from_router(routes_content)

    main_content = normalized.get("main.py", "")
    if main_content:
        normalized["main.py"] = _inject_optional_api_prefix_middleware(main_content)

    return normalized


def _strip_api_prefix_from_router(content: str) -> str:
    match = re.search(r"APIRouter\(([^)]*)\)", content)
    if not match or "prefix" not in match.group(1):
        return content

    args = re.sub(r"\s*prefix\s*=\s*['\"]/api['\"]\s*,?", "", match.group(1))
    args = re.sub(r"^\s*,\s*", "", args)
    args = re.sub(r",\s*,", ", ", args).strip().strip(",")
    replacement = f"APIRouter({args})" if args else "APIRouter()"
    return f"{content[:match.start()]}{replacement}{content[match.end():]}"


def _inject_optional_api_prefix_middleware(content: str) -> str:
    if '@app.middleware("http")' in content or "@app.middleware('http')" in content:
        return content

    updated = content
    if "from fastapi import FastAPI, Request" not in updated:
        updated = updated.replace("from fastapi import FastAPI", "from fastapi import FastAPI, Request")

    middleware = (
        '\n@app.middleware("http")\n'
        "async def normalize_api_prefix(request: Request, call_next):\n"
        '    if request.scope.get("path", "").startswith("/api/"):\n'
        '        request.scope["path"] = request.scope["path"][4:] or "/"\n'
        "    return await call_next(request)\n"
    )

    marker = "app.include_router(router)"
    if marker in updated:
        return updated.replace(marker, f"{middleware}\n{marker}", 1)
    return updated


def _normalize_backend_ai_fallbacks(files: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for path, content in files.items():
        updated = content
        if path.endswith("ai_service.py"):
            updated = updated.replace(
                'return {"note": "Failed to parse JSON from AI response", "raw": raw_json}',
                "return _coerce_unstructured_payload(raw_json)",
            )
            updated = updated.replace(
                "return {'note': 'Failed to parse JSON from AI response', 'raw': raw_json}",
                "return _coerce_unstructured_payload(raw_json)",
            )

            if "_coerce_unstructured_payload" not in updated:
                helper = (
                    "def _coerce_unstructured_payload(raw_text: str) -> Dict[str, Any]:\n"
                    "    compact = raw_text.strip()\n"
                    "    tags = [part.strip(\" -•\\t\") for part in re.split(r\",|\\\\n\", compact) if part.strip(\" -•\\t\")]\n"
                    "    return {\n"
                    '        "note": "Model returned plain text instead of JSON",\n'
                    '        "raw": compact,\n'
                    '        "text": compact,\n'
                    '        "summary": compact,\n'
                    '        "tags": tags[:6],\n'
                    "    }\n"
                )
                marker = "async def _call_inference"
                if marker in updated:
                    updated = updated.replace(marker, f"{helper}\n\n{marker}", 1)
                else:
                    updated = f"{helper}\n\n{updated}"
        normalized[path] = updated
    return normalized


def _normalize_backend_async_ai_calls(files: dict[str, str]) -> dict[str, str]:
    normalized = dict(files)
    ai_service = normalized.get("ai_service.py", "")
    async_helpers = set(re.findall(r"async def (\w+)\(", ai_service))
    if not async_helpers:
        return normalized

    for path, content in list(normalized.items()):
        if not path.endswith(".py") or path == "ai_service.py":
            continue

        updated = content
        for helper in async_helpers:
            updated = re.sub(rf"(?<!await\s)(=\s*){helper}\(", rf"\1await {helper}(", updated)
            updated = re.sub(rf"(?<!await\s)(return\s+){helper}\(", rf"\1await {helper}(", updated)

        function_pattern = re.compile(
            r"(?P<header>^def\s+\w+\([^)]*\):\n)(?P<body>(?:^[ \t]+.*\n?)*)",
            flags=re.MULTILINE,
        )

        def repl(match: re.Match[str]) -> str:
            header = match.group("header")
            body = match.group("body")
            block = f"{header}{body}"
            if "await " not in block:
                return block
            return block.replace("def ", "async def ", 1)

        updated = function_pattern.sub(repl, updated)
        normalized[path] = updated

    return normalized


def _extract_backend_request_fields(routes_source: str) -> dict[str, list[str]]:
    model_fields: dict[str, list[str]] = {}

    for class_name, body in re.findall(r"class\s+(\w+)\(BaseModel\):\n((?:\s+.+\n)+)", routes_source):
        fields = re.findall(r"^\s+(\w+)\s*:", body, flags=re.MULTILINE)
        if fields:
            model_fields[class_name] = fields

    endpoint_fields: dict[str, list[str]] = {}
    for endpoint, _param_name, model_name in re.findall(
        r'@router\.(?:post|put|patch)\("([^"]+)"\)\nasync def \w+\((\w+):\s*(\w+)',
        routes_source,
    ):
        fields = model_fields.get(model_name)
        if fields:
            endpoint_fields[endpoint] = fields

    return endpoint_fields


def _normalize_tailwind_config(raw: str) -> str:
    if (
        "./src/**/*.{js,ts,jsx,tsx,mdx}" in raw
        and "card:" in raw
        and "muted:" in raw
        and "primary:" in raw
        and "borderRadius" in raw
    ):
        return raw

    return (
        "import type { Config } from 'tailwindcss';\n\n"
        "const config: Config = {\n"
        "  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],\n"
        "  theme: {\n"
        "    extend: {\n"
        "      colors: {\n"
        "        background: 'var(--background)',\n"
        "        foreground: 'var(--foreground)',\n"
        "        card: 'var(--card)',\n"
        "        muted: 'var(--muted)',\n"
        "        border: 'var(--border)',\n"
        "        primary: 'var(--primary)',\n"
        "        accent: 'var(--accent)',\n"
        "        success: 'var(--success)',\n"
        "        warning: 'var(--warning)',\n"
        "      },\n"
        "      borderRadius: {\n"
        "        DEFAULT: 'var(--radius)',\n"
        "        lg: 'calc(var(--radius) + 0.25rem)',\n"
        "        xl: 'calc(var(--radius) + 0.5rem)',\n"
        "      },\n"
        "      boxShadow: {\n"
        "        card: 'var(--shadow)',\n"
        "      },\n"
        "    },\n"
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
    if cleaned.lower().startswith("json\n"):
        cleaned = cleaned[5:]

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

    balanced_json = _extract_balanced_json_block(cleaned)
    if balanced_json:
        try:
            return json.loads(balanced_json)
        except json.JSONDecodeError:
            logger.warning(
                "[CODE_GEN] %s: Balanced JSON extraction also failed",
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


def _extract_balanced_json_block(raw: str) -> str | None:
    for start_index, char in enumerate(raw):
        if char not in "{[":
            continue

        stack = ["}" if char == "{" else "]"]
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

            if current in "{[":
                stack.append("}" if current == "{" else "]")
                continue

            if current in "}]":
                if not stack or current != stack[-1]:
                    break
                stack.pop()
                if not stack:
                    return raw[start_index : index + 1]

    return None
