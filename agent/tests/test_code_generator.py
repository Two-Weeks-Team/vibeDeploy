import json

from agent.nodes.code_generator import _normalize_frontend_files


def test_normalize_frontend_files_patches_next_tsconfig_and_tailwind():
    files = {
        "src/app/page.tsx": (
            "import { useState } from 'react';\n"
            "import Form from '@/src/components/Form';\n"
            "export default function Page() { const [items, setItems] = useState([]); return null; }"
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
    }

    normalized = _normalize_frontend_files(files)
    tsconfig = json.loads(normalized["tsconfig.json"])

    assert normalized["next-env.d.ts"].startswith("/// <reference types=\"next\" />")
    assert "@/src/" not in normalized["src/app/page.tsx"]
    assert "@/components/Form" in normalized["src/app/page.tsx"]
    assert "useState<any[]>([])" in normalized["src/app/page.tsx"]
    assert "export default Form" in normalized["src/components/Form.tsx"]
    assert tsconfig["compilerOptions"]["moduleResolution"] == "bundler"
    assert tsconfig["compilerOptions"]["paths"] == {"@/*": ["./src/*"]}
    assert tsconfig["compilerOptions"]["baseUrl"] == "."
    assert {"name": "next"} in tsconfig["compilerOptions"]["plugins"]
    assert ".next/types/**/*.ts" in tsconfig["include"]
    assert "./src/**/*.{js,ts,jsx,tsx,mdx}" in normalized["tailwind.config.ts"]
    assert "module.exports" in normalized["postcss.config.js"]
    assert "plugins" in normalized["postcss.config.js"]
