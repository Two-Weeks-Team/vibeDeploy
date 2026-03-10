import json

from agent.nodes.code_generator import _normalize_files_dict, _normalize_frontend_files


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
