import json

import pytest

import agent.nodes.code_generator as code_generator_module
from agent.nodes.code_generator import (
    _build_backend_prompt_messages,
    _build_frontend_prompt_messages,
    _normalize_backend_files,
    _normalize_cross_stack,
    _normalize_files_dict,
    _normalize_frontend_files,
    _parse_json_response,
)


def test_normalize_frontend_files_patches_next_tsconfig_and_tailwind():
    files = {
        "src/app/page.tsx": (
            "import { API } from 'next/app';\n"
            "import { useState } from 'react';\n"
            "import Form from '@/src/components/Form';\n"
            "export default function Page() { const [items, setItems] = useState([]); const [selected, setSelected] = useState(null); return null; }"
        ),
        "src/components/Form.tsx": "export function Form() { return null; }",
        "tsconfig.json": json.dumps(
            {
                "compilerOptions": {
                    "module": "ESNext",
                    "moduleResolution": "Node16",
                    "paths": {"@/*": ["./broken/*"]},
                }
            }
        ),
        "tailwind.config.ts": "export default {};",
        "postcss.config.js": "export default { plugins: { tailwindcss: {}, autoprefixer: {} } };",
        "next.config.js": "module.exports = { reactStrictMode: true, swcMinify: true, experimental: { serverComponents: true } };",
    }

    normalized = _normalize_frontend_files(files)
    tsconfig = json.loads(normalized["tsconfig.json"])

    assert normalized["next-env.d.ts"].startswith("/// <reference types=\"next\" />")
    assert "@/src/" not in normalized["src/app/page.tsx"]
    assert "@/components/Form" in normalized["src/app/page.tsx"]
    assert normalized["src/app/page.tsx"].startswith('"use client";')
    assert "next/app" not in normalized["src/app/page.tsx"]
    assert "useState<any[]>([])" in normalized["src/app/page.tsx"]
    assert "useState<any>(null)" in normalized["src/app/page.tsx"]
    assert "export default Form" in normalized["src/components/Form.tsx"]
    assert tsconfig["compilerOptions"]["moduleResolution"] == "bundler"
    assert tsconfig["compilerOptions"]["paths"] == {"@/*": ["./src/*"]}
    assert tsconfig["compilerOptions"]["baseUrl"] == "."
    assert tsconfig["compilerOptions"]["lib"] == ["DOM", "DOM.Iterable", "ES2022"]
    assert {"name": "next"} in tsconfig["compilerOptions"]["plugins"]
    assert ".next/types/**/*.ts" in tsconfig["include"]
    assert "swcMinify" not in normalized["next.config.js"]
    assert "serverComponents" not in normalized["next.config.js"]
    assert "./src/**/*.{js,ts,jsx,tsx,mdx}" in normalized["tailwind.config.ts"]
    assert "card: 'var(--card)'" in normalized["tailwind.config.ts"]
    assert "borderRadius" in normalized["tailwind.config.ts"]
    assert "module.exports" in normalized["postcss.config.js"]
    assert "plugins" in normalized["postcss.config.js"]


def test_normalize_files_dict_stringifies_structured_file_bodies():
    normalized = _normalize_files_dict(
        {
            "package.json": {"name": "demo", "private": True},
            "src/app/page.tsx": "export default function Page() { return null; }",
        }
    )

    assert '"name": "demo"' in normalized["package.json"]
    assert normalized["src/app/page.tsx"].startswith("export default")


def test_normalize_files_dict_flattens_objectified_code_file_bodies():
    normalized = _normalize_files_dict(
        {
            "src/app/layout.tsx": {
                "import": "import './globals.css';",
                "export": (
                    "export default function RootLayout({ children }: { children: React.ReactNode }) {\n"
                    "  return <html><body>{children}</body></html>;\n"
                    "}"
                ),
            },
            "src/app/page.tsx": {
                "import": '"use client";\nimport { useState } from "react";',
                "export": (
                    "export default function Page() {\n"
                    "  const [count, setCount] = useState(0);\n"
                    "  return <button onClick={() => setCount(count + 1)}>{count}</button>;\n"
                    "}"
                ),
            },
        }
    )

    assert normalized["src/app/layout.tsx"].startswith("import './globals.css';")
    assert "export default function RootLayout" in normalized["src/app/layout.tsx"]
    assert normalized["src/app/page.tsx"].startswith('"use client";')
    assert "const [count, setCount] = useState(0);" in normalized["src/app/page.tsx"]


def test_normalize_files_dict_flattens_objectified_code_strings():
    normalized = _normalize_files_dict(
        {
            "src/app/page.tsx": (
                '"use client";\n\n'
                "{\n"
                '  "import": "use client;\\nimport { useState } from \\"react\\";",\n'
                '  "export": "export default function Page() {\\n  const [count, setCount] = useState(0);\\n  return <button>{count}</button>;\\n}"\n'
                "}"
            )
        }
    )

    assert normalized["src/app/page.tsx"].startswith("use client;")
    assert 'import { useState } from "react";' in normalized["src/app/page.tsx"]
    assert "const [count, setCount] = useState(0);" in normalized["src/app/page.tsx"]


def test_normalize_cross_stack_fixes_api_prefix_and_payload_field_names():
    frontend = {
        "src/lib/api.ts": (
            "export async function fetchSummaries(url) {\n"
            "  return fetch(`${API_BASE}/summarize`, {\n"
            "    method: 'POST',\n"
            "    body: JSON.stringify({ url }),\n"
            "  });\n"
            "}\n"
        )
    }
    backend = {
        "main.py": (
            "from fastapi import FastAPI\n"
            "from routes import router\n\n"
            "app = FastAPI()\n"
            "app.include_router(router)\n"
        ),
        "routes.py": (
            "from fastapi import APIRouter\n"
            "from pydantic import BaseModel\n\n"
            'router = APIRouter(prefix="/api")\n\n'
            "class SummarizeRequest(BaseModel):\n"
            "    content: str\n\n"
            '@router.post("/summarize")\n'
            "async def summarize(req: SummarizeRequest):\n"
            "    return {\"summary\": req.content}\n"
        ),
    }

    normalized_frontend, normalized_backend = _normalize_cross_stack(frontend, backend)

    assert 'prefix="/api"' not in normalized_backend["routes.py"]
    assert '@app.middleware("http")' in normalized_backend["main.py"]
    assert 'JSON.stringify({ content: url })' in normalized_frontend["src/lib/api.ts"]


def test_normalize_backend_files_strips_api_prefix_from_route_decorators():
    files = {
        "main.py": (
            "from fastapi import FastAPI\n"
            "from routes import router\n\n"
            "app = FastAPI()\n"
            "app.include_router(router)\n"
        ),
        "routes.py": (
            "from fastapi import APIRouter\n\n"
            "router = APIRouter()\n\n"
            '@router.post("/api/plan")\n'
            "async def create_plan():\n"
            "    return {'ok': True}\n\n"
            '@router.post("/api/insights")\n'
            "async def create_insights():\n"
            "    return {'ok': True}\n"
        ),
    }

    normalized = _normalize_backend_files(files)

    assert '@app.middleware("http")' in normalized["main.py"]
    assert '@router.post("/plan")' in normalized["routes.py"]
    assert '@router.post("/insights")' in normalized["routes.py"]
    assert '"/api/plan"' not in normalized["routes.py"]
    assert '"/api/insights"' not in normalized["routes.py"]


def test_normalize_frontend_files_adds_resilient_api_error_handling_and_partial_success():
    files = {
        "src/lib/api.ts": (
            "export async function summarize(url) {\n"
            "  const res = await fetch('/api/summarize', { method: 'POST' });\n"
            "  if (!res.ok) {\n"
            "    const err = await res.json();\n"
            "    throw new Error(err.error?.message ?? 'Summarization failed');\n"
            "  }\n"
            "  return (await res.json()).summary;\n"
            "}\n"
            "export async function generateTags(url) {\n"
            "  const res = await fetch('/api/generate-tags', { method: 'POST' });\n"
            "  if (!res.ok) {\n"
            "    const err = await res.json();\n"
            "    throw new Error(err.error?.message ?? 'Tag generation failed');\n"
            "  }\n"
            "  return (await res.json()).tags;\n"
            "}\n"
        ),
        "src/components/Hero.tsx": (
            "\"use client\";\n"
            "export default async function Hero(url) {\n"
            "  const [generatedSummary, generatedTags] = await Promise.all([\n"
            "    summarize(url),\n"
            "    generateTags(url)\n"
            "  ]);\n"
            "  setSummary(generatedSummary);\n"
            "  setTags(generatedTags);\n"
            "}\n"
        ),
    }

    normalized = _normalize_frontend_files(files)

    assert "throwApiError" in normalized["src/lib/api.ts"]
    assert 'await throwApiError(res, "Tag generation failed");' in normalized["src/lib/api.ts"]
    assert "Promise.allSettled" in normalized["src/components/Hero.tsx"]
    assert "Tag generation failed, but the summary is available." in normalized["src/components/Hero.tsx"]


def test_normalize_frontend_files_adds_required_google_font_weights():
    files = {
        "src/components/InsightPanel.tsx": (
            "import { Merriweather } from 'next/font/google';\n"
            "const merri = Merriweather({ subsets: ['latin'], variable: '--font-merri' });\n"
            "export default function InsightPanel(){ return <section className={merri.variable}>Hello</section>; }\n"
        )
    }

    normalized = _normalize_frontend_files(files)

    assert "weight: ['400', '700']" in normalized["src/components/InsightPanel.tsx"]


def test_normalize_frontend_files_adds_api_base_fallback():
    files = {
        "src/lib/api.ts": (
            "export async function fetchHabits() {\n"
            "  return fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/habits`);\n"
            "}\n"
        ),
        "src/app/page.tsx": (
            '"use client";\n'
            "export default function Page() {\n"
            "  return fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/health`);\n"
            "}\n"
        ),
    }

    normalized = _normalize_frontend_files(files)

    assert '${(process.env.NEXT_PUBLIC_API_URL || "")}/api/habits' in normalized["src/lib/api.ts"]
    assert '${(process.env.NEXT_PUBLIC_API_URL || "")}/api/health' in normalized["src/app/page.tsx"]


def test_normalize_frontend_files_removes_use_client_from_layout_metadata_export():
    files = {
        "src/app/layout.tsx": (
            '"use client";\n\n'
            "import '@/app/globals.css';\n\n"
            "export const metadata = {\n"
            "  title: 'DemoPilot',\n"
            "};\n\n"
            "export default function RootLayout({ children }: { children: React.ReactNode }) {\n"
            "  return <html><body>{children}</body></html>;\n"
            "}\n"
        )
    }

    normalized = _normalize_frontend_files(files)

    assert not normalized["src/app/layout.tsx"].lstrip().startswith('"use client";')
    assert "export const metadata" in normalized["src/app/layout.tsx"]


def test_normalize_frontend_files_canonicalizes_broken_use_client_directive_and_heroicons():
    files = {
        "package.json": json.dumps({"name": "demo-pilot", "private": True}),
        "src/components/Rehearsal.tsx": (
            "\"use client';\n"
            "import { MicrophoneIcon, CloudUploadIcon } from '@heroicons/react/24/solid';\n"
            "export default function Rehearsal() { return <MicrophoneIcon className=\"h-5 w-5\" />; }\n"
        ),
    }

    normalized = _normalize_frontend_files(files)

    assert normalized["src/components/Rehearsal.tsx"].startswith('"use client";')
    assert "ArrowUpTrayIcon" in normalized["src/components/Rehearsal.tsx"]
    assert "CloudUploadIcon" not in normalized["src/components/Rehearsal.tsx"]


def test_normalize_frontend_files_adds_detected_optional_dependencies_to_package_json():
    files = {
        "package.json": json.dumps(
            {
                "name": "queueflow-lite",
                "private": True,
                "dependencies": {
                    "next": "15.5.12",
                    "react": "19.0.0",
                    "react-dom": "19.0.0",
                    "@heroicons/react": "2.0.0",
                },
            }
        ),
        "src/components/QRCodeScanner.tsx": (
            '"use client";\n'
            "import { CameraIcon } from '@heroicons/react/24/outline';\n"
            "export default function QRCodeScanner() { return <CameraIcon className=\"h-5 w-5\" />; }\n"
        ),
    }

    normalized = _normalize_frontend_files(files)
    package_json = json.loads(normalized["package.json"])

    assert package_json["dependencies"]["@heroicons/react"] == "2.2.0"
    assert package_json["dependencies"]["typescript"] == "5.7.3"
    assert package_json["engines"] == {"node": "22.x"}


def test_parse_json_response_extracts_balanced_json_when_trailing_text_exists():
    response = (
        "Here is the generated bundle:\n"
        "{\n"
        '  "files": {\n'
        '    "src/app/page.tsx": "export default function Page() { return <div>{\\"ok\\"}</div>; }"\n'
        "  }\n"
        "}\n"
        "This trailing note should be ignored.\n"
    )

    parsed = _parse_json_response(response, {"files": {}}, label="frontend")

    assert parsed["files"]["src/app/page.tsx"].startswith("export default function Page")


def test_build_frontend_prompt_messages_repeat_strategy_for_deepseek_fallback():
    prompt_strategy = {
        "model_plan": {
            "frontend": {
                "family": "openai_gpt_oss",
                "fallback_families": ["deepseek_r1", "qwen3"],
            }
        },
        "frontend_prompt_appendix": "Frontend Architect:\n- Preserve the design system.",
        "cross_model_user_contract": "Cross-Model Output Contract:\n- Return only JSON.",
    }

    messages = _build_frontend_prompt_messages(
        context='{"idea": "demo"}',
        prompt_strategy=prompt_strategy,
        eval_feedback="Missing src/app/page.tsx",
    )

    assert messages[0]["role"] == "system"
    assert "Runtime Strategy Stack" in messages[0]["content"]
    assert "/no_think" in messages[1]["content"]
    assert "DeepSeek compatibility note" in messages[1]["content"]
    assert "Missing src/app/page.tsx" in messages[0]["content"]
    assert "Runtime Strategy Stack" in messages[1]["content"]


def test_build_backend_prompt_messages_use_user_only_for_primary_deepseek():
    prompt_strategy = {
        "model_plan": {
            "backend": {
                "family": "deepseek_r1",
                "fallback_families": [],
            }
        },
        "backend_prompt_appendix": "Backend Expert:\n- Keep routes contract-safe.",
        "cross_model_user_contract": "Cross-Model Output Contract:\n- Return only JSON.",
    }

    messages = _build_backend_prompt_messages(
        context='{"idea": "demo"}',
        prompt_strategy=prompt_strategy,
        eval_feedback="Fix response field names",
    )

    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert "Backend Expert" in messages[0]["content"]
    assert "Fix response field names" in messages[0]["content"]


def test_normalize_frontend_files_adds_chart_dependencies_when_imported():
    files = {
        "package.json": json.dumps({"name": "studymate", "private": True}),
        "src/components/ProgressDashboard.tsx": (
            '"use client";\n'
            "import { Doughnut } from 'react-chartjs-2';\n"
            "import 'chart.js/auto';\n"
            "export default function ProgressDashboard() { return <Doughnut data={{ labels: [], datasets: [] }} />; }\n"
        ),
    }

    normalized = _normalize_frontend_files(files)
    package_json = json.loads(normalized["package.json"])

    assert package_json["dependencies"]["react-chartjs-2"] == "5.3.1"
    assert package_json["dependencies"]["chart.js"] == "4.5.1"


def test_normalize_frontend_files_adds_overloads_for_optional_body_api_helpers():
    files = {
        "src/lib/api.ts": (
            "export type JoinRequest = { name: string };\n"
            "export type JoinResponse = { queue_position: number };\n"
            "export type PositionResponse = { current_position: number };\n\n"
            "export async function fetchQueuePosition(\n"
            "  queueId: string,\n"
            "  body?: JoinRequest\n"
            "): Promise<JoinResponse | PositionResponse> {\n"
            "  return body ? { queue_position: 1 } : { current_position: 1 };\n"
            "}\n"
        )
    }

    normalized = _normalize_frontend_files(files)

    assert "export async function fetchQueuePosition(queueId: string, body: JoinRequest): Promise<JoinResponse>;" in normalized["src/lib/api.ts"]
    assert "export async function fetchQueuePosition(queueId: string): Promise<PositionResponse>;" in normalized["src/lib/api.ts"]


def test_normalize_frontend_files_adds_missing_react_hook_imports():
    files = {
        "src/components/Hero.tsx": (
            '"use client";\n'
            "export default function Hero() {\n"
            "  const [count, setCount] = useState(0);\n"
            "  useEffect(() => {}, []);\n"
            "  return <button onClick={() => setCount(count + 1)}>{count}</button>;\n"
            "}\n"
        )
    }

    normalized = _normalize_frontend_files(files)

    assert 'import { useEffect, useState } from "react";' in normalized["src/components/Hero.tsx"]


def test_normalize_frontend_files_materializes_missing_ui_button_component():
    files = {
        "src/components/Hero.tsx": (
            '"use client";\n'
            'import { Button } from "@/components/ui/button";\n'
            "export default function Hero() { return <Button>Launch</Button>; }\n"
        )
    }

    normalized = _normalize_frontend_files(files)

    assert "src/components/ui/button.tsx" in normalized
    assert "export function Button" in normalized["src/components/ui/button.tsx"]


def test_normalize_backend_files_coerces_plain_text_ai_responses():
    files = {
        "ai_service.py": (
            "import re\n"
            "from typing import Any, Dict\n\n"
            "async def _call_inference(messages):\n"
            "    try:\n"
            "        raw_json = 'hello, world'\n"
            "        return {\"note\": \"Failed to parse JSON from AI response\", \"raw\": raw_json}\n"
            "    except Exception:\n"
            "        return {\"note\": \"AI unavailable\"}\n"
        )
    }

    normalized = _normalize_backend_files(files)

    assert "_coerce_unstructured_payload" in normalized["ai_service.py"]
    assert "return _coerce_unstructured_payload(raw_json)" in normalized["ai_service.py"]


def test_normalize_backend_ai_fallback_helper_is_import_safe_for_call_inference_files():
    files = {
        "ai_service.py": (
            "import os\n"
            "import json\n\n"
            "async def call_inference(messages):\n"
            "    raw_json = 'hello, world'\n"
            '    return {"note": "Failed to parse JSON from AI response", "raw": raw_json}\n'
        )
    }

    normalized = _normalize_backend_files(files)
    compiled = compile(normalized["ai_service.py"], "ai_service.py", "exec")

    assert "_coerce_unstructured_payload" in normalized["ai_service.py"]
    assert "dict[str, object]" in normalized["ai_service.py"]
    assert '"items": items' in normalized["ai_service.py"]
    assert '"highlights": highlights' in normalized["ai_service.py"]
    assert compiled is not None


def test_normalize_backend_files_fixes_oauth_scheme_reference_and_adds_python_version():
    files = {
        "routes.py": (
            "from fastapi import Depends\n"
            "from fastapi.security import OAuth2PasswordBearer\n\n"
            'oauth_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")\n\n'
            "async def get_current_user(token: str = Depends(auth_scheme)):\n"
            "    return token\n"
        )
    }

    normalized = _normalize_backend_files(files)

    assert "Depends(oauth_scheme)" in normalized["routes.py"]
    assert normalized[".python-version"] == "3.13\n"


def test_normalize_backend_files_avoids_duplicate_sslmode_query_params():
    files = {
        "models.py": (
            '_raw_url = os.getenv("DATABASE_URL", os.getenv("POSTGRES_URL", "sqlite:///./app.db"))\n'
            'if not _raw_url.startswith("sqlite") and "localhost" not in _raw_url and "127.0.0.1" not in _raw_url:\n'
            '    if "?" in _raw_url:\n'
            '        _raw_url = f"{_raw_url}&sslmode=require"\n'
            "    else:\n"
            '        _raw_url = f"{_raw_url}?sslmode=require"\n'
        )
    }

    normalized = _normalize_backend_files(files)

    assert 'and "sslmode=" not in _raw_url.lower()' in normalized["models.py"]


def test_normalize_backend_files_awaits_async_ai_helpers_in_routes():
    files = {
        "ai_service.py": (
            "async def summarize_text(url=None, text=None):\n"
            "    return {'summary': {'short': 'ok', 'long': 'ok'}}\n"
        ),
        "routes.py": (
            "from ai_service import summarize_text\n\n"
            "def create_bookmark(payload):\n"
            "    result = summarize_text(url=payload.url)\n"
            "    return result\n"
        ),
    }

    normalized = _normalize_backend_files(files)

    assert "async def create_bookmark" in normalized["routes.py"]
    assert "result = await summarize_text" in normalized["routes.py"]


def test_normalize_backend_files_relaxes_preferences_and_context_request_types():
    files = {
        "models.py": (
            "from typing import Dict\n"
            "from typing import Any, List\n\n"
            "class PlanRequest:\n"
            "    preferences: Dict[str, Any] = {}\n"
            "    context: List[str] = []\n"
            "    query: str = ''\n"
        )
    }

    normalized = _normalize_backend_files(files)

    assert "preferences: Any =" in normalized["models.py"]
    assert "context: Any =" in normalized["models.py"]


def test_normalize_backend_files_aligns_ai_response_shapes_with_frontend_contract():
    files = {
        "routes.py": (
            "from pydantic import BaseModel\n"
            "from typing import List\n\n"
            "class PlanResponse(BaseModel):\n"
            "    summary: str\n"
            "    items: List[str]\n"
            "    score: float\n\n"
            "class InsightsResponse(BaseModel):\n"
            "    insights: str\n"
            "    next_actions: List[str]\n"
            "    highlights: List[str]\n\n"
            'SYSTEM_PLAN = "Return JSON with keys: summary (string), items (list of strings), score (float)."\n'
            'SYSTEM_INSIGHTS = "Return JSON with keys: insights (string), next_actions (list of strings), highlights (list of strings)."\n'
        ),
        "ai_service.py": (
            "import json\n\n"
            "async def call_inference(messages):\n"
            "    try:\n"
            '        json_str = "{\\"summary\\": \\"ok\\"}"\n'
            "        result = json.loads(json_str)\n"
            "        return result\n"
            "    except Exception as e:\n"
            "        fallback = {\n"
            '            "summary": "AI service unavailable",\n'
            '            "items": [],\n'
            '            "score": 0.0,\n'
            '            "insights": "AI service unavailable",\n'
            '            "next_actions": [],\n'
            '            "highlights": [],\n'
            '            "note": "AI is temporarily unavailable. Please try again later."\n'
            "        }\n"
            "        return fallback\n"
        ),
    }

    normalized = _normalize_backend_files(files)

    assert "items: list[dict[str, object]]" in normalized["routes.py"]
    assert "insights: list[str]" in normalized["routes.py"]
    assert "items (list of objects with title, detail, score)" in normalized["routes.py"]
    assert "insights (list of strings)" in normalized["routes.py"]
    assert "_normalize_inference_payload" in normalized["ai_service.py"]
    assert "return _normalize_inference_payload(result)" in normalized["ai_service.py"]
    assert 'return _coerce_unstructured_payload("AI service fallback")' in normalized["ai_service.py"]


@pytest.mark.asyncio
async def test_code_generator_regenerates_only_missing_frontend(monkeypatch):
    state = {
        "generated_docs": {},
        "idea": {"title": "QueueFlow"},
        "blueprint": {
            "frontend_files": {
                "package.json": {},
                "src/app/layout.tsx": {},
                "src/app/page.tsx": {},
            },
            "backend_files": {
                "main.py": {},
                "requirements.txt": {},
            },
        },
        "prompt_strategy": {},
        "code_eval_result": {
            "passed": False,
            "missing_frontend": ["src/app/page.tsx"],
            "missing_backend": [],
        },
        "frontend_code": {},
        "backend_code": {
            "main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
            "requirements.txt": "fastapi\nuvicorn\n",
        },
    }
    calls = {"frontend": 0, "backend": 0, "max_attempts": []}

    async def fake_frontend(*args, **kwargs):
        calls["frontend"] += 1
        calls["max_attempts"].append(kwargs["max_attempts"])
        return {
            "package.json": '{"name":"queueflow","private":true}',
            "src/app/layout.tsx": "export default function Layout({ children }) { return <html><body>{children}</body></html>; }",
            "src/app/page.tsx": "export default function Page() { return <main>QueueFlow</main>; }",
        }

    async def fake_backend(*args, **kwargs):
        calls["backend"] += 1
        return {}

    monkeypatch.setattr(code_generator_module, "get_llm", lambda **kwargs: object())
    monkeypatch.setattr(code_generator_module, "get_rate_limit_fallback_models", lambda model: [])
    monkeypatch.setattr(code_generator_module, "_generate_frontend_files", fake_frontend)
    monkeypatch.setattr(code_generator_module, "_generate_backend_files", fake_backend)
    monkeypatch.setattr(code_generator_module, "_normalize_cross_stack", lambda fe, be: (fe, be))

    result = await code_generator_module.code_generator(state)

    assert calls["frontend"] == 1
    assert calls["backend"] == 0
    assert calls["max_attempts"] == [code_generator_module._codegen_max_attempts([])]
    assert "src/app/page.tsx" in result["frontend_code"]
    assert "main.py" in result["backend_code"]
    assert "requirements.txt" in result["backend_code"]


def test_codegen_max_attempts_stays_high_without_fallback_models():
    assert code_generator_module._codegen_max_attempts([]) == code_generator_module._STRICT_PRIMARY_CODEGEN_MAX_ATTEMPTS
    assert code_generator_module._codegen_max_attempts(["openai-gpt-oss-20b"]) == code_generator_module._CODEGEN_MODEL_MAX_ATTEMPTS


@pytest.mark.asyncio
async def test_generate_frontend_files_uses_deterministic_fallback_on_llm_error(monkeypatch):
    async def _fail(*args, **kwargs):
        raise RuntimeError("Error code: 429 - rate limit exceeded")

    monkeypatch.setattr(code_generator_module, "ainvoke_with_retry", _fail)

    files = await code_generator_module._generate_frontend_files(
        object(),
        json.dumps({"idea": {"name": "TripCanvas AI", "tagline": "Plan cinematic journeys"}}, ensure_ascii=False),
    )

    assert "src/app/page.tsx" in files
    assert "src/lib/api.ts" in files
    assert "src/components/WorkspacePanel.tsx" in files
    assert "src/components/CollectionPanel.tsx" in files
    assert "src/components/StatsStrip.tsx" in files


def test_fallback_frontend_bundle_covers_template_blueprint_components():
    files = code_generator_module._build_fallback_frontend_bundle(
        json.dumps(
            {
                "idea": {"name": "TripCanvas AI", "tagline": "Plan cinematic journeys"},
                "blueprint": {
                    "frontend_files": {
                        "package.json": {},
                        "src/app/layout.tsx": {},
                        "src/app/page.tsx": {},
                        "src/app/globals.css": {},
                        "src/lib/api.ts": {},
                        "src/components/Hero.tsx": {},
                        "src/components/InsightPanel.tsx": {},
                        "src/components/StatePanel.tsx": {},
                        "src/components/CollectionPanel.tsx": {},
                        "src/components/StatsStrip.tsx": {},
                    }
                },
            },
            ensure_ascii=False,
        )
    )

    expected = {
        "package.json",
        "src/app/layout.tsx",
        "src/app/page.tsx",
        "src/app/globals.css",
        "src/lib/api.ts",
        "src/components/Hero.tsx",
        "src/components/InsightPanel.tsx",
        "src/components/StatePanel.tsx",
        "src/components/CollectionPanel.tsx",
        "src/components/StatsStrip.tsx",
    }

    assert expected.issubset(files.keys())


def test_fallback_frontend_bundle_varies_layout_markup_and_reference_objects():
    storyboard = code_generator_module._build_fallback_frontend_bundle(
        json.dumps(
            {
                "idea": {
                    "name": "TripCanvas AI",
                    "tagline": "Plan cinematic journeys",
                    "layout_archetype": "storyboard",
                    "sample_seed_data": ["Day 1 route", "Night market stop"],
                    "reference_objects": ["route", "district"],
                }
            },
            ensure_ascii=False,
        )
    )
    console = code_generator_module._build_fallback_frontend_bundle(
        json.dumps(
            {
                "idea": {
                    "name": "StageSignal",
                    "tagline": "Run the live show",
                    "layout_archetype": "operations_console",
                    "sample_seed_data": ["Opening cue", "Sponsor break"],
                    "reference_objects": ["cue", "incident"],
                }
            },
            ensure_ascii=False,
        )
    )

    assert "src/components/ReferenceShelf.tsx" in storyboard
    assert 'const LAYOUT = "storyboard"' in storyboard["src/app/page.tsx"]
    assert "storyboard-stage" in storyboard["src/app/page.tsx"]
    assert "Day 1 route" in storyboard["src/app/page.tsx"]
    assert "route" in storyboard["src/app/page.tsx"]
    assert 'const LAYOUT = "operations_console"' in console["src/app/page.tsx"]
    assert "console-grid" in console["src/app/page.tsx"]
    assert "Opening cue" in console["src/app/page.tsx"]
    assert ".layout-operations-console .hero" in console["src/app/globals.css"]


def test_extract_template_seed_formats_structured_idea_lists_for_readable_ui_copy():
    seed = code_generator_module._extract_template_seed(
        json.dumps(
            {
                "idea": {
                    "name": "RoutePostcard",
                    "key_features": [
                        {
                            "name": "Mood-Driven Planner",
                            "description": "Choose city, vibe, trip length, and budget in one panel.",
                        },
                        {
                            "name": "Cinematic Postcard Storyboard",
                            "description": "Render a three-card editorial spread.",
                        },
                    ],
                    "sample_seed_data": [
                        {
                            "city": "Seoul",
                            "vibe": "vibrant nightlife",
                            "days": 3,
                            "budget_per_day": 120,
                            "postcards": [{"neighborhood": "Hongdae"}],
                        }
                    ],
                    "reference_objects": [
                        {"label": "Budget slider", "description": "Daily cap indicator"},
                        {"label": "Postcard card", "description": "Image + caption + map"},
                    ],
                }
            },
            ensure_ascii=False,
        )
    )

    assert seed["features"] == ["Mood-Driven Planner - Choose city, vibe, trip length, and budget in one panel.", "Cinematic Postcard Storyboard - Render a three-card editorial spread."]
    assert seed["sample_seed_data"] == ["Seoul · vibrant nightlife · 3 days · $120/day"]
    assert seed["reference_objects"] == ["Budget slider - Daily cap indicator", "Postcard card - Image + caption + map"]


@pytest.mark.asyncio
async def test_generate_backend_files_uses_deterministic_fallback_on_llm_error(monkeypatch):
    async def _fail(*args, **kwargs):
        raise RuntimeError("Error code: 429 - rate limit exceeded")

    monkeypatch.setattr(code_generator_module, "ainvoke_with_retry", _fail)

    files = await code_generator_module._generate_backend_files(
        object(),
        json.dumps({"idea": {"name": "TripCanvas AI", "tagline": "Plan cinematic journeys"}}, ensure_ascii=False),
    )

    assert "main.py" in files
    assert "routes.py" in files
    assert "ai_service.py" in files


@pytest.mark.asyncio
async def test_code_generator_forces_frontend_fallback_after_eval_failure(monkeypatch):
    async def _unexpected_frontend(*args, **kwargs):
        raise AssertionError("frontend LLM should not run when fallback is forced")

    async def _backend_files(*args, **kwargs):
        return {
            "main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
            "routes.py": "from fastapi import APIRouter\nrouter = APIRouter()\n",
            "requirements.txt": "fastapi\nuvicorn\n",
            "ai_service.py": "def build_plan(query, preferences): return {'summary': 'ok', 'score': 88, 'items': []}\n\ndef build_insights(selection, context): return {'insights': [], 'next_actions': [], 'highlights': []}\n",
        }

    monkeypatch.setattr(code_generator_module, "get_llm", lambda **kwargs: object())
    monkeypatch.setattr(code_generator_module, "get_rate_limit_fallback_models", lambda model: [])
    monkeypatch.setattr(code_generator_module, "_generate_frontend_files", _unexpected_frontend)
    monkeypatch.setattr(code_generator_module, "_generate_backend_files", _backend_files)
    monkeypatch.setattr(code_generator_module, "_normalize_cross_stack", lambda fe, be: (fe, be))

    result = await code_generator_module.code_generator(
        {
            "generated_docs": {},
            "idea": {
                "name": "RoutePostcard",
                "tagline": "Turn travel footage into route boards",
                "layout_archetype": "storyboard",
                "sample_seed_data": ["Day 1 route"],
                "reference_objects": ["route"],
            },
            "blueprint": {
                "frontend_files": {
                    "src/app/layout.tsx": {},
                    "src/app/page.tsx": {},
                    "src/app/globals.css": {},
                    "src/lib/api.ts": {},
                    "src/components/Hero.tsx": {},
                    "src/components/InsightPanel.tsx": {},
                    "src/components/StatePanel.tsx": {},
                    "src/components/WorkspacePanel.tsx": {},
                    "src/components/FeaturePanel.tsx": {},
                },
                "backend_files": {
                    "main.py": {},
                    "routes.py": {},
                    "requirements.txt": {},
                    "ai_service.py": {},
                },
            },
            "prompt_strategy": {},
            "code_eval_result": {
                "passed": False,
                "missing_frontend": ["src/components/WorkspacePanel.tsx"],
                "missing_backend": [],
                "experience": 62.0,
                "iteration": 1,
            },
            "frontend_code": {
                "src/app/page.tsx": "export default function Page(){ return <main><Hero /></main>; }",
            },
            "backend_code": {},
        }
    )

    assert "src/components/ReferenceShelf.tsx" in result["frontend_code"]
    assert "storyboard-stage" in result["frontend_code"]["src/app/page.tsx"]


@pytest.mark.asyncio
async def test_code_generator_prefers_deterministic_frontend_for_specialized_layout(monkeypatch):
    async def _unexpected_frontend(*args, **kwargs):
        raise AssertionError("frontend LLM should not run for specialized layouts")

    async def _backend_files(*args, **kwargs):
        return {
            "main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
            "routes.py": "from fastapi import APIRouter\nrouter = APIRouter()\n",
            "requirements.txt": "fastapi\nuvicorn\n",
            "ai_service.py": "def build_plan(query, preferences): return {'summary': 'ok', 'score': 88, 'items': []}\n\ndef build_insights(selection, context): return {'insights': [], 'next_actions': [], 'highlights': []}\n",
        }

    monkeypatch.setattr(code_generator_module, "get_llm", lambda **kwargs: object())
    monkeypatch.setattr(code_generator_module, "get_rate_limit_fallback_models", lambda model: [])
    monkeypatch.setattr(code_generator_module, "_generate_frontend_files", _unexpected_frontend)
    monkeypatch.setattr(code_generator_module, "_generate_backend_files", _backend_files)
    monkeypatch.setattr(code_generator_module, "_normalize_cross_stack", lambda fe, be: (fe, be))

    result = await code_generator_module.code_generator(
        {
            "generated_docs": {},
            "idea": {
                "name": "StageSignal",
                "tagline": "Run the live show",
                "layout_archetype": "operations_console",
                "sample_seed_data": ["Opening cue"],
                "reference_objects": ["cue"],
            },
            "blueprint": {
                "frontend_files": {
                    "src/app/layout.tsx": {},
                    "src/app/page.tsx": {},
                    "src/app/globals.css": {},
                    "src/lib/api.ts": {},
                },
                "backend_files": {
                    "main.py": {},
                    "routes.py": {},
                    "requirements.txt": {},
                    "ai_service.py": {},
                },
            },
            "prompt_strategy": {},
            "frontend_code": {},
            "backend_code": {},
        }
    )

    assert "console-grid" in result["frontend_code"]["src/app/page.tsx"]
    assert ".layout-operations-console .hero" in result["frontend_code"]["src/app/globals.css"]


@pytest.mark.asyncio
async def test_code_generator_merges_new_backend_files_into_existing_bundle(monkeypatch):
    state = {
        "generated_docs": {},
        "idea": {"title": "TripPilot"},
        "blueprint": {
            "frontend_files": {},
            "backend_files": {
                "main.py": {},
                "requirements.txt": {},
                "routes.py": {},
            },
        },
        "prompt_strategy": {},
        "code_eval_result": {
            "passed": False,
            "missing_frontend": [],
            "missing_backend": ["routes.py"],
        },
        "frontend_code": {},
        "backend_code": {
            "main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
            "requirements.txt": "fastapi\nuvicorn\n",
        },
    }
    calls = {"frontend": 0, "backend": 0}

    async def fake_backend(*args, **kwargs):
        calls["backend"] += 1
        return {
            "routes.py": "from fastapi import APIRouter\nrouter = APIRouter()\n@router.get('/health')\nasync def health(): return {'ok': True}\n"
        }

    async def fake_frontend(*args, **kwargs):
        calls["frontend"] += 1
        return {}

    monkeypatch.setattr(code_generator_module, "get_llm", lambda **kwargs: object())
    monkeypatch.setattr(code_generator_module, "get_rate_limit_fallback_models", lambda model: [])
    monkeypatch.setattr(code_generator_module, "_generate_frontend_files", fake_frontend)
    monkeypatch.setattr(code_generator_module, "_generate_backend_files", fake_backend)
    monkeypatch.setattr(code_generator_module, "_normalize_cross_stack", lambda fe, be: (fe, be))

    result = await code_generator_module.code_generator(state)

    assert calls["frontend"] == 0
    assert calls["backend"] == 1
    assert set(result["backend_code"]) >= {"main.py", "requirements.txt", "routes.py"}
