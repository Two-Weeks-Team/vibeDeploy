import json

from agent.nodes.code_generator import (
    _normalize_backend_files,
    _normalize_cross_stack,
    _normalize_files_dict,
    _normalize_frontend_files,
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
