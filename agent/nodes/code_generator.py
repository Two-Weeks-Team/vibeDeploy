import asyncio
import json
import logging
import os
import re
from html import escape as html_escape

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
_CODEGEN_MODEL_MAX_ATTEMPTS = 8
_STRICT_PRIMARY_CODEGEN_MAX_ATTEMPTS = 6
_STACK_GENERATION_PAUSE_SECONDS = 2
_FALLBACK_FRONTEND_MARKER_FILE = ".vibedeploy-fallback-frontend.json"
_FALLBACK_BACKEND_MARKER_FILE = ".vibedeploy-fallback-backend.json"
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
_STRUCTURED_CODE_FILE_SUFFIXES = (
    ".tsx",
    ".ts",
    ".jsx",
    ".js",
    ".mjs",
    ".cjs",
    ".py",
    ".css",
    ".scss",
    ".md",
    ".html",
)
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
    prompt_strategy = state.get("prompt_strategy", {}) or {}
    code_eval_result = state.get("code_eval_result")
    execution_tasks = state.get("execution_tasks") or []
    repair_tasks = state.get("repair_tasks") or []
    task_contracts = state.get("task_contracts") or {}
    existing_frontend_code = _normalize_frontend_files(_normalize_files_dict(state.get("frontend_code") or {}))
    existing_backend_code = _normalize_backend_files(_normalize_files_dict(state.get("backend_code") or {}))
    frontend_model = MODEL_CONFIG.get("code_gen_frontend", MODEL_CONFIG["code_gen"])
    backend_model = MODEL_CONFIG.get("code_gen_backend", MODEL_CONFIG["code_gen"])
    frontend_fallback_models = get_rate_limit_fallback_models(frontend_model)
    backend_fallback_models = get_rate_limit_fallback_models(backend_model)
    frontend_max_attempts = _codegen_max_attempts(frontend_fallback_models)
    backend_max_attempts = _codegen_max_attempts(backend_fallback_models)

    frontend_llm = None
    backend_llm = None
    frontend_llm_error = ""
    backend_llm_error = ""
    try:
        frontend_llm = get_llm(
            model=frontend_model,
            temperature=0.3,
            max_tokens=12000,
        )
    except Exception as exc:
        frontend_llm_error = str(exc)[:200]
        logger.warning("[CODE_GEN] Frontend model unavailable, using fallback bundle: %s", frontend_llm_error)
    try:
        backend_llm = get_llm(
            model=backend_model,
            temperature=0.3,
            max_tokens=10000,
        )
    except Exception as exc:
        backend_llm_error = str(exc)[:200]
        logger.warning("[CODE_GEN] Backend model unavailable, using fallback bundle: %s", backend_llm_error)

    iteration = state.get("code_eval_iteration", 0)
    context = json.dumps(
        {
            "idea": idea,
            "generated_docs": generated_docs,
            "blueprint": blueprint,
            "execution_tasks": execution_tasks,
            "repair_tasks": repair_tasks,
            "task_contracts": task_contracts,
        },
        indent=2,
        ensure_ascii=False,
    )

    eval_feedback = _build_eval_feedback(code_eval_result)
    regenerate_frontend = _should_regenerate_target(
        target="frontend",
        existing_files=existing_frontend_code,
        blueprint=blueprint,
        code_eval_result=code_eval_result,
    )
    regenerate_backend = _should_regenerate_target(
        target="backend",
        existing_files=existing_backend_code,
        blueprint=blueprint,
        code_eval_result=code_eval_result,
    )

    frontend_code = dict(existing_frontend_code)
    backend_code = dict(existing_backend_code)
    force_frontend_fallback = _should_force_frontend_fallback(code_eval_result)

    if regenerate_frontend:
        if force_frontend_fallback or frontend_llm is None:
            logger.warning(
                "[CODE_GEN] Using deterministic frontend scaffold after repeated evaluation failure (forced=%s, model_available=%s)",
                force_frontend_fallback,
                frontend_llm is not None,
            )
            generated_frontend = _build_fallback_frontend_bundle(context)
        else:
            generated_frontend = await _generate_frontend_files(
                frontend_llm,
                context,
                prompt_strategy=prompt_strategy,
                eval_feedback=eval_feedback,
                fallback_models=frontend_fallback_models,
                max_attempts=frontend_max_attempts,
                iteration=iteration,
                has_existing_bundle=bool(existing_frontend_code),
            )
        frontend_code = _merge_generated_files(existing_frontend_code, generated_frontend, label="frontend")
    else:
        logger.info("[CODE_GEN] Reusing previous frontend bundle (%d files)", len(frontend_code))

    if regenerate_frontend and regenerate_backend:
        await asyncio.sleep(_STACK_GENERATION_PAUSE_SECONDS)

    if regenerate_backend:
        if backend_llm is None:
            logger.warning("[CODE_GEN] Using deterministic backend scaffold because the backend model is unavailable")
            generated_backend = _build_fallback_backend_bundle(context)
        else:
            generated_backend = await _generate_backend_files(
                backend_llm,
                context,
                prompt_strategy=prompt_strategy,
                eval_feedback=eval_feedback,
                fallback_models=backend_fallback_models,
                max_attempts=backend_max_attempts,
                iteration=iteration,
                has_existing_bundle=bool(existing_backend_code),
            )
        backend_code = _merge_generated_files(existing_backend_code, generated_backend, label="backend")
    else:
        logger.info("[CODE_GEN] Reusing previous backend bundle (%d files)", len(backend_code))

    frontend_code, backend_code = _normalize_cross_stack(frontend_code, backend_code)

    generation_warnings = []

    if _FALLBACK_FRONTEND_MARKER_FILE in frontend_code:
        generation_warnings.append("fallback_frontend_scaffold_used")
        if frontend_llm_error:
            generation_warnings.append(f"frontend_model_unavailable:{frontend_llm_error}")
    if _FALLBACK_BACKEND_MARKER_FILE in backend_code:
        generation_warnings.append("fallback_backend_scaffold_used")
        if backend_llm_error:
            generation_warnings.append(f"backend_model_unavailable:{backend_llm_error}")

    if regenerate_frontend and len(frontend_code) < _MIN_FRONTEND_FILES:
        warning = (
            f"Frontend generation produced {len(frontend_code)} merged files "
            f"(expected >= {_MIN_FRONTEND_FILES}). "
            f"Files: {list(frontend_code.keys()) if frontend_code else '(none)'}"
        )
        logger.warning("[CODE_GEN] %s", warning)
        generation_warnings.append(warning)

        logger.info("[CODE_GEN] Retrying frontend generation (attempt 2)...")
        retried_frontend = (
            _build_fallback_frontend_bundle(context)
            if frontend_llm is None
            else await _generate_frontend_files(
                frontend_llm,
                context,
                retry=True,
                prompt_strategy=prompt_strategy,
                eval_feedback=eval_feedback,
                fallback_models=frontend_fallback_models,
                max_attempts=frontend_max_attempts,
            )
        )
        frontend_code = _merge_generated_files(frontend_code, retried_frontend, label="frontend")
        frontend_code, backend_code = _normalize_cross_stack(frontend_code, backend_code)

        if len(frontend_code) < _MIN_FRONTEND_FILES:
            retry_warning = (
                f"Frontend retry still has {len(frontend_code)} merged files. "
                "Further code-eval retries are required before deployment."
            )
            logger.warning("[CODE_GEN] %s", retry_warning)
            generation_warnings.append(retry_warning)

    if regenerate_backend and len(backend_code) < _MIN_BACKEND_FILES:
        warning = (
            f"Backend generation produced {len(backend_code)} merged files "
            f"(expected >= {_MIN_BACKEND_FILES}). "
            f"Files: {list(backend_code.keys()) if backend_code else '(none)'}"
        )
        logger.warning("[CODE_GEN] %s", warning)
        generation_warnings.append(warning)

        logger.info("[CODE_GEN] Retrying backend generation (attempt 2)...")
        retried_backend = (
            _build_fallback_backend_bundle(context)
            if backend_llm is None
            else await _generate_backend_files(
                backend_llm,
                context,
                retry=True,
                prompt_strategy=prompt_strategy,
                eval_feedback=eval_feedback,
                fallback_models=backend_fallback_models,
                max_attempts=backend_max_attempts,
            )
        )
        backend_code = _merge_generated_files(backend_code, retried_backend, label="backend")
        frontend_code, backend_code = _normalize_cross_stack(frontend_code, backend_code)

        if len(backend_code) < _MIN_BACKEND_FILES:
            retry_warning = (
                f"Backend retry still has {len(backend_code)} merged files. "
                "Further code-eval retries are required before deployment."
            )
            logger.warning("[CODE_GEN] %s", retry_warning)
            generation_warnings.append(retry_warning)

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


def _should_force_frontend_fallback(code_eval_result: dict | None) -> bool:
    if not isinstance(code_eval_result, dict) or code_eval_result.get("passed", False):
        return False
    if os.getenv("VIBEDEPLOY_ENABLE_LAST_RESORT_FRONTEND_FALLBACK", "").strip() != "1":
        return False

    try:
        iteration = int(code_eval_result.get("iteration", 0) or 0)
    except (TypeError, ValueError):
        iteration = 0
    return iteration >= 1


def _should_regenerate_target(
    *,
    target: str,
    existing_files: dict[str, str],
    blueprint: dict | None,
    code_eval_result: dict | None,
) -> bool:
    expected_files = (blueprint or {}).get(f"{target}_files") or {}
    if not expected_files:
        return False
    if not existing_files:
        return True
    if not code_eval_result:
        return True

    missing_key = f"missing_{target}"
    other_missing_key = "missing_backend" if target == "frontend" else "missing_frontend"
    if code_eval_result.get(missing_key):
        return True
    if code_eval_result.get(other_missing_key):
        return False
    return True


def _merge_generated_files(
    existing_files: dict[str, str],
    generated_files: dict[str, str],
    *,
    label: str,
) -> dict[str, str]:
    if not generated_files:
        if existing_files:
            logger.warning(
                "[CODE_GEN] %s generation returned 0 files; preserving previous %d-file bundle",
                label,
                len(existing_files),
            )
        return dict(existing_files)

    merged = dict(existing_files)
    merged.update(generated_files)
    return merged


def _get_prompt_target_bundle(prompt_strategy: dict | None, target: str) -> dict:
    model_plan = (prompt_strategy or {}).get("model_plan", {}) or {}
    bundle = dict(model_plan.get(target, {}) or {})
    family = bundle.get("family", "generic")
    fallback_families = list(bundle.get("fallback_families", []) or [])
    bundle["family"] = family
    bundle["fallback_families"] = fallback_families
    bundle["families"] = _unique_strings([family, *fallback_families])
    return bundle


def _build_cross_model_user_contract(prompt_strategy: dict | None, target: str) -> str:
    bundle = _get_prompt_target_bundle(prompt_strategy, target)
    contract = ((prompt_strategy or {}).get("cross_model_user_contract") or "").strip()
    lines: list[str] = []

    if "qwen3" in bundle["families"]:
        lines.append("/no_think")

    if contract:
        lines.append(contract)

    if "deepseek_r1" in bundle["families"]:
        lines.append(
            "DeepSeek compatibility note:\n"
            "- All critical instructions are repeated in this user message.\n"
            "- Do not add explanation outside the final JSON payload."
        )

    return "\n\n".join(lines)


def _should_use_user_only_messages(prompt_strategy: dict | None, target: str) -> bool:
    bundle = _get_prompt_target_bundle(prompt_strategy, target)
    return bundle.get("family") == "deepseek_r1"


def _should_repeat_strategy_in_user(prompt_strategy: dict | None, target: str) -> bool:
    bundle = _get_prompt_target_bundle(prompt_strategy, target)
    return "deepseek_r1" in bundle["families"]


def _build_frontend_prompt_messages(
    *,
    context: str,
    prompt_strategy: dict | None,
    retry: bool = False,
    eval_feedback: str | None = None,
    iteration: int = 0,
) -> list[dict[str, str]]:
    extra_instruction = ""
    if retry:
        extra_instruction = (
            "\n\nCRITICAL: Your previous response could not be parsed as valid JSON. "
            'You MUST return ONLY a valid JSON object like: {"files": {"path": "content", ...}}. '
            "No markdown, no explanation — ONLY the JSON object."
        )
    if eval_feedback:
        extra_instruction += f"\n\nPREVIOUS EVALUATION FEEDBACK (fix these issues):\n{eval_feedback}"
    if iteration > 1:
        extra_instruction += (
            f"\n\nITERATION {iteration}: This is retry #{iteration}. "
            "Focus on fixing the specific issues from evaluation feedback. "
            "Do NOT regenerate files that already passed evaluation. "
            "Only modify files that had problems."
        )

    strategy_appendix = ((prompt_strategy or {}).get("frontend_prompt_appendix") or "").strip()
    cross_model_contract = _build_cross_model_user_contract(prompt_strategy, "frontend")
    user_sections = [
        "Generate frontend files from this product context.",
        cross_model_contract,
        "### Product Context\n" + context,
        (
            "### Execution Notes\n"
            "- Convert the PRD, tech spec, and blueprint into a visually distinctive product, not a generic dashboard.\n"
            "- Treat any design_direction, visual_style_hints, ux_highlights, demo_story, and blueprint experience_contract as hard requirements.\n"
            "- The generated src/app/page.tsx must compose multiple domain components from the blueprint manifest, not only a hero form.\n"
            "- If a layout_archetype exists, the DOM structure, section ordering, and spatial rhythm must visibly embody that archetype.\n"
            "- Storyboard, operations console, studio, atlas, and notebook products must not collapse into the same repeated scaffold.\n"
            "- Use the domain's own nouns and surface names. Do not default to the same hero/workspace/feature/collection wording across unrelated products.\n"
            "- Build the first-run experience for judges seeing the app for the first time in a live demo.\n"
        ),
    ]
    if strategy_appendix and _should_repeat_strategy_in_user(prompt_strategy, "frontend"):
        user_sections.insert(2, "### Runtime Strategy Stack\n" + strategy_appendix)

    system_sections = [
        CODE_GENERATION_BASE_SYSTEM_PROMPT,
        FRONTEND_SYSTEM_PROMPT,
        (
            "Return JSON object with exactly one top-level key: 'files'. "
            "EVERY files[path] value must be a string containing the full file contents. "
            "For JSON files like package.json or tsconfig.json, embed the file body as a JSON string, "
            "not as a nested object."
            f"{extra_instruction}"
        ),
    ]
    if strategy_appendix:
        system_sections.append("### Runtime Strategy Stack\n" + strategy_appendix)

    if _should_use_user_only_messages(prompt_strategy, "frontend"):
        return [
            {
                "role": "user",
                "content": "\n\n".join(section for section in [*system_sections, *user_sections] if section),
            }
        ]

    return [
        {"role": "system", "content": "\n\n".join(section for section in system_sections if section)},
        {"role": "user", "content": "\n\n".join(section for section in user_sections if section)},
    ]


def _build_backend_prompt_messages(
    *,
    context: str,
    prompt_strategy: dict | None,
    retry: bool = False,
    eval_feedback: str | None = None,
    iteration: int = 0,
) -> list[dict[str, str]]:
    extra_instruction = ""
    if retry:
        extra_instruction = (
            "\n\nCRITICAL: Your previous response could not be parsed as valid JSON. "
            'You MUST return ONLY a valid JSON object like: {"files": {"path": "content", ...}}. '
            "No markdown, no explanation — ONLY the JSON object."
        )
    if eval_feedback:
        extra_instruction += f"\n\nPREVIOUS EVALUATION FEEDBACK (fix these issues):\n{eval_feedback}"
    if iteration > 1:
        extra_instruction += (
            f"\n\nITERATION {iteration}: This is retry #{iteration}. "
            "Focus on fixing the specific issues from evaluation feedback. "
            "Do NOT regenerate files that already passed evaluation. "
            "Only modify files that had problems."
        )

    strategy_appendix = ((prompt_strategy or {}).get("backend_prompt_appendix") or "").strip()
    cross_model_contract = _build_cross_model_user_contract(prompt_strategy, "backend")
    user_sections = [
        "Generate backend files from this product context. AI features must be integral to business endpoints.",
        cross_model_contract,
        "### Product Context\n" + context,
        (
            "### Execution Notes\n"
            "- Preserve the frontend/backend contract exactly for endpoint paths and request field names.\n"
            "- Preserve the frontend/backend contract for response field names too, so the frontend can safely render returned data.\n"
            "- Keep routes robust behind DigitalOcean ingress by avoiding APIRouter(prefix='/api').\n"
        ),
    ]
    if strategy_appendix and _should_repeat_strategy_in_user(prompt_strategy, "backend"):
        user_sections.insert(2, "### Runtime Strategy Stack\n" + strategy_appendix)

    system_sections = [
        CODE_GENERATION_BASE_SYSTEM_PROMPT,
        BACKEND_SYSTEM_PROMPT,
        (
            "Return JSON object with exactly one top-level key: 'files'. "
            "EVERY files[path] value must be a string containing the full file contents. "
            "For JSON files, return the file body as a JSON string, not as a nested object."
            f"{extra_instruction}"
        ),
    ]
    if strategy_appendix:
        system_sections.append("### Runtime Strategy Stack\n" + strategy_appendix)

    if _should_use_user_only_messages(prompt_strategy, "backend"):
        return [
            {
                "role": "user",
                "content": "\n\n".join(section for section in [*system_sections, *user_sections] if section),
            }
        ]

    return [
        {"role": "system", "content": "\n\n".join(section for section in system_sections if section)},
        {"role": "user", "content": "\n\n".join(section for section in user_sections if section)},
    ]


async def _generate_frontend_files(
    llm,
    context: str,
    retry: bool = False,
    prompt_strategy: dict | None = None,
    eval_feedback: str | None = None,
    fallback_models: list[str] | None = None,
    max_attempts: int = 6,
    iteration: int = 0,
    has_existing_bundle: bool = False,
) -> dict[str, str]:
    try:
        response = await ainvoke_with_retry(
            llm,
            _build_frontend_prompt_messages(
                context=context,
                prompt_strategy=prompt_strategy,
                retry=retry,
                eval_feedback=eval_feedback,
                iteration=iteration,
            ),
            max_attempts=max_attempts,
            fallback_models=fallback_models,
            rate_limit_switch_after_attempts=max_attempts,
        )

        parsed = await _parse_generated_files_response(response.content, label="frontend")
        files = parsed.get("files", {})
        return _normalize_frontend_files(_normalize_files_dict(files))
    except Exception as exc:
        if has_existing_bundle:
            logger.warning("[CODE_GEN] Frontend generation failed; preserving previous bundle: %s", str(exc)[:200])
            return {}
        logger.warning("[CODE_GEN] Falling back to deterministic frontend scaffold: %s", str(exc)[:200])
        return _build_fallback_frontend_bundle(context)


async def _generate_backend_files(
    llm,
    context: str,
    retry: bool = False,
    prompt_strategy: dict | None = None,
    eval_feedback: str | None = None,
    fallback_models: list[str] | None = None,
    max_attempts: int = 6,
    iteration: int = 0,
    has_existing_bundle: bool = False,
) -> dict[str, str]:
    try:
        response = await ainvoke_with_retry(
            llm,
            _build_backend_prompt_messages(
                context=context,
                prompt_strategy=prompt_strategy,
                retry=retry,
                eval_feedback=eval_feedback,
                iteration=iteration,
            ),
            max_attempts=max_attempts,
            fallback_models=fallback_models,
            rate_limit_switch_after_attempts=max_attempts,
        )

        parsed = await _parse_generated_files_response(response.content, label="backend")
        files = parsed.get("files", {})
        return _normalize_backend_files(_normalize_files_dict(files))
    except Exception as exc:
        if has_existing_bundle:
            logger.warning("[CODE_GEN] Backend generation failed; preserving previous bundle: %s", str(exc)[:200])
            return {}
        logger.warning("[CODE_GEN] Falling back to deterministic backend scaffold: %s", str(exc)[:200])
        return _build_fallback_backend_bundle(context)


def _extract_template_seed(context: str) -> dict[str, object]:
    try:
        payload = json.loads(context)
    except Exception:
        payload = {}

    idea = payload.get("idea", {}) if isinstance(payload, dict) else {}
    if not isinstance(idea, dict):
        idea = {}

    title = str(idea.get("name") or "VibeLaunch").strip() or "VibeLaunch"
    tagline = str(idea.get("tagline") or "Turn an idea into a polished demo.").strip()
    features = _seed_text_list(idea.get("key_features"))
    if not features:
        features = ["Guided workflow", "Insights panel", "Saved sessions"]
    proof_points = _seed_text_list(idea.get("proof_points"))
    if not proof_points:
        proof_points = ["Shareable outputs", "Visible recent activity", "Clear next actions"]
    surfaces = _seed_text_list(idea.get("must_have_surfaces"))
    trust_surfaces = _seed_text_list(idea.get("trust_surfaces"))
    output_entities = _seed_text_list(idea.get("output_entities"))
    sample_seed_data = _seed_text_list(idea.get("sample_seed_data"))
    reference_objects = _seed_text_list(idea.get("reference_objects"))
    signature_demo_moments = _seed_text_list(idea.get("signature_demo_moments"))
    input_labels = idea.get("input_labels") if isinstance(idea.get("input_labels"), dict) else {}

    layout_archetype = str(idea.get("layout_archetype") or "").strip().lower()
    interface_metaphor = str(idea.get("interface_metaphor") or "").strip()
    domain = str(idea.get("domain") or "").strip().lower()
    ui_copy_tone = str(idea.get("ui_copy_tone") or "").strip()
    primary_action_label = str(idea.get("primary_action_label") or "").strip() or "Generate showcase plan"
    ready_title = signature_demo_moments[0] if signature_demo_moments else "Ready for the live demo"
    ready_detail = (
        str(idea.get("demo_story_hints") or "").strip()
        or "The first action should create a visible, judge-friendly output."
    )
    flagship_hint = str(idea.get("selected_flagship") or title or domain).strip()
    domain_defaults = _fallback_domain_defaults(domain, interface_metaphor, flagship_hint)
    if not ui_copy_tone:
        ui_copy_tone = domain_defaults["ui_copy_tone"]
    if not ready_detail or ("trip" in ready_detail.lower() and "travel" not in domain):
        ready_detail = domain_defaults["ready_detail"]

    palette = _fallback_palette_for_profile(layout_archetype or domain, flagship_hint)
    surface_labels = {
        "hero": interface_metaphor or domain_defaults["hero"] or _fallback_surface_label(layout_archetype, "hero"),
        "workspace": surfaces[0]
        if surfaces
        else domain_defaults["workspace"] or _fallback_surface_label(layout_archetype, "workspace"),
        "result": surfaces[1]
        if len(surfaces) > 1
        else domain_defaults["result"] or _fallback_surface_label(layout_archetype, "result"),
        "support": trust_surfaces[0]
        if trust_surfaces
        else domain_defaults["support"] or _fallback_surface_label(layout_archetype, "support"),
        "collection": surfaces[-1]
        if surfaces
        else domain_defaults["collection"] or _fallback_surface_label(layout_archetype, "collection"),
    }
    placeholders = {
        "query": str(
            input_labels.get("query_label")
            or domain_defaults["query_placeholder"]
            or "Describe the session you want to generate."
        ).strip(),
        "preferences": str(
            input_labels.get("preferences_label")
            or domain_defaults["preferences_placeholder"]
            or "Add constraints, style cues, or priorities."
        ).strip(),
    }
    stats = [
        {
            "label": output_entities[0]
            if output_entities
            else reference_objects[0]
            if reference_objects
            else "Feature lanes",
            "value": str(len(features)),
        },
        {"label": surface_labels["collection"], "value": "0"},
        {"label": "Readiness score", "value": "88"},
    ]

    return {
        "title": title,
        "tagline": tagline,
        "slug": re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "vibelaunch",
        "features": features[:4],
        "proof_points": proof_points[:4],
        "layout_archetype": layout_archetype,
        "domain": domain,
        "ui_copy_tone": ui_copy_tone,
        "primary_action_label": primary_action_label
        if primary_action_label != "Generate showcase plan"
        else domain_defaults["button_label"],
        "ready_title": ready_title if ready_title != "Ready for the live demo" else domain_defaults["ready_title"],
        "ready_detail": ready_detail,
        "surface_labels": surface_labels,
        "placeholders": placeholders,
        "stats": stats,
        "sample_seed_data": sample_seed_data[:4] or reference_objects[:4] or features[:4],
        "reference_objects": reference_objects[:5] or output_entities[:5] or features[:5],
        "palette": palette,
        "collection_title": (
            f"{interface_metaphor.title()} stays visible after each run."
            if interface_metaphor
            else domain_defaults["collection_title"]
        ),
        "support_title": (trust_surfaces[0].title() if trust_surfaces else domain_defaults["support_title"]),
        "reference_title": (surfaces[2].title() if len(surfaces) > 2 else domain_defaults["reference_title"]),
        "button_label": primary_action_label
        if primary_action_label != "Generate showcase plan"
        else domain_defaults["button_label"],
    }


def _fallback_domain_defaults(domain: str, interface_metaphor: str, flagship_hint: str = "") -> dict[str, str]:
    normalized = " ".join(part for part in [domain or "", flagship_hint or ""] if part).lower()
    if "creator" in normalized or "content" in normalized:
        return {
            "hero": interface_metaphor or "editorial production board",
            "workspace": "hook card builder",
            "result": "shot list",
            "support": "repurpose lane",
            "collection": "publish queue",
            "query_placeholder": "Content angle, audience, or campaign brief",
            "preferences_placeholder": "Platforms, tone, cadence, and recording constraints",
            "button_label": "Generate content batch",
            "ready_title": "assembling a multi-post creator batch live",
            "ready_detail": "Show the system turning rough content intent into a reusable creator batch with hooks, shot lists, and repurpose lanes.",
            "collection_title": "Editorial Production Board stays visible after each run.",
            "support_title": "Repurpose Lane",
            "reference_title": "Publish Queue",
            "ui_copy_tone": "creator-native and decisive",
        }
    if "travel" in normalized or "weekender" in normalized:
        return {
            "hero": interface_metaphor or "postcard route studio",
            "workspace": "route card",
            "result": "district stop",
            "support": "saved trip shelf",
            "collection": "destination brief",
            "query_placeholder": "Trip brief, mood, or city goal",
            "preferences_placeholder": "Style, budget, season, and must-see cues",
            "button_label": "Build trip route",
            "ready_title": "assembling a day-by-day route live",
            "ready_detail": "Show the system turning a rough travel cue into a screenshot-ready route board with stops, backups, and timing fallbacks.",
            "collection_title": "Postcard Route Studio stays visible after each run.",
            "support_title": "Saved Trip Shelf",
            "reference_title": "Backup Plan",
            "ui_copy_tone": "cinematic and traveler-friendly",
        }
    if "budget" in normalized or "cash runway" in normalized or "financial" in normalized:
        return {
            "hero": interface_metaphor or "money runway atlas",
            "workspace": "runway band",
            "result": "scenario card",
            "support": "safety ladder",
            "collection": "money bucket archive",
            "query_placeholder": "Income shock, budget reset, or monthly target",
            "preferences_placeholder": "Bills, risk tolerance, runway goal, and safety rules",
            "button_label": "Build runway plan",
            "ready_title": "turning a reset brief into a runway map",
            "ready_detail": "Show the system turning a money reset brief into a visible runway plan with buckets, scenarios, and tradeoff clarity.",
            "collection_title": "Money Runway Atlas stays visible after each run.",
            "support_title": "Safety Ladder",
            "reference_title": "Scenario Card",
            "ui_copy_tone": "calm and analytical",
        }
    if "interview" in normalized or "learning" in normalized:
        return {
            "hero": interface_metaphor or "curriculum workshop",
            "workspace": "sprint lane",
            "result": "drill card",
            "support": "review block",
            "collection": "saved revision roadmap",
            "query_placeholder": "Learning goal or interview target",
            "preferences_placeholder": "Available time, topics, and pressure points",
            "button_label": "Generate study sprint",
            "ready_title": "turning a vague goal into a syllabus instantly",
            "ready_detail": "Show the system turning an interview target into a sprint lane, drill sequence, and saved revision roadmap.",
            "collection_title": "Curriculum Workshop stays visible after each run.",
            "support_title": "Review Block",
            "reference_title": "Confidence Checkpoint",
            "ui_copy_tone": "focused and coach-like",
        }
    if "meal" in normalized or "grocery" in normalized:
        return {
            "hero": interface_metaphor or "kitchen prep atlas",
            "workspace": "prep block",
            "result": "meal board",
            "support": "grocery lane",
            "collection": "saved meal board",
            "query_placeholder": "Weekly cooking goal, diet, or meal prep brief",
            "preferences_placeholder": "Household size, prep time, budget, and ingredients to use",
            "button_label": "Generate meal prep board",
            "ready_title": "turning grocery inspiration into a prep board",
            "ready_detail": "Show the system turning cooking inspiration into prep blocks, grocery lanes, and a reusable meal board.",
            "collection_title": "Kitchen Prep Atlas stays visible after each run.",
            "support_title": "Grocery Lane",
            "reference_title": "Container Checklist",
            "ui_copy_tone": "practical and kitchen-ready",
        }
    return {
        "hero": interface_metaphor or "product surface",
        "workspace": "primary workspace",
        "result": "insight panel",
        "support": "supporting evidence",
        "collection": "saved library",
        "query_placeholder": "Describe the session you want to generate.",
        "preferences_placeholder": "Add constraints, style cues, or priorities.",
        "button_label": "Generate showcase plan",
        "ready_title": "Ready for the live demo",
        "ready_detail": "The first action should create a visible, judge-friendly output.",
        "collection_title": "Outputs stay visible after each successful run.",
        "support_title": "Supporting evidence and proof points",
        "reference_title": "Signature demo objects",
        "ui_copy_tone": "clear and direct",
    }


def _fallback_surface_label(layout_archetype: str, role: str) -> str:
    labels = {
        "storyboard": {
            "hero": "Postcard route studio",
            "workspace": "Trip brief editor",
            "result": "Day-by-day route board",
            "support": "Moodboard highlights",
            "collection": "Saved itineraries",
        },
        "operations_console": {
            "hero": "Live show command center",
            "workspace": "Run-of-show builder",
            "result": "Cue timeline",
            "support": "Readiness and incident lane",
            "collection": "Saved show plans",
        },
        "studio": {
            "hero": "Curriculum workshop",
            "workspace": "Study sprint builder",
            "result": "Syllabus board",
            "support": "Review cadence rail",
            "collection": "Saved study plans",
        },
        "atlas": {
            "hero": "Money runway atlas",
            "workspace": "Planning scenario builder",
            "result": "Runway and bucket plan",
            "support": "Risk and confidence rail",
            "collection": "Saved money plans",
        },
        "notebook": {
            "hero": "Growth notebook",
            "workspace": "Roadmap brief",
            "result": "Milestone roadmap",
            "support": "Coach notes and proof artifacts",
            "collection": "Saved coaching paths",
        },
    }
    return labels.get(layout_archetype, {}).get(
        role,
        {
            "hero": "Product surface",
            "workspace": "Primary workspace",
            "result": "Insight or result panel",
            "support": "Secondary supporting panel",
            "collection": "Saved library and recent activity",
        }[role],
    )


def _fallback_palette_for_layout(layout_archetype: str) -> dict[str, str]:
    palettes = {
        "storyboard": {
            "background": "#f6efe3",
            "foreground": "#1f1a17",
            "primary": "#0f5f52",
            "accent": "#d98c3f",
            "card": "rgba(255, 252, 246, 0.88)",
            "muted": "rgba(31, 26, 23, 0.62)",
            "border": "rgba(31, 26, 23, 0.12)",
            "font": 'Georgia, "Times New Roman", serif',
        },
        "operations_console": {
            "background": "#0b1020",
            "foreground": "#edf2ff",
            "primary": "#60f5c0",
            "accent": "#ff7b54",
            "card": "rgba(18, 24, 44, 0.88)",
            "muted": "rgba(237, 242, 255, 0.68)",
            "border": "rgba(141, 165, 214, 0.22)",
            "font": '"Space Grotesk", "Helvetica Neue", sans-serif',
        },
        "studio": {
            "background": "#f4f7ff",
            "foreground": "#172033",
            "primary": "#3657ff",
            "accent": "#ff8a3d",
            "card": "rgba(255, 255, 255, 0.9)",
            "muted": "rgba(23, 32, 51, 0.64)",
            "border": "rgba(54, 87, 255, 0.14)",
            "font": '"Sora", "Avenir Next", sans-serif',
        },
        "atlas": {
            "background": "#eef1eb",
            "foreground": "#162018",
            "primary": "#2f6b47",
            "accent": "#f2a03d",
            "card": "rgba(252, 255, 249, 0.9)",
            "muted": "rgba(22, 32, 24, 0.62)",
            "border": "rgba(22, 32, 24, 0.12)",
            "font": '"IBM Plex Sans", "Helvetica Neue", sans-serif',
        },
        "notebook": {
            "background": "#f3eee7",
            "foreground": "#231b17",
            "primary": "#6b4f3a",
            "accent": "#2d7f6f",
            "card": "rgba(255, 251, 247, 0.9)",
            "muted": "rgba(35, 27, 23, 0.64)",
            "border": "rgba(35, 27, 23, 0.12)",
            "font": '"Fraunces", Georgia, serif',
        },
    }
    return palettes.get(
        layout_archetype,
        {
            "background": "#f3efe4",
            "foreground": "#1f1a17",
            "primary": "#0f5f52",
            "accent": "#d98c3f",
            "card": "rgba(255, 252, 246, 0.86)",
            "muted": "rgba(31, 26, 23, 0.62)",
            "border": "rgba(31, 26, 23, 0.12)",
            "font": 'Georgia, "Times New Roman", serif',
        },
    )


def _fallback_palette_for_profile(layout_archetype: str, flagship_hint: str) -> dict[str, str]:
    normalized = str(flagship_hint or "").lower()
    if "creator" in normalized:
        return {
            "background": "#f7f2ec",
            "foreground": "#1d1820",
            "primary": "#1a1330",
            "accent": "#ff6b6b",
            "card": "rgba(255, 248, 243, 0.9)",
            "muted": "rgba(29, 24, 32, 0.62)",
            "border": "rgba(29, 24, 32, 0.12)",
            "font": '"Fraunces", Georgia, serif',
        }
    if "weekender" in normalized or "routepostcard" in normalized or "travel" in normalized:
        return {
            "background": "#f5eadc",
            "foreground": "#211814",
            "primary": "#0c5c73",
            "accent": "#f08a3c",
            "card": "rgba(255, 249, 242, 0.9)",
            "muted": "rgba(33, 24, 20, 0.6)",
            "border": "rgba(33, 24, 20, 0.12)",
            "font": '"Cormorant Garamond", Georgia, serif',
        }
    if "runway" in normalized or "ledger" in normalized or "finance" in normalized:
        return {
            "background": "#f3f5f2",
            "foreground": "#142018",
            "primary": "#0f6c48",
            "accent": "#d9a441",
            "card": "rgba(252, 255, 250, 0.92)",
            "muted": "rgba(20, 32, 24, 0.6)",
            "border": "rgba(20, 32, 24, 0.1)",
            "font": '"IBM Plex Sans", "Helvetica Neue", sans-serif',
        }
    if "interview" in normalized or "forge" in normalized or "study" in normalized:
        return {
            "background": "#eff3ff",
            "foreground": "#162139",
            "primary": "#3159ff",
            "accent": "#ff9a3d",
            "card": "rgba(255, 255, 255, 0.92)",
            "muted": "rgba(22, 33, 57, 0.6)",
            "border": "rgba(49, 89, 255, 0.12)",
            "font": '"Sora", "Avenir Next", sans-serif',
        }
    if "meal" in normalized or "prep" in normalized or "kitchen" in normalized:
        return {
            "background": "#f1f6ea",
            "foreground": "#182114",
            "primary": "#497b2b",
            "accent": "#ff9f43",
            "card": "rgba(252, 255, 248, 0.92)",
            "muted": "rgba(24, 33, 20, 0.58)",
            "border": "rgba(24, 33, 20, 0.1)",
            "font": '"IBM Plex Sans", "Helvetica Neue", sans-serif',
        }
    return _fallback_palette_for_layout(layout_archetype)


def _build_fallback_frontend_bundle(context: str) -> dict[str, str]:
    seed = _extract_template_seed(context)
    title = str(seed["title"])
    tagline = str(seed["tagline"])
    palette = dict(seed["palette"])

    return _normalize_frontend_files(
        {
            _FALLBACK_FRONTEND_MARKER_FILE: json.dumps(
                {"kind": "frontend", "reason": "deterministic_fallback"}, indent=2
            ),
            "package.json": json.dumps({"name": str(seed["slug"]), "private": True}, indent=2),
            "next.config.js": """/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${apiBase}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
""",
            "public/hero-scene.svg": _build_fallback_scene_svg(seed),
            "public/thumb-1.svg": _build_fallback_thumb_svg(seed, 0),
            "public/thumb-2.svg": _build_fallback_thumb_svg(seed, 1),
            "public/thumb-3.svg": _build_fallback_thumb_svg(seed, 2),
            "src/app/layout.tsx": f"""import type {{ Metadata }} from "next";
import type {{ ReactNode }} from "react";
import "./globals.css";

export const metadata: Metadata = {{
  title: {json.dumps(title)},
  description: {json.dumps(tagline)},
}};

export default function RootLayout({{ children }}: {{ children: ReactNode }}) {{
  return (
    <html lang="en">
      <body>{{children}}</body>
    </html>
  );
}}
""",
            "src/app/page.tsx": _build_fallback_page_source(seed),
            "src/app/globals.css": _build_fallback_globals_css(seed, palette),
            "src/lib/api.ts": """const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function throwApiError(response: Response): Promise<never> {
  const raw = await response.text();
  throw new Error(raw || "Request failed");
}

async function request<T>(path: string, body: Record<string, unknown>): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    return throwApiError(res);
  }
  return res.json();
}

export async function createPlan(body: { query: string; preferences: string }) {
  return request<{ summary: string; score: number; items: Array<{ title: string; detail: string; score: number }> }>(
    "/api/plan",
    body,
  );
}

export async function createInsights(body: { selection: string; context: string }) {
  return request<{ insights: string[]; next_actions: string[]; highlights: string[] }>("/api/insights", body);
}
""",
            "src/components/Hero.tsx": """type HeroProps = {
  appName: string;
  tagline: string;
  proofPoints: string[];
  eyebrow: string;
  visualSrc: string;
};

export default function Hero({ appName, tagline, proofPoints, eyebrow, visualSrc }: HeroProps) {
  return (
    <section className="hero">
      <div className="hero-copy">
        <span className="eyebrow">{eyebrow}</span>
        <h1>{appName}</h1>
        <p>{tagline}</p>
        <ul className="hero-proof-list">
          {proofPoints.map((point) => (
            <li className="proof-pill" key={point}>{point}</li>
          ))}
        </ul>
      </div>
      <div className="hero-visual-frame">
        <img className="hero-visual" src={visualSrc} alt={`${appName} visual`} />
      </div>
    </section>
  );
}
""",
            "src/components/WorkspacePanel.tsx": """type WorkspacePanelProps = {
  query: string;
  preferences: string;
  onQueryChange: (value: string) => void;
  onPreferencesChange: (value: string) => void;
  onGenerate: () => void;
  loading: boolean;
  features: string[];
  eyebrow: string;
  queryPlaceholder: string;
  preferencesPlaceholder: string;
  actionLabel: string;
};

export default function WorkspacePanel({
  query,
  preferences,
  onQueryChange,
  onPreferencesChange,
  onGenerate,
  loading,
  features,
  eyebrow,
  queryPlaceholder,
  preferencesPlaceholder,
  actionLabel,
}: WorkspacePanelProps) {
  return (
    <section className="workspace-panel">
      <span className="eyebrow">{eyebrow}</span>
      <div className="controls">
        <textarea value={query} onChange={(event) => onQueryChange(event.target.value)} placeholder={queryPlaceholder} />
        <textarea value={preferences} onChange={(event) => onPreferencesChange(event.target.value)} placeholder={preferencesPlaceholder} />
        <div className="button-row">
          <button className="primary-button" onClick={onGenerate} disabled={loading}>
            {loading ? "Generating..." : actionLabel}
          </button>
        </div>
      </div>
      <div className="feature-chips">
        {features.map((feature) => (
          <span className="feature-chip" key={feature}>{feature}</span>
        ))}
      </div>
    </section>
  );
}
""",
            "src/components/InsightPanel.tsx": """type PlanPayload = {
  summary: string;
  score: number;
  items: Array<{ title: string; detail: string; score: number }>;
  insights?: { insights: string[]; next_actions: string[]; highlights: string[] };
};

export default function InsightPanel({ plan, eyebrow }: { plan: PlanPayload; eyebrow: string }) {
  return (
    <section className="insight-panel">
      <span className="eyebrow">{eyebrow}</span>
      <span className="score-pill">Readiness score {plan.score}</span>
      <h2>{plan.summary}</h2>
      {plan.items.map((item) => (
        <article className="item-card" key={item.title}>
          <h3>{item.title}</h3>
          <p>{item.detail}</p>
        </article>
      ))}
      {plan.insights ? (
        <ul className="insight-list">
          {plan.insights.highlights.concat(plan.insights.next_actions).map((entry) => (
            <li key={entry}>{entry}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
""",
            "src/components/FeaturePanel.tsx": """type FeaturePanelProps = {
  eyebrow: string;
  title: string;
  features: string[];
  proofPoints: string[];
};

export default function FeaturePanel({ eyebrow, title, features, proofPoints }: FeaturePanelProps) {
  return (
    <section className="feature-panel">
      <span className="eyebrow">{eyebrow}</span>
      <h2>{title}</h2>
      <div className="feature-columns">
        <div className="feature-group">
          <h3>Core moves</h3>
          <ul className="feature-list">
            {features.map((entry) => (
              <li key={entry}>{entry}</li>
            ))}
          </ul>
        </div>
        <div className="feature-group">
          <h3>Proof markers</h3>
          <ul className="feature-list feature-proof-list">
            {proofPoints.map((entry) => (
              <li key={entry}>{entry}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
""",
            "src/components/ReferenceShelf.tsx": """type ReferenceShelfProps = {
  eyebrow: string;
  title: string;
  items: string[];
  objects: string[];
  tone: string;
  thumbs: string[];
};

export default function ReferenceShelf({ eyebrow, title, items, objects, tone, thumbs }: ReferenceShelfProps) {
  return (
    <section className="reference-shelf">
      <div className="section-heading">
        <span className="eyebrow">{eyebrow}</span>
        <h2>{title}</h2>
        <p>{tone}</p>
      </div>
      <div className="reference-grid">
        {items.map((item, index) => (
          <article className="reference-card" key={`${item}-${index}`}>
            <img
              className="reference-thumb"
              src={thumbs[index % Math.max(thumbs.length, 1)] || "/thumb-1.svg"}
              alt={`${item} visual`}
            />
            <strong>{item}</strong>
            <span>{objects[index % Math.max(objects.length, 1)] || title}</span>
          </article>
        ))}
      </div>
      <div className="object-strip">
        {objects.map((objectName) => (
          <span className="object-pill" key={objectName}>{objectName}</span>
        ))}
      </div>
    </section>
  );
}
""",
            "src/components/CollectionPanel.tsx": """type SavedPlan = {
  summary: string;
  score: number;
  items: Array<{ title: string; detail: string; score: number }>;
};

export default function CollectionPanel({
  saved,
  eyebrow,
  title,
  emptyTitle,
  emptyDetail,
}: {
  saved: SavedPlan[];
  eyebrow: string;
  title: string;
  emptyTitle: string;
  emptyDetail: string;
}) {
  return (
    <section className="collection-panel">
      <div className="section-heading">
        <span className="eyebrow">{eyebrow}</span>
        <h2>{title}</h2>
      </div>
      <div className="saved-grid">
        {saved.length ? (
          saved.map((entry, index) => (
            <article className="saved-card" key={`${entry.summary}-${index}`}>
              <span className="saved-score">Score {entry.score}</span>
              <h3>{entry.summary}</h3>
              <ul>
                {entry.items.slice(0, 2).map((item) => (
                  <li key={item.title}>{item.title}</li>
                ))}
              </ul>
            </article>
          ))
        ) : (
            <article className="saved-card">
              <span className="saved-score">Empty state</span>
              <h3>{emptyTitle}</h3>
              <p>{emptyDetail}</p>
           </article>
        )}
      </div>
    </section>
  );
}
""",
            "src/components/StatePanel.tsx": """export default function StatePanel({
  eyebrow,
  title,
  detail,
  tone,
}: {
  eyebrow: string;
  title: string;
  detail: string;
  tone: "neutral" | "error";
}) {
  return (
    <section className="status-panel">
      <span className="eyebrow">{eyebrow || (tone === "error" ? "Attention" : "Ready")}</span>
      <h2>{title}</h2>
      <p>{detail}</p>
    </section>
  );
}
""",
            "src/components/StatsStrip.tsx": """type StatsStripProps = {
  stats: Array<{ label: string; value: string }>;
};

export default function StatsStrip({ stats }: StatsStripProps) {
  return (
    <section className="stats-strip">
      {stats.map((stat) => (
        <article className="stat-chip" key={stat.label}>
          <span className="eyebrow">{stat.label}</span>
          <strong>{stat.value}</strong>
        </article>
      ))}
    </section>
  );
}
""",
        }
    )


def _build_fallback_page_source(seed: dict[str, object]) -> str:
    title_json = json.dumps(str(seed["title"]))
    tagline_json = json.dumps(str(seed["tagline"]))
    features_json = json.dumps(list(seed["features"]))
    proof_points_json = json.dumps(list(seed["proof_points"]))
    surface_labels_json = json.dumps(seed["surface_labels"])
    placeholders_json = json.dumps(seed["placeholders"])
    stats_json = json.dumps(seed["stats"])
    ready_title_json = json.dumps(str(seed["ready_title"]))
    ready_detail_json = json.dumps(str(seed["ready_detail"]))
    collection_title_json = json.dumps(str(seed["collection_title"]))
    support_title_json = json.dumps(str(seed["support_title"]))
    reference_title_json = json.dumps(str(seed["reference_title"]))
    button_label_json = json.dumps(str(seed["button_label"]))
    layout_json = json.dumps(str(seed["layout_archetype"] or "lab"))
    ui_copy_tone_json = json.dumps(str(seed["ui_copy_tone"] or "intentional and domain-specific"))
    sample_seed_data_json = json.dumps(list(seed["sample_seed_data"]))
    reference_objects_json = json.dumps(list(seed["reference_objects"]))
    hero_visual_json = json.dumps("/hero-scene.svg")
    thumbs_json = json.dumps(["/thumb-1.svg", "/thumb-2.svg", "/thumb-3.svg"])
    slug_json = json.dumps(str(seed["slug"]))
    empty_collection_title_json = json.dumps(f"Create the first {str(seed['surface_labels']['collection']).lower()}")
    empty_collection_detail_json = json.dumps(
        f"The {str(seed['surface_labels']['collection']).lower()} surface fills after the first successful run."
    )

    return f""""use client";

import {{ useState }} from "react";
import CollectionPanel from "@/components/CollectionPanel";
import FeaturePanel from "@/components/FeaturePanel";
import Hero from "@/components/Hero";
import InsightPanel from "@/components/InsightPanel";
import ReferenceShelf from "@/components/ReferenceShelf";
import StatePanel from "@/components/StatePanel";
import StatsStrip from "@/components/StatsStrip";
import WorkspacePanel from "@/components/WorkspacePanel";
import {{ createInsights, createPlan }} from "@/lib/api";

const APP_NAME = {title_json};
const TAGLINE = {tagline_json};
const FEATURE_CHIPS = {features_json};
const PROOF_POINTS = {proof_points_json};
const SURFACE_LABELS = {surface_labels_json};
const PLACEHOLDERS = {placeholders_json};
const DEFAULT_STATS = {stats_json};
const READY_TITLE = {ready_title_json};
const READY_DETAIL = {ready_detail_json};
const COLLECTION_TITLE = {collection_title_json};
const SUPPORT_TITLE = {support_title_json};
const REFERENCE_TITLE = {reference_title_json};
const BUTTON_LABEL = {button_label_json};
type LayoutKind = "storyboard" | "operations_console" | "studio" | "atlas" | "notebook" | "lab";
const LAYOUT: LayoutKind = {layout_json};
const UI_COPY_TONE = {ui_copy_tone_json};
const SAMPLE_ITEMS = {sample_seed_data_json};
const REFERENCE_OBJECTS = {reference_objects_json};
const HERO_VISUAL = {hero_visual_json};
const THUMBS = {thumbs_json};
const DOMAIN_CLASS: string = {slug_json};
const EMPTY_COLLECTION_TITLE = {empty_collection_title_json};
const EMPTY_COLLECTION_DETAIL = {empty_collection_detail_json};

type PlanItem = {{ title: string; detail: string; score: number }};
type InsightPayload = {{ insights: string[]; next_actions: string[]; highlights: string[] }};
type PlanPayload = {{ summary: string; score: number; items: PlanItem[]; insights?: InsightPayload }};

export default function Page() {{
  const [query, setQuery] = useState("");
  const [preferences, setPreferences] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [plan, setPlan] = useState<PlanPayload | null>(null);
  const [saved, setSaved] = useState<PlanPayload[]>([]);
  const layoutClass = LAYOUT.replace(/_/g, "-");

  async function handleGenerate() {{
    setLoading(true);
    setError("");
    try {{
      const nextPlan = await createPlan({{ query, preferences }});
      const insightPayload = await createInsights({{
        selection: nextPlan.items?.[0]?.title ?? query,
        context: preferences || query,
      }});
      const composed = {{ ...nextPlan, insights: insightPayload }};
      setPlan(composed);
      setSaved((previous) => [composed, ...previous].slice(0, 4));
    }} catch (err) {{
      setError(err instanceof Error ? err.message : "Request failed");
    }} finally {{
      setLoading(false);
    }}
  }}

  const stats = DEFAULT_STATS.map((stat, index) => {{
    if (index === 0) return {{ ...stat, value: String(FEATURE_CHIPS.length) }};
    if (index === 1) return {{ ...stat, value: String(saved.length) }};
    if (index === 2) return {{ ...stat, value: plan ? String(plan.score) : stat.value }};
    return stat;
  }});

  const heroNode = (
    <Hero
      appName={{APP_NAME}}
      tagline={{TAGLINE}}
      proofPoints={{PROOF_POINTS}}
      eyebrow={{SURFACE_LABELS.hero}}
      visualSrc={{HERO_VISUAL}}
    />
  );
  const statsNode = <StatsStrip stats={{stats}} />;
  const workspaceNode = (
    <WorkspacePanel
      query={{query}}
      preferences={{preferences}}
      onQueryChange={{setQuery}}
      onPreferencesChange={{setPreferences}}
      onGenerate={{handleGenerate}}
      loading={{loading}}
      features={{FEATURE_CHIPS}}
      eyebrow={{SURFACE_LABELS.workspace}}
      queryPlaceholder={{PLACEHOLDERS.query}}
      preferencesPlaceholder={{PLACEHOLDERS.preferences}}
      actionLabel={{BUTTON_LABEL}}
    />
  );
  const primaryNode = error ? (
    <StatePanel eyebrow="Request blocked" title="Request blocked" tone="error" detail={{error}} />
  ) : plan ? (
    <InsightPanel plan={{plan}} eyebrow={{SURFACE_LABELS.result}} />
  ) : (
    <StatePanel eyebrow={{SURFACE_LABELS.result}} title={{READY_TITLE}} tone="neutral" detail={{READY_DETAIL}} />
  );
  const featureNode = (
    <FeaturePanel eyebrow={{SURFACE_LABELS.support}} title={{SUPPORT_TITLE}} features={{FEATURE_CHIPS}} proofPoints={{PROOF_POINTS}} />
  );
  const collectionNode = (
    <CollectionPanel
      eyebrow={{SURFACE_LABELS.collection}}
      title={{COLLECTION_TITLE}}
      saved={{saved}}
      emptyTitle={{EMPTY_COLLECTION_TITLE}}
      emptyDetail={{EMPTY_COLLECTION_DETAIL}}
    />
  );
  const referenceNode = (
    <ReferenceShelf
      eyebrow={{SURFACE_LABELS.support}}
      title={{REFERENCE_TITLE}}
      items={{SAMPLE_ITEMS}}
      objects={{REFERENCE_OBJECTS}}
      tone={{UI_COPY_TONE}}
      thumbs={{THUMBS}}
    />
  );

  function renderLayout() {{
    if (DOMAIN_CLASS === "creator-batch-studio") {{
      return (
        <section className="creator-shell">
          <div className="creator-topline">
            <div className="creator-workbench">
              {{workspaceNode}}
              {{statsNode}}
            </div>
            {{heroNode}}
          </div>
          <div className="creator-editorial-stage">
            <div className="creator-side-rail">
              {{featureNode}}
            </div>
            <div className="creator-primary-rail">{{primaryNode}}</div>
            <div className="creator-library-rail">
              {{referenceNode}}
            </div>
          </div>
          <div className="creator-bottomline">
            <div className="creator-collection-rail">
              {{collectionNode}}
            </div>
            <div className="creator-proof-rail">{{referenceNode}}</div>
          </div>
        </section>
      );
    }}

    if (DOMAIN_CLASS === "weekender-route-postcards") {{
      return (
        <section className="travel-shell">
          {{heroNode}}
          {{statsNode}}
          <div className="travel-ribbon">{{referenceNode}}</div>
          <div className="travel-planner-grid">
            <div className="travel-brief-column">{{workspaceNode}}</div>
            <div className="travel-result-column">
              {{primaryNode}}
              {{collectionNode}}
            </div>
            <div className="travel-proof-column">
              {{featureNode}}
            </div>
          </div>
        </section>
      );
    }}

    if (DOMAIN_CLASS === "meal-prep-atlas") {{
      return (
        <section className="meal-shell">
          <div className="meal-top-row">
            {{heroNode}}
            <div className="meal-proof-stack">
              {{statsNode}}
              {{featureNode}}
            </div>
          </div>
          <div className="meal-main-grid">
            <div className="meal-planner-column">{{workspaceNode}}</div>
            <div className="meal-reference-column">{{referenceNode}}</div>
          </div>
          <div className="meal-bottom-row">
            {{primaryNode}}
            {{collectionNode}}
          </div>
        </section>
      );
    }}

    if (LAYOUT === "storyboard") {{
      return (
        <>
          {{heroNode}}
          {{statsNode}}
          <section className="storyboard-stage">
            <div className="storyboard-main">
              {{workspaceNode}}
              {{primaryNode}}
            </div>
            <div className="storyboard-side">
              {{referenceNode}}
              {{featureNode}}
            </div>
          </section>
          {{collectionNode}}
        </>
      );
    }}

    if (LAYOUT === "operations_console") {{
      return (
        <section className="console-shell">
          <div className="console-top">
            {{heroNode}}
            {{statsNode}}
          </div>
          <div className="console-grid">
            <div className="console-operator-lane">
              {{workspaceNode}}
              {{referenceNode}}
            </div>
            <div className="console-timeline-lane">{{primaryNode}}</div>
            <div className="console-support-lane">
              {{featureNode}}
              {{collectionNode}}
            </div>
          </div>
        </section>
      );
    }}

    if (LAYOUT === "studio") {{
      return (
        <section className="studio-shell">
          <div className="studio-top">
            {{heroNode}}
            {{primaryNode}}
          </div>
          {{statsNode}}
          <div className="studio-bottom">
            <div className="studio-left">
              {{workspaceNode}}
              {{collectionNode}}
            </div>
            <div className="studio-right">
              {{referenceNode}}
              {{featureNode}}
            </div>
          </div>
        </section>
      );
    }}

    if (LAYOUT === "atlas") {{
      return (
        <section className="atlas-shell">
          <div className="atlas-hero-row">
            {{heroNode}}
            <div className="atlas-side-stack">
              {{statsNode}}
              {{referenceNode}}
            </div>
          </div>
          <div className="atlas-main-row">
            <div className="atlas-primary-stack">
              {{primaryNode}}
              {{collectionNode}}
            </div>
            <div className="atlas-secondary-stack">
              {{workspaceNode}}
              {{featureNode}}
            </div>
          </div>
        </section>
      );
    }}

    if (LAYOUT === "notebook") {{
      return (
        <section className="notebook-shell">
          {{heroNode}}
          <div className="notebook-top">
            <div className="notebook-left">
              {{primaryNode}}
              {{referenceNode}}
            </div>
            <div className="notebook-right">
              {{workspaceNode}}
              {{featureNode}}
            </div>
          </div>
          <div className="notebook-bottom">
            {{collectionNode}}
            {{statsNode}}
          </div>
        </section>
      );
    }}

    return (
      <>
        {{heroNode}}
        {{statsNode}}
        <section className="content-grid">
          {{workspaceNode}}
          <div className="stack">
            {{primaryNode}}
            {{referenceNode}}
            {{featureNode}}
          </div>
        </section>
        {{collectionNode}}
      </>
    );
  }}

  return (
    <main className={{`page-shell layout-${{layoutClass}} domain-${{DOMAIN_CLASS}}`}}>
      {{renderLayout()}}
    </main>
    );
}}
"""


def _build_fallback_scene_svg(seed: dict[str, object]) -> str:
    palette = dict(seed["palette"])
    title = _svg_text(str(seed["title"]))
    tagline = _svg_text(str(seed["tagline"]))
    layout = str(seed.get("layout_archetype") or "lab")
    objects = list(seed.get("reference_objects") or [])[:3]
    labels = [_svg_text(str(item)) for item in objects] or ["signal", "artifact", "result"]
    while len(labels) < 3:
        labels.append(labels[-1])

    if layout == "storyboard":
        cards = "".join(
            [
                f'<g transform="translate({80 + index * 210} {160 + (index % 2) * 22}) rotate({-6 + index * 6})">'
                f'<rect width="220" height="280" rx="26" fill="rgba(255,255,255,0.82)" stroke="{palette["border"]}"/>'
                f'<rect x="20" y="22" width="180" height="150" rx="18" fill="{palette["accent"]}" opacity="0.22"/>'
                f'<rect x="20" y="190" width="130" height="12" rx="6" fill="{palette["primary"]}" opacity="0.86"/>'
                f'<rect x="20" y="214" width="168" height="10" rx="5" fill="{palette["foreground"]}" opacity="0.18"/>'
                f'<text x="20" y="252" font-size="20" fill="{palette["foreground"]}" font-family="Arial, sans-serif">{labels[index]}</text>'
                "</g>"
                for index in range(3)
            ]
        )
        inner = cards
    elif layout == "atlas":
        inner = "".join(
            [
                f'<rect x="80" y="120" width="240" height="180" rx="28" fill="rgba(255,255,255,0.82)" stroke="{palette["border"]}"/>',
                f'<rect x="360" y="96" width="300" height="220" rx="32" fill="rgba(255,255,255,0.86)" stroke="{palette["border"]}"/>',
                f'<rect x="700" y="148" width="180" height="180" rx="26" fill="rgba(255,255,255,0.78)" stroke="{palette["border"]}"/>',
                f'<path d="M200 300 C 280 360, 360 360, 460 250 S 660 120, 780 210" stroke="{palette["primary"]}" stroke-width="14" stroke-linecap="round" fill="none" opacity="0.88"/>',
                f'<circle cx="200" cy="300" r="18" fill="{palette["accent"]}"/>',
                f'<circle cx="460" cy="250" r="18" fill="{palette["accent"]}"/>',
                f'<circle cx="780" cy="210" r="18" fill="{palette["accent"]}"/>',
                f'<text x="110" y="174" font-size="22" fill="{palette["foreground"]}">{labels[0]}</text>',
                f'<text x="390" y="150" font-size="22" fill="{palette["foreground"]}">{labels[1]}</text>',
                f'<text x="725" y="204" font-size="22" fill="{palette["foreground"]}">{labels[2]}</text>',
            ]
        )
    elif layout == "studio":
        inner = "".join(
            [
                f'<rect x="86" y="88" width="760" height="500" rx="24" fill="rgba(255,255,255,0.86)" stroke="{palette["border"]}"/>',
                "".join(
                    f'<line x1="120" y1="{160 + row * 52}" x2="800" y2="{160 + row * 52}" stroke="{palette["border"]}" stroke-width="2" opacity="0.8"/>'
                    for row in range(7)
                ),
                "".join(
                    f'<rect x="{140 + index * 190}" y="120" width="150" height="72" rx="18" fill="{palette["accent"]}" opacity="0.22"/>'
                    f'<text x="{158 + index * 190}" y="164" font-size="20" fill="{palette["foreground"]}">{labels[index]}</text>'
                    for index in range(3)
                ),
                f'<rect x="170" y="264" width="180" height="108" rx="18" fill="{palette["primary"]}" opacity="0.14"/>',
                f'<rect x="404" y="312" width="204" height="108" rx="18" fill="{palette["primary"]}" opacity="0.14"/>',
                f'<rect x="648" y="232" width="126" height="156" rx="18" fill="{palette["accent"]}" opacity="0.18"/>',
            ]
        )
    elif layout == "notebook":
        inner = "".join(
            [
                f'<rect x="92" y="92" width="736" height="490" rx="34" fill="rgba(255,251,247,0.92)" stroke="{palette["border"]}" stroke-dasharray="10 8"/>',
                "".join(
                    f'<line x1="132" y1="{160 + row * 50}" x2="792" y2="{160 + row * 50}" stroke="{palette["border"]}" stroke-width="2" opacity="0.8"/>'
                    for row in range(7)
                ),
                f'<path d="M180 110 L320 110 L360 150 L220 150 Z" fill="{palette["accent"]}" opacity="0.26"/>',
                f'<text x="220" y="140" font-size="22" fill="{palette["foreground"]}">{labels[0]}</text>',
                f'<rect x="490" y="128" width="210" height="120" rx="20" fill="{palette["primary"]}" opacity="0.16"/>',
                f'<text x="520" y="196" font-size="22" fill="{palette["foreground"]}">{labels[1]}</text>',
                f'<rect x="212" y="334" width="420" height="140" rx="22" fill="rgba(255,255,255,0.64)" stroke="{palette["border"]}"/>',
                f'<text x="250" y="412" font-size="26" fill="{palette["foreground"]}">{labels[2]}</text>',
            ]
        )
    else:
        inner = "".join(
            [
                f'<rect x="96" y="104" width="720" height="460" rx="36" fill="rgba(255,255,255,0.84)" stroke="{palette["border"]}"/>',
                f'<circle cx="220" cy="220" r="80" fill="{palette["accent"]}" opacity="0.24"/>',
                f'<circle cx="690" cy="260" r="110" fill="{palette["primary"]}" opacity="0.16"/>',
                f'<text x="172" y="232" font-size="22" fill="{palette["foreground"]}">{labels[0]}</text>',
                f'<text x="558" y="268" font-size="22" fill="{palette["foreground"]}">{labels[1]}</text>',
                f'<rect x="250" y="380" width="400" height="90" rx="22" fill="rgba(255,255,255,0.68)" stroke="{palette["border"]}"/>',
                f'<text x="310" y="435" font-size="24" fill="{palette["foreground"]}">{labels[2]}</text>',
            ]
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 640" fill="none">'
        f'<defs><linearGradient id="hero-gradient" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0%" stop-color="{palette["background"]}"/>'
        f'<stop offset="100%" stop-color="{palette["card"]}"/>'
        f"</linearGradient></defs>"
        f'<rect width="960" height="640" fill="url(#hero-gradient)"/>'
        f'<circle cx="860" cy="70" r="180" fill="{palette["accent"]}" opacity="0.16"/>'
        f'<circle cx="120" cy="560" r="160" fill="{palette["primary"]}" opacity="0.14"/>'
        f"{inner}"
        f'<text x="96" y="66" font-size="18" letter-spacing="3" fill="{palette["primary"]}" font-family="Arial, sans-serif">{title}</text>'
        f'<text x="96" y="604" font-size="20" fill="{palette["foreground"]}" opacity="0.72" font-family="Arial, sans-serif">{tagline[:84]}</text>'
        "</svg>"
    )


def _build_fallback_thumb_svg(seed: dict[str, object], index: int) -> str:
    palette = dict(seed["palette"])
    items = list(seed.get("sample_seed_data") or [])
    objects = list(seed.get("reference_objects") or [])
    label = _svg_text(str(items[index % max(len(items), 1)] if items else f"Frame {index + 1}"))
    sublabel = _svg_text(str(objects[index % max(len(objects), 1)] if objects else seed.get("title", "Artifact")))
    accent = palette["accent"]
    primary = palette["primary"]
    border = palette["border"]
    foreground = palette["foreground"]
    background = palette["background"]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 480" fill="none">'
        f'<rect width="640" height="480" rx="40" fill="{background}"/>'
        f'<rect x="34" y="34" width="572" height="412" rx="30" fill="rgba(255,255,255,0.78)" stroke="{border}"/>'
        f'<rect x="64" y="66" width="512" height="224" rx="24" fill="{accent}" opacity="0.24"/>'
        f'<path d="M84 242 C 160 180, 248 310, 336 224 S 486 176, 552 246" stroke="{primary}" stroke-width="16" stroke-linecap="round" fill="none" opacity="0.8"/>'
        f'<rect x="64" y="324" width="222" height="18" rx="9" fill="{primary}" opacity="0.84"/>'
        f'<rect x="64" y="358" width="314" height="14" rx="7" fill="{foreground}" opacity="0.18"/>'
        f'<text x="64" y="404" font-size="28" fill="{foreground}" font-family="Arial, sans-serif">{label}</text>'
        f'<text x="64" y="434" font-size="18" fill="{foreground}" opacity="0.68" font-family="Arial, sans-serif">{sublabel}</text>'
        "</svg>"
    )


def _svg_text(value: str) -> str:
    return html_escape(str(value or ""), quote=False)


def _build_fallback_globals_css(seed: dict[str, object], palette: dict[str, str]) -> str:
    background_css = str(palette["background"])
    foreground_css = str(palette["foreground"])
    primary_css = str(palette["primary"])
    accent_css = str(palette["accent"])
    card_css = str(palette["card"])
    muted_css = str(palette["muted"])
    border_css = str(palette["border"])
    font_css = str(palette["font"])

    return (
        ":root {\n"
        f"  --background: {background_css};\n"
        f"  --foreground: {foreground_css};\n"
        f"  --primary: {primary_css};\n"
        f"  --accent: {accent_css};\n"
        f"  --card: {card_css};\n"
        f"  --muted: {muted_css};\n"
        f"  --border: {border_css};\n"
        "}\n\n"
        "* { box-sizing: border-box; }\n"
        "html, body { margin: 0; padding: 0; min-height: 100%; }\n"
        "body {\n"
        "  background:\n"
        "    radial-gradient(circle at top left, rgba(217, 140, 63, 0.24), transparent 28%),\n"
        "    radial-gradient(circle at top right, rgba(15, 95, 82, 0.16), transparent 24%),\n"
        "    linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0)),\n"
        "    var(--background);\n"
        "  color: var(--foreground);\n"
        f"  font-family: {font_css};\n"
        "}\n"
        "a { color: inherit; text-decoration: none; }\n"
        "button, textarea { font: inherit; }\n"
        ".page-shell { max-width: 1280px; margin: 0 auto; padding: 28px 18px 88px; display: grid; gap: 22px; }\n"
        ".hero, .workspace-panel, .insight-panel, .status-panel, .feature-panel, .collection-panel, .saved-card, .stats-strip, .reference-shelf {\n"
        "  background: var(--card);\n"
        "  border: 1px solid var(--border);\n"
        "  border-radius: 26px;\n"
        "  box-shadow: 0 26px 80px rgba(20, 16, 12, 0.08);\n"
        "}\n"
        ".hero, .workspace-panel, .insight-panel, .status-panel, .feature-panel, .collection-panel, .reference-shelf { padding: 24px; }\n"
        ".hero { overflow: hidden; position: relative; display: grid; grid-template-columns: minmax(0, 1.02fr) minmax(280px, 0.98fr); gap: 22px; align-items: stretch; }\n"
        ".hero-copy { display: grid; gap: 16px; align-content: start; }\n"
        ".hero-visual-frame { min-height: 320px; border-radius: 22px; overflow: hidden; border: 1px solid var(--border); background: rgba(255,255,255,0.42); box-shadow: inset 0 1px 0 rgba(255,255,255,0.4); }\n"
        ".hero-visual { width: 100%; height: 100%; display: block; object-fit: cover; }\n"
        ".hero::after { content: ''; position: absolute; inset: auto -10% -35% auto; width: 260px; height: 260px; border-radius: 50%; background: rgba(255,255,255,0.18); filter: blur(8px); }\n"
        ".hero h1, .section-heading h2 { margin: 0; font-size: clamp(2.3rem, 5vw, 4.8rem); line-height: 0.92; letter-spacing: -0.04em; }\n"
        ".hero p, .section-heading p, .status-panel p, .item-card p { color: var(--muted); }\n"
        ".eyebrow { display: inline-flex; padding: 8px 12px; border-radius: 999px; background: rgba(255,255,255,0.52); color: var(--primary); font-size: 0.78rem; letter-spacing: 0.14em; text-transform: uppercase; }\n"
        ".hero-proof-list { list-style: none; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: 10px; }\n"
        ".proof-pill { display: inline-flex; padding: 9px 12px; border-radius: 999px; background: rgba(255,255,255,0.68); border: 1px solid var(--border); color: var(--foreground); font-size: 0.92rem; }\n"
        ".feature-list, .insight-list, .saved-card ul { padding-left: 18px; color: var(--muted); }\n"
        ".stats-strip { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; padding: 14px; }\n"
        ".stat-chip { padding: 14px 16px; border-radius: 18px; background: rgba(255,255,255,0.58); border: 1px solid var(--border); }\n"
        ".stat-chip strong { display: block; margin-top: 6px; font-size: 1.45rem; }\n"
        ".content-grid, .stack, .storyboard-main, .storyboard-side, .console-operator-lane, .console-support-lane, .studio-left, .studio-right, .atlas-side-stack, .atlas-primary-stack, .atlas-secondary-stack, .notebook-left, .notebook-right, .creator-workbench, .creator-primary-rail, .creator-side-rail, .creator-library-rail, .creator-collection-rail, .creator-proof-rail, .travel-brief-column, .travel-result-column, .travel-proof-column, .meal-proof-stack, .meal-planner-column, .meal-reference-column { display: grid; gap: 20px; }\n"
        ".content-grid { grid-template-columns: 1.05fr 0.95fr; }\n"
        ".creator-shell, .travel-shell, .meal-shell { display: grid; gap: 22px; }\n"
        ".creator-topline { display: grid; grid-template-columns: 0.76fr 1.24fr; gap: 20px; align-items: start; }\n"
        ".creator-workbench .stats-strip { grid-template-columns: 1fr; }\n"
        ".creator-editorial-stage { display: grid; grid-template-columns: 0.7fr 1.14fr 0.74fr; gap: 20px; align-items: start; }\n"
        ".creator-bottomline { display: grid; grid-template-columns: 1.08fr 0.92fr; gap: 20px; align-items: start; }\n"
        ".travel-ribbon .reference-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }\n"
        ".travel-planner-grid { display: grid; grid-template-columns: 0.86fr 1.12fr 0.82fr; gap: 20px; align-items: start; }\n"
        ".travel-result-column .collection-panel { min-height: 100%; }\n"
        ".meal-top-row { display: grid; grid-template-columns: 1.12fr 0.88fr; gap: 20px; align-items: start; }\n"
        ".meal-main-grid { display: grid; grid-template-columns: 0.98fr 1.02fr; gap: 20px; align-items: start; }\n"
        ".meal-bottom-row { display: grid; grid-template-columns: 1.06fr 0.94fr; gap: 20px; align-items: start; }\n"
        ".workspace-panel textarea { width: 100%; min-height: 140px; margin-top: 12px; border-radius: 18px; border: 1px solid var(--border); padding: 16px; background: rgba(255,255,255,0.74); color: var(--foreground); }\n"
        ".controls { display: grid; gap: 12px; }\n"
        ".button-row { display: flex; gap: 12px; align-items: center; }\n"
        ".primary-button { border: none; border-radius: 999px; background: var(--primary); color: white; padding: 14px 22px; cursor: pointer; }\n"
        ".primary-button:disabled { opacity: 0.72; cursor: progress; }\n"
        ".feature-chips, .object-strip { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px; }\n"
        ".feature-chip, .saved-score, .object-pill { display: inline-flex; padding: 8px 12px; border-radius: 999px; background: rgba(217,140,63,0.14); color: var(--accent); }\n"
        ".score-pill { display: inline-flex; padding: 10px 14px; border-radius: 999px; background: rgba(15,95,82,0.1); color: var(--primary); font-weight: 600; }\n"
        ".item-card, .reference-card { margin-top: 12px; padding: 16px; border-radius: 18px; background: rgba(255,255,255,0.72); border: 1px solid var(--border); }\n"
        ".feature-columns { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-top: 14px; }\n"
        ".feature-group { padding: 14px; border-radius: 18px; background: rgba(255,255,255,0.58); border: 1px solid var(--border); }\n"
        ".feature-group h3 { margin: 0 0 12px; font-size: 0.98rem; letter-spacing: 0.02em; }\n"
        ".saved-grid, .reference-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px; margin-top: 16px; }\n"
        ".saved-card { padding: 18px; }\n"
        ".reference-card { display: grid; gap: 10px; align-content: start; }\n"
        ".reference-thumb { width: 100%; aspect-ratio: 1.24 / 1; border-radius: 16px; object-fit: cover; border: 1px solid var(--border); background: rgba(255,255,255,0.5); }\n"
        ".reference-card strong { display: block; font-size: 1.06rem; }\n"
        ".reference-card span { display: inline-flex; margin-top: 8px; color: var(--muted); }\n"
        ".storyboard-stage { display: grid; grid-template-columns: 1.14fr 0.86fr; gap: 20px; align-items: start; }\n"
        ".console-shell, .studio-shell, .atlas-shell, .notebook-shell { display: grid; gap: 20px; }\n"
        ".console-top { display: grid; grid-template-columns: 0.96fr 1.04fr; gap: 20px; align-items: stretch; }\n"
        ".console-grid { display: grid; grid-template-columns: 0.88fr 1.16fr 0.88fr; gap: 20px; align-items: start; }\n"
        ".console-timeline-lane { min-height: 100%; }\n"
        ".studio-top { display: grid; grid-template-columns: 1.02fr 0.98fr; gap: 20px; align-items: start; }\n"
        ".studio-bottom { display: grid; grid-template-columns: 0.98fr 1.02fr; gap: 20px; align-items: start; }\n"
        ".atlas-hero-row { display: grid; grid-template-columns: 1.12fr 0.88fr; gap: 20px; align-items: start; }\n"
        ".atlas-main-row { display: grid; grid-template-columns: 1.02fr 0.98fr; gap: 20px; align-items: start; }\n"
        ".notebook-top { display: grid; grid-template-columns: 0.98fr 1.02fr; gap: 20px; align-items: start; }\n"
        ".notebook-bottom { display: grid; grid-template-columns: 1.08fr 0.92fr; gap: 20px; align-items: start; }\n"
        ".layout-storyboard .hero { background: linear-gradient(135deg, rgba(255,255,255,0.9), rgba(243, 217, 179, 0.68)); }\n"
        ".layout-storyboard .reference-card:nth-child(odd) { transform: rotate(-1.2deg); }\n"
        ".layout-storyboard .reference-card:nth-child(even) { transform: rotate(1deg); }\n"
        ".domain-creator-batch-studio .hero { background: linear-gradient(135deg, rgba(255,247,243,0.95), rgba(255,107,107,0.14)); }\n"
        ".domain-creator-batch-studio { background: linear-gradient(180deg, #f7f2ec 0%, #f3ece5 52%, #f8f5f0 100%); }\n"
        ".domain-creator-batch-studio .hero { background: linear-gradient(145deg, rgba(255,248,244,0.98), rgba(255,107,107,0.12)); border-radius: 40px 14px 32px 14px; }\n"
        ".domain-creator-batch-studio .hero-visual-frame { border-radius: 32px 32px 14px 14px; background: linear-gradient(180deg, rgba(255,255,255,0.42), rgba(255,107,107,0.08)); }\n"
        ".domain-creator-batch-studio .workspace-panel, .domain-creator-batch-studio .feature-panel, .domain-creator-batch-studio .collection-panel { border-radius: 14px; box-shadow: 0 16px 36px rgba(29,24,32,0.08); }\n"
        ".domain-creator-batch-studio .insight-panel, .domain-creator-batch-studio .status-panel { border-radius: 40px 14px 32px 14px; }\n"
        ".domain-creator-batch-studio .reference-card:nth-child(3n+1) { transform: translateY(-10px) rotate(-1.4deg); }\n"
        ".domain-creator-batch-studio .reference-card:nth-child(3n+2) { transform: translateY(6px) rotate(1.1deg); }\n"
        ".domain-creator-batch-studio .feature-group { border-radius: 26px; background: #1a1330; color: rgba(255,255,255,0.88); }\n"
        ".domain-creator-batch-studio .feature-group h3 { color: #ffb4a2; }\n"
        ".domain-creator-batch-studio .feature-list { color: rgba(255,255,255,0.76); }\n"
        ".domain-creator-batch-studio .proof-pill { background: rgba(255,107,107,0.12); color: #9f2239; }\n"
        ".domain-creator-batch-studio .creator-topline .hero { min-height: 100%; }\n"
        ".domain-creator-batch-studio .creator-primary-rail .insight-panel, .domain-creator-batch-studio .creator-primary-rail .status-panel { min-height: 100%; }\n"
        ".domain-creator-batch-studio .stats-strip { display: flex; flex-wrap: wrap; gap: 10px; padding: 0; background: transparent; border: none; box-shadow: none; }\n"
        ".domain-creator-batch-studio .stat-chip { min-width: 150px; border-radius: 999px; background: #1a1330; color: white; border: none; }\n"
        ".domain-creator-batch-studio .stat-chip .eyebrow { background: rgba(255,255,255,0.14); color: #ffb4a2; }\n"
        ".domain-creator-batch-studio .creator-bottomline { align-items: stretch; }\n"
        ".domain-creator-batch-studio .creator-proof-rail .reference-grid { grid-template-columns: 1fr; }\n"
        ".domain-weekender-route-postcards .hero { background: linear-gradient(145deg, rgba(255,250,243,0.96), rgba(240,138,60,0.18)); }\n"
        ".domain-weekender-route-postcards { background: linear-gradient(180deg, #f4e6d5 0%, #f8efe4 50%, #f6ecdf 100%); }\n"
        ".domain-weekender-route-postcards .hero { border-radius: 18px 18px 44px 18px; box-shadow: 0 22px 50px rgba(43,28,20,0.1); }\n"
        ".domain-weekender-route-postcards .hero-visual-frame { border-radius: 18px; box-shadow: 0 18px 40px rgba(25,20,18,0.15); }\n"
        ".domain-weekender-route-postcards .workspace-panel, .domain-weekender-route-postcards .feature-panel, .domain-weekender-route-postcards .collection-panel { border-radius: 22px; }\n"
        ".domain-weekender-route-postcards .reference-card { border-radius: 12px; box-shadow: 0 12px 26px rgba(25,20,18,0.1); }\n"
        ".domain-weekender-route-postcards .reference-card:nth-child(odd) { transform: rotate(-2.2deg); }\n"
        ".domain-weekender-route-postcards .reference-card:nth-child(even) { transform: rotate(1.8deg); }\n"
        ".domain-weekender-route-postcards .proof-pill { background: rgba(240,138,60,0.14); color: #9c4b14; }\n"
        ".domain-weekender-route-postcards .travel-ribbon { margin-top: -6px; }\n"
        ".domain-weekender-route-postcards .travel-proof-column .stats-strip { grid-template-columns: 1fr; background: rgba(255,248,240,0.84); border-radius: 24px; }\n"
        ".domain-weekender-route-postcards .travel-proof-column .stat-chip { border-radius: 16px; }\n"
        ".domain-weekender-route-postcards .travel-ribbon .reference-card { min-height: 238px; }\n"
        ".domain-meal-prep-atlas .hero { background: radial-gradient(circle at top right, rgba(73,123,43,0.15), transparent 34%), rgba(255,255,255,0.88); }\n"
        ".domain-meal-prep-atlas .hero-visual-frame { border-radius: 30px; background: linear-gradient(180deg, rgba(255,255,255,0.52), rgba(73,123,43,0.08)); }\n"
        ".domain-meal-prep-atlas .feature-group { background: rgba(255,255,255,0.76); }\n"
        ".domain-meal-prep-atlas .reference-card { border-radius: 28px; }\n"
        ".domain-meal-prep-atlas .proof-pill { background: rgba(73,123,43,0.12); color: #2f6d1e; }\n"
        ".domain-meal-prep-atlas .meal-reference-column .reference-grid { grid-template-columns: 1fr; }\n"
        ".domain-meal-prep-atlas .meal-proof-stack .stats-strip { grid-template-columns: 1fr; }\n"
        ".layout-operations-console .hero,\n"
        ".layout-operations-console .workspace-panel,\n"
        ".layout-operations-console .insight-panel,\n"
        ".layout-operations-console .status-panel,\n"
        ".layout-operations-console .feature-panel,\n"
        ".layout-operations-console .collection-panel,\n"
        ".layout-operations-console .reference-shelf,\n"
        ".layout-operations-console .stats-strip { background: rgba(11, 16, 32, 0.78); backdrop-filter: blur(20px); }\n"
        ".layout-operations-console .hero { background-image: linear-gradient(135deg, rgba(96,245,192,0.12), rgba(255,123,84,0.12)); }\n"
        ".layout-operations-console .reference-card { border-left: 4px solid var(--accent); }\n"
        ".layout-operations-console .eyebrow { background: rgba(96,245,192,0.1); }\n"
        ".layout-studio .hero { background: linear-gradient(135deg, rgba(255,255,255,0.92), rgba(205,221,255,0.76)); }\n"
        ".layout-studio .workspace-panel,\n"
        ".layout-studio .reference-shelf { background-image: linear-gradient(180deg, rgba(255,255,255,0.45), rgba(255,255,255,0.2)); }\n"
        ".layout-studio .reference-card { box-shadow: 0 10px 24px rgba(54, 87, 255, 0.1); }\n"
        ".layout-atlas .hero { background: radial-gradient(circle at top right, rgba(242,160,61,0.24), transparent 32%), rgba(255,255,255,0.62); }\n"
        ".layout-atlas .stats-strip { grid-template-columns: 1fr; }\n"
        ".layout-atlas .reference-card strong { font-size: 1.2rem; }\n"
        ".layout-notebook .hero { background: linear-gradient(180deg, rgba(255,255,255,0.9), rgba(234,222,209,0.78)); }\n"
        ".layout-notebook .reference-shelf, .layout-notebook .workspace-panel { border-style: dashed; }\n"
        ".layout-notebook .saved-card { background: rgba(255, 248, 241, 0.82); }\n"
        "@media (max-width: 1080px) {\n"
        "  .hero,\n"
        "  .storyboard-stage,\n"
        "  .console-top,\n"
        "  .console-grid,\n"
        "  .creator-hero-row,\n"
        "  .creator-topline,\n"
        "  .creator-editorial-stage,\n"
        "  .creator-bottomline,\n"
        "  .travel-planner-grid,\n"
        "  .meal-top-row,\n"
        "  .meal-main-grid,\n"
        "  .meal-bottom-row,\n"
        "  .studio-top,\n"
        "  .studio-bottom,\n"
        "  .atlas-hero-row,\n"
        "  .atlas-main-row,\n"
        "  .notebook-top,\n"
        "  .notebook-bottom,\n"
        "  .content-grid {\n"
        "    grid-template-columns: 1fr;\n"
        "  }\n"
        "}\n"
        "@media (max-width: 720px) {\n"
        "  .page-shell { padding: 18px 14px 72px; }\n"
        "  .stats-strip { grid-template-columns: 1fr; }\n"
        "  .feature-columns { grid-template-columns: 1fr; }\n"
        "  .hero, .workspace-panel, .insight-panel, .status-panel, .feature-panel, .collection-panel, .reference-shelf { padding: 18px; }\n"
        "  .hero h1, .section-heading h2 { font-size: clamp(2rem, 14vw, 3.2rem); }\n"
        "}\n"
    )


def _build_fallback_backend_bundle(context: str) -> dict[str, str]:
    seed = _extract_template_seed(context)
    title_json = json.dumps(str(seed["title"]))
    tagline_json = json.dumps(str(seed["tagline"]))
    features_json = json.dumps(list(seed["features"]))
    proof_points_json = json.dumps(list(seed["proof_points"]))
    reference_objects_json = json.dumps(list(seed["reference_objects"]))
    sample_seed_data_json = json.dumps(list(seed["sample_seed_data"]))
    surface_labels_json = json.dumps(seed["surface_labels"])
    collection_title_json = json.dumps(str(seed["collection_title"]))

    return _normalize_backend_files(
        {
            _FALLBACK_BACKEND_MARKER_FILE: json.dumps(
                {"kind": "backend", "reason": "deterministic_fallback"}, indent=2
            ),
            "requirements.txt": "fastapi\nuvicorn[standard]\npydantic\n",
            "main.py": """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import router

app = FastAPI(title="Generated Showcase API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
app.include_router(router, prefix="/api")
""",
            "models.py": """from pydantic import BaseModel


class PlanRequest(BaseModel):
    query: str = ""
    preferences: str = ""


class InsightRequest(BaseModel):
    selection: str = ""
    context: str = ""
""",
            "routes.py": """from fastapi import APIRouter

from ai_service import build_insights, build_plan
from models import InsightRequest, PlanRequest

router = APIRouter()


@router.get("/health")
async def health():
    return {"ok": True}


@router.post("/plan")
async def create_plan(payload: PlanRequest):
    return build_plan(payload.query, payload.preferences)


@router.post("/insights")
async def create_insights(payload: InsightRequest):
    return build_insights(payload.selection, payload.context)
""",
            "ai_service.py": f"""APP_NAME = {title_json}
APP_TAGLINE = {tagline_json}
KEY_FEATURES = {features_json}
PROOF_POINTS = {proof_points_json}
REFERENCE_OBJECTS = {reference_objects_json}
SAMPLE_SEED_DATA = {sample_seed_data_json}
SURFACE_LABELS = {surface_labels_json}
COLLECTION_TITLE = {collection_title_json}


def _artifact_label(items, index, fallback):
    if index < len(items) and str(items[index]).strip():
        return str(items[index]).strip()
    return fallback


def _sentence_case(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text[0].upper() + text[1:]


def build_plan(query: str, preferences: str) -> dict:
    subject = (query or APP_TAGLINE).strip() or APP_NAME
    guidance = (preferences or "Keep the result practical, saveable, and ready to use immediately.").strip()
    result_labels = SAMPLE_SEED_DATA or PROOF_POINTS or KEY_FEATURES
    object_labels = REFERENCE_OBJECTS or KEY_FEATURES
    items = []
    for index in range(3):
        object_label = _artifact_label(object_labels, index, f"Step {{index + 1}}")
        result_label = _artifact_label(result_labels, index, _artifact_label(PROOF_POINTS, index, "usable output"))
        partner_label = _artifact_label(object_labels, min(index + 1, len(object_labels) - 1), SURFACE_LABELS.get("collection", "saved result"))
        items.append(
            {{
                "title": _sentence_case(object_label),
                "detail": f"Shape {{result_label.lower()}} through {{object_label.lower()}}, keep {{partner_label.lower()}} visible, and follow: {{guidance}}.",
                "score": min(96, 78 + index * 5),
            }}
        )
    summary_result = _artifact_label(result_labels, 0, "usable output")
    summary_objects = ", ".join(label.lower() for label in object_labels[:2])
    return {{
        "summary": f"{{APP_NAME}} turned '{{subject}}' into {{summary_result.lower()}} with {{summary_objects}} and a reusable {{SURFACE_LABELS.get('collection', 'saved result').lower()}}.",
        "score": 88,
        "items": items,
    }}


def build_insights(selection: str, context: str) -> dict:
    focus = (selection or _artifact_label(REFERENCE_OBJECTS, 0, APP_NAME)).strip()
    base_context = (context or APP_TAGLINE).strip()
    collection_label = SURFACE_LABELS.get("collection", "saved result")
    support_label = SURFACE_LABELS.get("support", "support rail")
    return {{
        "insights": [
            f"Lead with {{focus}} so the first screen proves {{_artifact_label(PROOF_POINTS, 0, 'usable value').lower()}} immediately.",
            f"Keep {{support_label.lower()}} and {{collection_label.lower()}} visible so the workflow reads like a dedicated product, not a generic tool.",
        ],
        "next_actions": [
            f"Save the strongest {{collection_label.lower()}} after each run.",
            f"Use {{base_context}} to refine the next {{_artifact_label(REFERENCE_OBJECTS, 1, 'artifact').lower()}}.",
        ],
        "highlights": PROOF_POINTS[:3] or SAMPLE_SEED_DATA[:3],
    }}
""",
        }
    )


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _seed_text_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    return _unique_strings([text for item in value if (text := _stringify_seed_item(item))])


def _stringify_seed_item(item: object) -> str:
    if item is None:
        return ""

    if isinstance(item, str):
        return item.strip()

    if isinstance(item, (int, float, bool)):
        return str(item).strip()

    if not isinstance(item, dict):
        return str(item).strip()

    trip_fields = [
        _dict_text(item, "city"),
        _dict_text(item, "vibe"),
        _quantified_label(item.get("days"), "day"),
        _currency_label(item.get("budget_per_day")),
    ]
    trip_summary = " · ".join(part for part in trip_fields if part)
    if trip_summary:
        return trip_summary

    for primary_key, secondary_keys in (
        ("name", ("description", "detail", "summary")),
        ("title", ("description", "detail", "summary")),
        ("label", ("description", "detail", "summary")),
        ("neighborhood", ("highlight", "rain_alt", "detail")),
        ("surface", ("description", "detail")),
        ("object", ("description", "detail")),
    ):
        primary = _dict_text(item, primary_key)
        if not primary:
            continue
        secondary = next((_dict_text(item, key) for key in secondary_keys if _dict_text(item, key)), "")
        if secondary:
            return f"{primary} - {secondary}"
        return primary

    scalar_pairs: list[str] = []
    for key, value in item.items():
        if isinstance(value, (list, dict)) or value is None:
            continue
        scalar_text = str(value).strip()
        if not scalar_text:
            continue
        scalar_pairs.append(f"{key.replace('_', ' ')}: {scalar_text}")
        if len(scalar_pairs) == 3:
            break
    return " · ".join(scalar_pairs)


def _dict_text(item: dict[object, object], key: str) -> str:
    value = item.get(key)
    if value is None:
        return ""
    return str(value).strip()


def _quantified_label(value: object, singular: str) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, (int, float)):
        amount = int(value) if isinstance(value, float) and value.is_integer() else value
        return f"{amount} {singular}{'' if amount == 1 else 's'}"
    text = str(value).strip()
    if not text:
        return ""
    if text.lower().endswith(singular) or text.lower().endswith(f"{singular}s"):
        return text
    return f"{text} {singular}s"


def _currency_label(value: object) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, (int, float)):
        amount = int(value) if isinstance(value, float) and value.is_integer() else value
        return f"${amount}/day"
    text = str(value).strip()
    if not text:
        return ""
    if text.startswith("$") or "/day" in text.lower():
        return text
    return f"{text}/day"


def _normalize_files_dict(files: object) -> dict[str, str]:
    if not isinstance(files, dict):
        return {}

    normalized: dict[str, str] = {}
    for key, value in files.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, str):
            flattened = _flatten_objectified_code_string(key, value)
            normalized[key] = flattened if flattened is not None else value
        elif isinstance(value, dict):
            flattened = _flatten_structured_file_body(key, value)
            normalized[key] = flattened if flattened is not None else json.dumps(value, indent=2, ensure_ascii=False)
        elif isinstance(value, list):
            flattened = _flatten_structured_file_list(key, value)
            normalized[key] = flattened if flattened is not None else json.dumps(value, indent=2, ensure_ascii=False)
        elif isinstance(value, (int, float, bool)):
            normalized[key] = str(value)
    return normalized


def _flatten_structured_file_body(path: str, value: dict[object, object]) -> str | None:
    if not path.endswith(_STRUCTURED_CODE_FILE_SUFFIXES):
        return None
    if not value:
        return None

    parts: list[str] = []
    for segment in value.values():
        if not isinstance(segment, str):
            return None
        stripped = segment.strip()
        if stripped:
            parts.append(stripped)

    if not parts:
        return None

    return "\n\n".join(parts) + "\n"


def _flatten_structured_file_list(path: str, value: list[object]) -> str | None:
    if not path.endswith(_STRUCTURED_CODE_FILE_SUFFIXES):
        return None
    if not value:
        return None

    parts: list[str] = []
    for segment in value:
        if not isinstance(segment, str):
            return None
        stripped = segment.strip()
        if stripped:
            parts.append(stripped)

    if not parts:
        return None

    return "\n\n".join(parts) + "\n"


def _flatten_objectified_code_string(path: str, raw: str) -> str | None:
    if not path.endswith(_STRUCTURED_CODE_FILE_SUFFIXES):
        return None

    candidate = raw.strip()
    if not candidate:
        return None

    if candidate.startswith('"use client";'):
        candidate = candidate[len('"use client";') :].lstrip()

    if not candidate.startswith("{"):
        return None

    parts = re.findall(r'"[^"]+"\s*:\s*"([\s\S]*?)"(?=,\s*"[^"]+"\s*:|\s*}\s*$)', candidate, re.S)
    if not parts:
        return None

    flattened_parts: list[str] = []
    for part in parts:
        decoded = bytes(part, "utf-8").decode("unicode_escape").strip()
        if decoded:
            flattened_parts.append(decoded)

    if not flattened_parts:
        return None

    return "\n\n".join(flattened_parts) + "\n"


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
    normalized = _normalize_backend_response_shapes(normalized)
    normalized = _normalize_backend_database_url_guards(normalized)
    normalized = _normalize_backend_auth_scheme_references(normalized)
    normalized = _normalize_backend_flexible_request_fields(normalized)
    normalized = _normalize_backend_ai_fallbacks(normalized)
    normalized = _normalize_backend_async_ai_calls(normalized)
    if normalized:
        normalized.setdefault(".python-version", "3.13\n")
    return normalized


def _normalize_cross_stack(
    frontend_files: dict[str, str], backend_files: dict[str, str]
) -> tuple[dict[str, str], dict[str, str]]:
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


def _normalize_backend_flexible_request_fields(files: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    pattern = re.compile(
        r"^(\s*)(preferences|context)(\s*:\s*)(?:Dict\[[^\]]+\]|List\[[^\]]+\]|list\[[^\]]+\])(\s*=)",
        flags=re.MULTILINE,
    )

    for path, content in files.items():
        updated = content
        if path.endswith(".py") and ("preferences:" in content or "context:" in content):
            updated, replacements = pattern.subn(r"\1\2\3Any\4", updated)
            if replacements:
                typing_import = re.search(r"from typing import ([^\n]+)", updated)
                if typing_import:
                    imported = [part.strip() for part in typing_import.group(1).split(",") if part.strip()]
                    if "Any" not in imported:
                        imported.append("Any")
                        updated = (
                            f"{updated[: typing_import.start()]}"
                            f"from typing import {', '.join(imported)}"
                            f"{updated[typing_import.end() :]}"
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
        if (
            path.endswith(".tsx")
            and not stripped.startswith('"use client"')
            and not stripped.startswith("'use client'")
        ):
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
        if path.endswith(layout_suffixes) and ("export const metadata" in content or "generateMetadata" in content):
            updated = re.sub(r'^\s*"use client";\n+', "", updated, count=1)
        normalized[path] = updated

    return normalized


def _normalize_frontend_react_hook_imports(files: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for path, content in files.items():
        updated = content
        if path.endswith((".ts", ".tsx", ".js", ".jsx")):
            used_symbols = sorted(
                symbol for symbol in _REACT_IMPORTABLE_SYMBOLS if re.search(rf"\b{symbol}\b", updated)
            )
            if used_symbols:
                match = re.search(r'import\s+\{(?P<named>[^}]+)\}\s+from\s+[\'"]react[\'"]\s*;?', updated)
                if match:
                    existing = {part.strip() for part in match.group("named").split(",") if part.strip()}
                    merged = ", ".join(sorted(existing | set(used_symbols)))
                    updated = f'{updated[: match.start()]}import {{ {merged} }} from "react";{updated[match.end() :]}'
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
                return f"import {{ {', '.join(renamed_items)} }} from '@heroicons/react/24/{match.group('variant')}';"

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
                return f"if (!res.ok) {{\n    await throwApiError(res, {json.dumps(fallback)});\n  }}"

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
                    updated = f"{import_block.group(1)}\n{helper}{updated[import_block.end() :]}"
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
        if (
            path.endswith(".tsx")
            and "summarize(" in content
            and "generateTags(" in content
            and "Promise.all([" in content
        ):
            updated = pattern.sub(
                lambda match: (
                    f"const [summaryResult, tagsResult] = await Promise.allSettled([\n"
                    f"        summarize({match.group('arg')}),\n"
                    f"        generateTags({match.group('arg')}),\n"
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
                if (
                    f"export async function {name}(" in updated[: match.start()]
                    and f"{name}(" in updated[: match.start()]
                ):
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
                match.group("from") or match.group("bare") or match.group("dynamic") or match.group("require") or ""
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

    return "module.exports = {\n  reactStrictMode: true,\n};\n"


def _normalize_backend_api_routes(files: dict[str, str]) -> dict[str, str]:
    normalized = dict(files)

    routes_content = normalized.get("routes.py", "")
    if routes_content:
        routes_content = _strip_api_prefix_from_router(routes_content)
        routes_content = _strip_api_prefix_from_route_decorators(routes_content)
        normalized["routes.py"] = routes_content

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
    return f"{content[: match.start()]}{replacement}{content[match.end() :]}"


def _strip_api_prefix_from_route_decorators(content: str) -> str:
    updated = content
    for target in ("router", "app"):
        for method in ("get", "post", "put", "patch", "delete", "options", "head"):
            updated = updated.replace(f'@{target}.{method}("/api/', f'@{target}.{method}("/')
            updated = updated.replace(f"@{target}.{method}('/api/", f"@{target}.{method}('/")
            updated = updated.replace(f'@{target}.{method}("/api")', f'@{target}.{method}("/")')
            updated = updated.replace(f"@{target}.{method}('/api')", f"@{target}.{method}('/')")
    return updated


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


def _normalize_backend_response_shapes(files: dict[str, str]) -> dict[str, str]:
    normalized = dict(files)
    routes_content = normalized.get("routes.py", "")
    if not routes_content:
        return normalized

    updated = routes_content
    updated = updated.replace("items: List[str]", "items: list[dict[str, object]]")
    updated = updated.replace("items: list[str]", "items: list[dict[str, object]]")
    updated = updated.replace("insights: str", "insights: list[str]")
    updated = updated.replace("insights: String", "insights: list[str]")
    updated = updated.replace("items (list of strings)", "items (list of objects with title, detail, score)")
    updated = updated.replace("insights (string)", "insights (list of strings)")
    normalized["routes.py"] = updated
    return normalized


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
            updated = updated.replace(
                'return {"note": "AI service is temporarily unavailable. Please try again later."}',
                'return _coerce_unstructured_payload("AI service fallback")',
            )
            updated = updated.replace(
                "return {'note': 'AI service is temporarily unavailable. Please try again later.'}",
                'return _coerce_unstructured_payload("AI service fallback")',
            )
            updated = re.sub(
                r"fallback\s*=\s*\{[\s\S]*?['\"]summary['\"]\s*:\s*['\"]AI service unavailable['\"][\s\S]*?\}\s*return fallback",
                'return _coerce_unstructured_payload("AI service fallback")',
                updated,
                count=1,
            )
            updated = re.sub(
                r"(result\s*=\s*json\.loads\(json_str\)\s*\n)(\s*)return result\b",
                r"\1\2return _normalize_inference_payload(result)",
                updated,
                count=1,
            )

            if "def _coerce_unstructured_payload" not in updated:
                helper = (
                    "def _coerce_unstructured_payload(raw_text: str) -> dict[str, object]:\n"
                    "    compact = raw_text.strip()\n"
                    '    normalized = compact.replace("\\n", ",")\n'
                    '    tags = [part.strip(" -•\\t") for part in normalized.split(",") if part.strip(" -•\\t")]\n'
                    "    if not tags:\n"
                    '        tags = ["guided plan", "saved output", "shareable insight"]\n'
                    "    headline = tags[0].title()\n"
                    "    items = []\n"
                    "    for index, tag in enumerate(tags[:3], start=1):\n"
                    "        items.append({\n"
                    '            "title": f"Stage {index}: {tag.title()}",\n'
                    '            "detail": f"Use {tag} to move the request toward a demo-ready outcome.",\n'
                    '            "score": min(96, 80 + index * 4),\n'
                    "        })\n"
                    "    highlights = [tag.title() for tag in tags[:3]]\n"
                    "    return {\n"
                    '        "note": "Model returned plain text instead of JSON",\n'
                    '        "raw": compact,\n'
                    '        "text": compact,\n'
                    '        "summary": compact or f"{headline} fallback is ready for review.",\n'
                    '        "tags": tags[:6],\n'
                    '        "items": items,\n'
                    '        "score": 88,\n'
                    '        "insights": [f"Lead with {headline} on the first screen.", "Keep one clear action visible throughout the flow."],\n'
                    '        "next_actions": ["Review the generated plan.", "Save the strongest output for the demo finale."],\n'
                    '        "highlights": highlights,\n'
                    "    }\n"
                )
                helper += (
                    "\n"
                    "def _normalize_inference_payload(payload: object) -> dict[str, object]:\n"
                    "    if not isinstance(payload, dict):\n"
                    "        return _coerce_unstructured_payload(str(payload))\n"
                    "    normalized = dict(payload)\n"
                    '    summary = str(normalized.get("summary") or normalized.get("note") or "AI-generated plan ready")\n'
                    '    raw_items = normalized.get("items")\n'
                    "    items: list[dict[str, object]] = []\n"
                    "    if isinstance(raw_items, list):\n"
                    "        for index, entry in enumerate(raw_items[:3], start=1):\n"
                    "            if isinstance(entry, dict):\n"
                    '                title = str(entry.get("title") or f"Stage {index}")\n'
                    '                detail = str(entry.get("detail") or entry.get("description") or title)\n'
                    '                score = float(entry.get("score") or min(96, 80 + index * 4))\n'
                    "            else:\n"
                    '                label = str(entry).strip() or f"Stage {index}"\n'
                    '                title = f"Stage {index}: {label.title()}"\n'
                    '                detail = f"Use {label} to move the request toward a demo-ready outcome."\n'
                    "                score = float(min(96, 80 + index * 4))\n"
                    '            items.append({"title": title, "detail": detail, "score": score})\n'
                    "    if not items:\n"
                    '        items = _coerce_unstructured_payload(summary).get("items", [])\n'
                    '    raw_insights = normalized.get("insights")\n'
                    "    if isinstance(raw_insights, list):\n"
                    "        insights = [str(entry) for entry in raw_insights if str(entry).strip()]\n"
                    "    elif isinstance(raw_insights, str) and raw_insights.strip():\n"
                    "        insights = [raw_insights.strip()]\n"
                    "    else:\n"
                    "        insights = []\n"
                    '    next_actions = normalized.get("next_actions")\n'
                    "    if isinstance(next_actions, list):\n"
                    "        next_actions = [str(entry) for entry in next_actions if str(entry).strip()]\n"
                    "    else:\n"
                    "        next_actions = []\n"
                    '    highlights = normalized.get("highlights")\n'
                    "    if isinstance(highlights, list):\n"
                    "        highlights = [str(entry) for entry in highlights if str(entry).strip()]\n"
                    "    else:\n"
                    "        highlights = []\n"
                    "    if not insights and not next_actions and not highlights:\n"
                    "        fallback = _coerce_unstructured_payload(summary)\n"
                    '        insights = fallback.get("insights", [])\n'
                    '        next_actions = fallback.get("next_actions", [])\n'
                    '        highlights = fallback.get("highlights", [])\n'
                    "    return {\n"
                    "        **normalized,\n"
                    '        "summary": summary,\n'
                    '        "items": items,\n'
                    '        "score": float(normalized.get("score") or 88),\n'
                    '        "insights": insights,\n'
                    '        "next_actions": next_actions,\n'
                    '        "highlights": highlights,\n'
                    "    }\n"
                )
                marker_match = re.search(r"^async def\s+_?call_inference\b", updated, flags=re.MULTILINE)
                if marker_match:
                    updated = f"{updated[: marker_match.start()]}{helper}\n\n{updated[marker_match.start() :]}"
                else:
                    import_block = re.match(r"((?:from [^\n]+\n|import [^\n]+\n)+\n?)", updated)
                    if import_block:
                        updated = f"{updated[: import_block.end()]}{helper}\n\n{updated[import_block.end() :]}"
                    else:
                        updated = f"{helper}\n\n{updated}"
        normalized[path] = updated
    return normalized


def _codegen_max_attempts(fallback_models: list[str]) -> int:
    if fallback_models:
        return _CODEGEN_MODEL_MAX_ATTEMPTS
    return _STRICT_PRIMARY_CODEGEN_MAX_ATTEMPTS


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

    return "module.exports = {\n  plugins: {\n    tailwindcss: {},\n    autoprefixer: {},\n  },\n};\n"


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


async def _parse_generated_files_response(content, label: str) -> dict:
    parsed = _parse_json_response(content, {"files": {}}, label=label)
    files = parsed.get("files")
    if isinstance(files, dict) and files:
        return parsed

    raw_response = str(parsed.get("raw_response") or "").strip()
    if not raw_response:
        return parsed

    repair_model = MODEL_CONFIG["ci_repair"]
    repair_llm = get_llm(model=repair_model, temperature=0.0, max_tokens=20000)
    repair_messages = [
        {
            "role": "system",
            "content": (
                "You repair malformed code-generation payloads.\n"
                "Return ONLY strict JSON with this exact shape: "
                '{"files":{"path":"full file content"}}.\n'
                "Preserve file contents, escape newlines and quotes correctly, and remove any prose outside the JSON object."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Repair this malformed code-generation payload into strict JSON.\n\nLabel: {label}\n\n{raw_response}"
            ),
        },
    ]

    try:
        repaired = await ainvoke_with_retry(
            repair_llm,
            repair_messages,
            max_attempts=2,
            fallback_models=get_rate_limit_fallback_models(repair_model),
            rate_limit_switch_after_attempts=2,
        )
        repaired_payload = _parse_json_response(repaired.content, {"files": {}}, label=f"{label}-repair")
        if isinstance(repaired_payload.get("files"), dict) and repaired_payload["files"]:
            logger.info("[CODE_GEN] %s: recovered malformed JSON via repair pass", label)
            return repaired_payload
    except Exception as exc:
        logger.warning("[CODE_GEN] %s: repair pass failed: %s", label, str(exc)[:200])

    return parsed


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
