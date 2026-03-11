from agent.nodes.code_evaluator import _check_consistency, _check_experience, _check_runnability, route_code_eval


def test_check_consistency_matches_contract_calls_across_generated_files():
    blueprint = {
        "frontend_backend_contract": [
            {
                "frontend_file": "src/lib/api.ts",
                "backend_file": "routes.py",
                "calls": ["GET /api/bookmarks", "POST /api/bookmarks/summarize"],
            }
        ]
    }
    frontend_code = {
        "src/app/page.tsx": (
            "async function load(){ await fetch('/api/bookmarks'); "
            "await fetch('/api/bookmarks/summarize', { method: 'POST' }); }"
        ),
        "src/components/BookmarkList.tsx": "export default function BookmarkList(){ return <div />; }",
    }
    backend_code = {
        "routes.py": (
            'from fastapi import APIRouter\n'
            'router = APIRouter(prefix="/api/bookmarks")\n'
            '@router.get("/")\n'
            'async def list_bookmarks(): ...\n'
            '@router.post("/summarize")\n'
            'async def summarize_bookmark(): ...\n'
        )
    }

    assert _check_consistency(frontend_code, backend_code, blueprint) >= 80.0


def test_check_consistency_uses_request_and_response_field_contracts():
    blueprint = {
        "frontend_backend_contract": [
            {
                "frontend_file": "src/lib/api.ts",
                "backend_file": "routes.py",
                "calls": ["POST /api/summarize"],
                "request_fields": ["url"],
                "response_fields": ["summary"],
            }
        ]
    }
    frontend_code = {
        "src/lib/api.ts": (
            "export async function summarize(url) {\n"
            "  const res = await fetch('/api/summarize', {\n"
            "    method: 'POST',\n"
            "    body: JSON.stringify({ url }),\n"
            "  });\n"
            "  const data = await res.json();\n"
            "  return data.summary;\n"
            "}\n"
        )
    }
    backend_code = {
        "routes.py": (
            "from fastapi import APIRouter\n"
            "from pydantic import BaseModel\n\n"
            "router = APIRouter()\n\n"
            "class SummarizeRequest(BaseModel):\n"
            "    url: str\n\n"
            "class SummarizeResponse(BaseModel):\n"
            "    summary: str\n\n"
            "@router.post('/summarize', response_model=SummarizeResponse)\n"
            "async def summarize(req: SummarizeRequest):\n"
            "    return SummarizeResponse(summary=req.url)\n"
        )
    }

    assert _check_consistency(frontend_code, backend_code, blueprint) >= 85.0


def test_check_runnability_accepts_server_component_with_direct_fetch():
    frontend_code = {
        "package.json": '{"dependencies":{"next":"15.0.0"}}',
        "src/app/layout.tsx": "export default function Layout({ children }) { return <html><body>{children}</body></html>; }",
        "src/app/page.tsx": "export default async function Page() { await fetch('/api/items'); return <main>Hello</main>; }",
        "src/app/globals.css": "body { margin: 0; }",
    }
    backend_code = {
        "requirements.txt": "fastapi\nuvicorn\n",
        "main.py": (
            "from fastapi import FastAPI\n"
            "app = FastAPI()\n"
            "@app.get('/api/items')\n"
            "async def get_items(): return []\n"
            "if __name__ == '__main__':\n"
            "    import uvicorn\n"
        ),
    }

    assert _check_runnability(frontend_code, backend_code) >= 80.0


def test_check_runnability_penalizes_unawaited_async_ai_helpers():
    frontend_code = {
        "package.json": '{"dependencies":{"next":"15.0.0"}}',
        "src/app/layout.tsx": "export default function Layout({ children }) { return <html><body>{children}</body></html>; }",
        "src/app/page.tsx": "export default async function Page() { return <main>Hello</main>; }",
        "src/app/globals.css": "body { margin: 0; }",
    }
    backend_code = {
        "requirements.txt": "fastapi\nuvicorn\n",
        "main.py": (
            "from fastapi import FastAPI\n"
            "app = FastAPI()\n"
            "if __name__ == '__main__':\n"
            "    import uvicorn\n"
        ),
        "routes.py": (
            "from ai_service import summarize_text\n"
            "def create_bookmark(payload):\n"
            "    result = summarize_text(url=payload.url)\n"
            "    return result\n"
        ),
        "ai_service.py": "async def summarize_text(url=None, text=None):\n    return {}\n",
    }

    assert _check_runnability(frontend_code, backend_code) < 85.0


def test_check_consistency_penalizes_misaligned_endpoint_names():
    blueprint = {
        "frontend_backend_contract": [
            {
                "frontend_file": "src/lib/api.ts",
                "backend_file": "routes.py",
                "calls": ["GET /api/bookmarks"],
            }
        ]
    }
    frontend_code = {
        "src/lib/api.ts": "export async function fetchItems() { return fetch('/api/links'); }",
    }
    backend_code = {
        "routes.py": (
            "from fastapi import APIRouter\n"
            "router = APIRouter()\n"
            "@router.get('/bookmarks')\n"
            "async def list_bookmarks():\n"
            "    return {'items': []}\n"
        )
    }

    assert _check_consistency(frontend_code, backend_code, blueprint) < 70.0


def test_check_experience_rewards_multi_panel_ui_and_resilient_api_patterns():
    blueprint = {
        "frontend_files": {
            "src/components/Hero.tsx": {},
            "src/components/InsightPanel.tsx": {},
            "src/components/CollectionPanel.tsx": {},
            "src/components/StatePanel.tsx": {},
        }
    }
    frontend_code = {
        "src/app/page.tsx": (
            "export default function Page(){ return <main><Hero /><InsightPanel /><CollectionPanel /><StatePanel /></main>; }"
        ),
        "src/components/Hero.tsx": "export default function Hero(){ return <section>Analyze</section>; }",
        "src/components/InsightPanel.tsx": "export default function InsightPanel(){ return <section>Summary result</section>; }",
        "src/components/CollectionPanel.tsx": "export default function CollectionPanel(){ return <section>Saved bookmarks history</section>; }",
        "src/components/StatePanel.tsx": "export default function StatePanel(){ return <div>Loading error empty state</div>; }",
        "src/lib/api.ts": "async function throwApiError(){} async function x(){ await Promise.allSettled([]); }",
    }

    assert _check_experience(frontend_code, blueprint) >= 80.0


def test_route_code_eval_retries_missing_backend_beyond_generic_iteration_limit():
    state = {
        "code_eval_result": {
            "passed": False,
            "missing_frontend": [],
            "missing_backend": ["routes.py"],
        },
        "code_eval_iteration": 3,
        "blueprint": {
            "frontend_files": {},
            "backend_files": {
                "main.py": {},
                "requirements.txt": {},
                "routes.py": {},
            },
        },
        "backend_code": {
            "main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
            "requirements.txt": "fastapi\nuvicorn\n",
        },
    }

    assert route_code_eval(state) == "code_generator"


def test_route_code_eval_deploys_after_backend_retry_budget_is_exhausted():
    state = {
        "code_eval_result": {
            "passed": False,
            "missing_frontend": [],
            "missing_backend": ["routes.py"],
        },
        "code_eval_iteration": 5,
        "blueprint": {
            "frontend_files": {},
            "backend_files": {
                "main.py": {},
                "requirements.txt": {},
                "routes.py": {},
            },
        },
        "backend_code": {
            "main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
            "requirements.txt": "fastapi\nuvicorn\n",
        },
    }

    assert route_code_eval(state) == "deployer"
