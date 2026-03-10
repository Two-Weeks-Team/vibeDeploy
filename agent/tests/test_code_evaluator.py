from agent.nodes.code_evaluator import _check_consistency, _check_runnability


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
