import pytest

from agent.nodes.code_evaluator import (
    _check_consistency,
    _check_experience,
    _check_runnability,
    code_evaluator,
    route_code_eval,
)


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
            "from fastapi import APIRouter\n"
            'router = APIRouter(prefix="/api/bookmarks")\n'
            '@router.get("/")\n'
            "async def list_bookmarks(): ...\n"
            '@router.post("/summarize")\n'
            "async def summarize_bookmark(): ...\n"
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
        "main.py": ("from fastapi import FastAPI\napp = FastAPI()\nif __name__ == '__main__':\n    import uvicorn\n"),
        "routes.py": (
            "from ai_service import summarize_text\n"
            "def create_bookmark(payload):\n"
            "    result = summarize_text(url=payload.url)\n"
            "    return result\n"
        ),
        "ai_service.py": "async def summarize_text(url=None, text=None):\n    return {}\n",
    }

    assert _check_runnability(frontend_code, backend_code) < 85.0


@pytest.mark.asyncio
async def test_code_evaluator_blocks_deterministic_fallback_scaffold_deployments():
    result = await code_evaluator(
        {
            "blueprint": {
                "frontend_files": {
                    "package.json": {},
                    "src/app/layout.tsx": {},
                    "src/app/page.tsx": {},
                    "src/app/globals.css": {},
                },
                "backend_files": {"main.py": {}, "requirements.txt": {}},
            },
            "frontend_code": {
                ".vibedeploy-fallback-frontend.json": '{"kind":"frontend"}',
                "package.json": '{"dependencies":{"next":"15.0.0"}}',
                "src/app/layout.tsx": "export default function Layout({ children }) { return <html><body>{children}</body></html>; }",
                "src/app/page.tsx": "export default function Page() { return <main>Fallback</main>; }",
                "src/app/globals.css": "body { margin: 0; }",
            },
            "backend_code": {
                "main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
                "requirements.txt": "fastapi\nuvicorn\n",
            },
        }
    )

    assert result["code_eval_result"]["passed"] is False
    assert result["code_eval_result"]["deployment_blocked"] is True
    assert "deterministic fallback scaffold detected" in result["code_eval_result"]["blockers"]


@pytest.mark.asyncio
async def test_code_evaluator_reports_flagship_artifact_fidelity_hits():
    result = await code_evaluator(
        {
            "blueprint": {
                "frontend_files": {
                    "package.json": {},
                    "src/app/layout.tsx": {},
                    "src/app/page.tsx": {},
                    "src/app/globals.css": {},
                },
                "backend_files": {"main.py": {}, "requirements.txt": {}},
            },
            "frontend_code": {
                "package.json": '{"dependencies":{"next":"15.0.0"}}',
                "src/app/layout.tsx": "export default function Layout({ children }) { return <html><body>{children}</body></html>; }",
                "src/app/page.tsx": "export default function Page() { return <main>route card district stop backup plan budget cue day-by-day route sequence highlight stops weather fallback</main>; }",
                "src/app/globals.css": "body { margin: 0; }",
            },
            "backend_code": {
                "main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
                "requirements.txt": "fastapi\nuvicorn\n",
            },
            "flagship_contract": {
                "required_objects": ["route card", "district stop", "backup plan", "budget cue"],
                "required_results": ["day-by-day route sequence", "highlight stops", "weather or timing fallback"],
                "acceptance_checks": ["first fold already looks like a travel artifact"],
            },
        }
    )

    fidelity = result["code_eval_result"]["artifact_fidelity"]
    assert fidelity["score"] >= 70
    assert "route card" in fidelity["required_object_hits"]
    assert "day-by-day route sequence" in fidelity["required_result_hits"]


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
        "src/components/StatePanel.tsx": (
            "import { useState } from 'react';"
            "export default function StatePanel(){"
            "const [loading, setLoading] = useState(false);"
            "const [error, setError] = useState<string | null>(null);"
            "return loading ? <div>Loading...</div> : error ? <div>{error}</div> : <div>empty state</div>;"
            "}"
        ),
        "src/lib/api.ts": "async function throwApiError(){} async function x(){ await Promise.allSettled([]); }",
    }

    assert _check_experience(frontend_code, blueprint) >= 80.0


@pytest.mark.asyncio
async def test_code_evaluator_fails_when_blueprint_frontend_files_are_missing():
    state = {
        "blueprint": {
            "frontend_files": {
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
            },
        },
        "frontend_code": {
            "src/app/page.tsx": "export default function Page(){ return <main><Hero /><InsightPanel /><StatePanel /></main>; }",
            "src/components/Hero.tsx": "export default function Hero(){ return <section>Hero</section>; }",
            "src/components/InsightPanel.tsx": "export default function InsightPanel(){ return <section>Result</section>; }",
            "src/components/StatePanel.tsx": "export default function StatePanel(){ return <section>Loading empty error</section>; }",
        },
        "backend_code": {
            "main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
            "routes.py": "from fastapi import APIRouter\nrouter = APIRouter()\n",
            "requirements.txt": "fastapi\nuvicorn\n",
        },
    }

    result = await code_evaluator(state)

    assert result["code_eval_result"]["passed"] is False
    assert "src/components/WorkspacePanel.tsx" in result["code_eval_result"]["missing_frontend"]


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


@pytest.mark.asyncio
async def test_code_evaluator_returns_repair_tasks_for_blockers():
    result = await code_evaluator(
        {
            "blueprint": {
                "frontend_files": {"src/app/page.tsx": {}, "src/components/WorkspacePanel.tsx": {}},
                "backend_files": {"main.py": {}, "routes.py": {}, "requirements.txt": {}},
            },
            "frontend_code": {"src/app/page.tsx": "export default function Page(){ return <main />; }"},
            "backend_code": {"main.py": "from fastapi import FastAPI\napp = FastAPI()\n"},
            "execution_tasks": [
                {
                    "title": "prep block",
                    "target": "frontend",
                    "kind": "ui_object",
                    "success_signal": "visible",
                    "priority": "high",
                }
            ],
        }
    )

    repair_tasks = result["repair_tasks"]
    assert repair_tasks
    assert any(task["target"] == "frontend" for task in repair_tasks)
    assert result["task_distribution"]["total"] >= len(repair_tasks)


@pytest.mark.asyncio
async def test_code_evaluator_emits_result_event_when_config_provided():
    """Verify that code_evaluator emits a code_eval.result event with scores."""
    from unittest.mock import patch

    emitted_events = []

    async def _capture_event(name, payload, *, config):
        emitted_events.append({"name": name, "payload": payload})

    with patch("agent.nodes.code_evaluator.adispatch_custom_event", side_effect=_capture_event):
        await code_evaluator(
            {
                "blueprint": {
                    "frontend_files": {"package.json": {}, "src/app/page.tsx": {}},
                    "backend_files": {"main.py": {}, "requirements.txt": {}},
                },
                "frontend_code": {
                    "package.json": '{"dependencies":{"next":"15.0.0"}}',
                    "src/app/page.tsx": "export default function Page(){ return <main>Hello</main>; }",
                },
                "backend_code": {
                    "main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
                    "requirements.txt": "fastapi\nuvicorn\n",
                },
            },
            config={"configurable": {"thread_id": "test-thread"}},
        )

    assert len(emitted_events) == 1
    event = emitted_events[0]
    assert event["name"] == "code_eval.result"
    assert event["payload"]["type"] == "code_eval.result"
    assert "match_rate" in event["payload"]
    assert "iteration" in event["payload"]
    assert "passed" in event["payload"]
    assert event["payload"]["node"] == "code_evaluator"
