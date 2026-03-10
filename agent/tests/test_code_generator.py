import json

from agent.nodes.code_generator import (
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
