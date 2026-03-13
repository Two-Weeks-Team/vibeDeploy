import pytest

from agent.nodes.deployer import (
    _apply_deterministic_repairs,
    _build_table_prefix,
    _ensure_frontend_lockfile,
    _ensure_unique_backend_table_prefix,
    _generate_ci_yml,
    _get_deploy_blocker,
    _is_do_app_limit_error,
    _prepare_files_for_push,
    _reclaim_do_app_capacity,
)
from agent.tools.digitalocean import build_app_spec


@pytest.mark.asyncio
async def test_reclaim_do_app_capacity_deletes_oldest_failed_app(monkeypatch):
    deleted_ids = []

    async def fake_list_apps():
        return [
            {
                "id": "keep-live",
                "spec": {"name": "queuebite"},
                "live_url": "https://queuebite.example.com",
                "created_at": "2026-03-06T00:00:00Z",
                "active_deployment": {"phase": "ACTIVE"},
            },
            {
                "id": "keep-prod",
                "spec": {"name": "vibedeploy"},
                "live_url": "https://vibedeploy.example.com",
                "created_at": "2026-03-06T00:00:00Z",
                "active_deployment": {"phase": "ACTIVE"},
            },
            {
                "id": "old-failed",
                "spec": {"name": "recipe-box-lite"},
                "live_url": "",
                "created_at": "2026-03-10T04:14:41Z",
                "active_deployment": {"phase": "UNKNOWN"},
            },
            {
                "id": "new-failed",
                "spec": {"name": "bookmark-buddy-lite"},
                "live_url": "",
                "created_at": "2026-03-10T09:57:16Z",
                "active_deployment": {"phase": "UNKNOWN"},
            },
        ]

    async def fake_delete_app(app_id: str):
        deleted_ids.append(app_id)
        return {"status": "deleted", "app_id": app_id}

    async def fake_sleep(_seconds: float):
        return None

    monkeypatch.setattr("agent.nodes.deployer.list_apps", fake_list_apps)
    monkeypatch.setattr("agent.nodes.deployer.delete_app", fake_delete_app)
    monkeypatch.setattr("agent.nodes.deployer.asyncio.sleep", fake_sleep)

    result = await _reclaim_do_app_capacity("bookmarkbrain")

    assert result["status"] == "deleted"
    assert deleted_ids == ["old-failed"]


@pytest.mark.asyncio
async def test_reclaim_do_app_capacity_deletes_oldest_live_app_when_full(monkeypatch):
    deleted_ids = []

    async def fake_list_apps():
        return [
            {
                "id": "keep-prod",
                "spec": {"name": "vibedeploy"},
                "live_url": "https://vibedeploy.example.com",
                "created_at": "2026-03-06T00:00:00Z",
                "active_deployment": {"phase": "ACTIVE"},
            },
            {
                "id": "old-live",
                "spec": {"name": "queuebite"},
                "live_url": "https://queuebite.example.com",
                "created_at": "2026-03-06T00:00:00Z",
                "active_deployment": {"phase": "ACTIVE"},
            },
            {
                "id": "new-live",
                "spec": {"name": "spendsense"},
                "live_url": "https://spendsense.example.com",
                "created_at": "2026-03-10T09:57:16Z",
                "active_deployment": {"phase": "ACTIVE"},
            },
        ]

    async def fake_delete_app(app_id: str):
        deleted_ids.append(app_id)
        return {"status": "deleted", "app_id": app_id}

    async def fake_sleep(_seconds: float):
        return None

    monkeypatch.setattr("agent.nodes.deployer.list_apps", fake_list_apps)
    monkeypatch.setattr("agent.nodes.deployer.delete_app", fake_delete_app)
    monkeypatch.setattr("agent.nodes.deployer.asyncio.sleep", fake_sleep)

    result = await _reclaim_do_app_capacity("queuesmart")

    assert result["status"] == "deleted"
    assert deleted_ids == ["old-live"]


@pytest.mark.asyncio
async def test_reclaim_do_app_capacity_skips_in_progress_apps(monkeypatch):
    deleted_ids = []

    async def fake_list_apps():
        return [
            {
                "id": "deploying-app",
                "spec": {"name": "pawhealth-162626"},
                "live_url": "",
                "created_at": "2026-03-10T17:15:03Z",
                "active_deployment": {"phase": "UNKNOWN"},
                "in_progress_deployment": {"phase": "DEPLOYING"},
            },
            {
                "id": "old-failed",
                "spec": {"name": "queueflow-lite"},
                "live_url": "",
                "created_at": "2026-03-10T04:14:41Z",
                "active_deployment": {"phase": "ERROR"},
            },
        ]

    async def fake_delete_app(app_id: str):
        deleted_ids.append(app_id)
        return {"status": "deleted", "app_id": app_id}

    async def fake_sleep(_seconds: float):
        return None

    monkeypatch.setattr("agent.nodes.deployer.list_apps", fake_list_apps)
    monkeypatch.setattr("agent.nodes.deployer.delete_app", fake_delete_app)
    monkeypatch.setattr("agent.nodes.deployer.asyncio.sleep", fake_sleep)

    result = await _reclaim_do_app_capacity("studymate")

    assert result["status"] == "deleted"
    assert deleted_ids == ["old-failed"]


def test_is_do_app_limit_error_matches_expected_message():
    assert _is_do_app_limit_error({"status": "error", "error": "HTTP 429: App count of 11 exceeds limit of 10"})
    assert not _is_do_app_limit_error({"status": "error", "error": "something else"})


def test_ensure_unique_backend_table_prefix_uses_app_slug():
    files = {
        "models.py": 'TABLE_PREFIX = "ss_"\nclass User:\n    pass\n',
        "main.py": "print('ok')\n",
    }

    updated = _ensure_unique_backend_table_prefix(files, "smartspend-ai-159620")

    assert 'TABLE_PREFIX = "smartspend_ai_159620_"' in updated["models.py"]
    assert updated["main.py"] == files["main.py"]


def test_build_table_prefix_falls_back_for_empty_names():
    assert _build_table_prefix("###") == "app_"


@pytest.mark.asyncio
async def test_ensure_frontend_lockfile_adds_generated_lockfile(monkeypatch):
    async def fake_generate_package_lock(_package_json: str) -> str:
        return '{\n  "name": "paw-health",\n  "lockfileVersion": 3\n}\n'

    monkeypatch.setattr("agent.nodes.deployer._generate_package_lock", fake_generate_package_lock)

    files = {
        "main.py": "print('ok')\n",
        "web/package.json": '{ "name": "paw-health", "private": true }\n',
    }

    updated = await _ensure_frontend_lockfile(files)

    assert updated["web/package-lock.json"].startswith("{")
    assert '"lockfileVersion": 3' in updated["web/package-lock.json"]


@pytest.mark.asyncio
async def test_ensure_frontend_lockfile_replaces_empty_lockfile(monkeypatch):
    async def fake_generate_package_lock(_package_json: str) -> str:
        return '{\n  "name": "paw-health",\n  "lockfileVersion": 3,\n  "packages": {}\n}\n'

    monkeypatch.setattr("agent.nodes.deployer._generate_package_lock", fake_generate_package_lock)

    files = {
        "main.py": "print('ok')\n",
        "web/package.json": '{ "name": "paw-health", "private": true }\n',
        "web/package-lock.json": "",
    }

    updated = await _ensure_frontend_lockfile(files)

    assert '"lockfileVersion": 3' in updated["web/package-lock.json"]


@pytest.mark.asyncio
async def test_prepare_files_for_push_canonicalizes_repaired_use_client_directives():
    files = {
        "web/src/components/Hero.tsx": (
            "use client;\n\n"
            "type HeroProps = { appName: string };\n"
            "export default function Hero({ appName }: HeroProps) { return <section>{appName}</section>; }\n"
        ),
        "web/src/components/WorkspacePanel.tsx": (
            "use client;\n\n"
            "export default function WorkspacePanel() {\n"
            "  return <button onClick={() => null}>Generate</button>;\n"
            "}\n"
        ),
    }

    updated = await _prepare_files_for_push(files)

    assert updated["web/src/components/Hero.tsx"].startswith('"use client";')
    assert updated["web/src/components/WorkspacePanel.tsx"].startswith('"use client";')


@pytest.mark.asyncio
async def test_prepare_files_for_push_adds_use_client_to_interactive_repairs():
    files = {
        "web/src/components/WorkspacePanel.tsx": (
            "export default function WorkspacePanel() {\n  return <textarea onChange={() => null} />;\n}\n"
        )
    }

    updated = await _prepare_files_for_push(files)

    assert updated["web/src/components/WorkspacePanel.tsx"].startswith('"use client";')


def test_build_app_spec_frontend_build_command_falls_back_to_npm_install():
    spec = build_app_spec("pawhealth", "https://github.com/Two-Weeks-Team/pawhealth-162626.git", has_frontend=True)

    web_service = next(service for service in spec["services"] if service["name"].endswith("-web"))

    assert web_service["build_command"] == (
        "if [ -s package-lock.json ]; then npm ci || npm install; else npm install; fi && npm run build"
    )


def test_generate_ci_yml_frontend_install_falls_back_when_lockfile_is_empty_or_invalid():
    yml = _generate_ci_yml(has_frontend=True)

    assert "if [ -s package-lock.json ]; then" in yml
    assert "npm ci || npm install" in yml


def test_get_deploy_blocker_rejects_docs_only_bundle():
    blocker = _get_deploy_blocker(
        frontend_code={},
        backend_code={},
        blueprint={
            "frontend_files": {"package.json": {}, "src/app/page.tsx": {}},
            "backend_files": {"main.py": {}, "requirements.txt": {}},
        },
    )

    assert blocker == "missing backend files: main.py, requirements.txt"


def test_get_deploy_blocker_accepts_full_stack_bundle():
    blocker = _get_deploy_blocker(
        frontend_code={
            "package.json": '{"name":"demo","private":true}',
            "src/app/layout.tsx": "export default function Layout({ children }) { return <html><body>{children}</body></html>; }",
            "src/app/page.tsx": "export default function Page() { return <main>Demo</main>; }",
        },
        backend_code={
            "main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
            "requirements.txt": "fastapi\nuvicorn\n",
        },
        blueprint={
            "frontend_files": {"package.json": {}, "src/app/page.tsx": {}},
            "backend_files": {"main.py": {}, "requirements.txt": {}},
        },
    )

    assert blocker is None


def test_get_deploy_blocker_rejects_failed_code_eval_even_with_files_present():
    blocker = _get_deploy_blocker(
        frontend_code={
            "package.json": '{"name":"demo","private":true}',
            "src/app/layout.tsx": "export default function Layout({ children }) { return <html><body>{children}</body></html>; }",
            "src/app/page.tsx": "export default function Page() { return <main>Demo</main>; }",
        },
        backend_code={
            "main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
            "requirements.txt": "fastapi\nuvicorn\n",
        },
        blueprint={
            "frontend_files": {"package.json": {}, "src/app/page.tsx": {}},
            "backend_files": {"main.py": {}, "requirements.txt": {}},
        },
        code_eval_result={
            "passed": False,
            "deployment_blocked": True,
            "blockers": ["deterministic fallback scaffold detected"],
        },
    )

    assert blocker == "deterministic fallback scaffold detected"


def test_get_deploy_blocker_allows_high_quality_flagship_fallback_bundle():
    blocker = _get_deploy_blocker(
        frontend_code={
            ".vibedeploy-fallback-frontend.json": '{"kind":"frontend"}',
            "package.json": '{"name":"demo","private":true}',
            "src/app/layout.tsx": "export default function Layout({ children }) { return <html><body>{children}</body></html>; }",
            "src/app/page.tsx": "export default function Page() { return <main>Demo</main>; }",
        },
        backend_code={
            "main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
            "requirements.txt": "fastapi\nuvicorn\n",
        },
        blueprint={
            "frontend_files": {"package.json": {}, "src/app/page.tsx": {}},
            "backend_files": {"main.py": {}, "requirements.txt": {}},
        },
        code_eval_result={
            "passed": False,
            "deployment_blocked": True,
            "blockers": ["deterministic fallback scaffold detected"],
            "completeness": 100,
            "runnability": 95,
            "experience": 98,
        },
        selected_flagship="creator-batch-studio",
    )

    assert blocker is None


@pytest.mark.asyncio
async def test_local_fallback_deploy_reports_local_app_dir(tmp_path, monkeypatch):
    from agent.nodes import deployer as deployer_module

    monkeypatch.setattr(deployer_module, "_find_free_port", lambda start_port=9100: start_port)

    async def _fake_spawn(*args, **kwargs):
        return None

    monkeypatch.setattr(deployer_module, "_spawn_background_process", _fake_spawn)

    result = await deployer_module._local_fallback_deploy(
        "creator-batch-studio-test",
        {
            "main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
            "requirements.txt": "fastapi\nuvicorn\n",
        },
        "",
        "github_token_missing",
    )

    assert result["deploy_result"]["status"] == "local_running"
    assert result["deploy_result"]["local_app_dir"].endswith("creator-batch-studio-test")


def test_apply_deterministic_repairs_relaxes_layout_literal_type_errors():
    files = {
        "web/src/app/page.tsx": (
            '"use client";\n\n'
            'const LAYOUT = "operations_console";\n\n'
            "export default function Page() {\n"
            '  if (LAYOUT === "storyboard") return <main>Storyboard</main>;\n'
            '  if (LAYOUT === "operations_console") return <main>Console</main>;\n'
            "  return null;\n"
            "}\n"
        )
    }
    error_logs = (
        "./src/app/page.tsx:117:9\n"
        "Type error: This comparison appears to be unintentional because the types "
        "'\"operations_console\"' and '\"storyboard\"' have no overlap.\n"
    )

    repaired = _apply_deterministic_repairs(files, error_logs)

    assert 'const LAYOUT: string = "operations_console";' in repaired["web/src/app/page.tsx"]


def test_apply_deterministic_repairs_fixes_typescript_nullable_property_access():
    files = {
        "web/src/app/page.tsx": (
            '"use client";\n'
            "export default function Page() {\n"
            "  const selectedHabit = { id: 'habit-1' } as { id: string } | null;\n"
            "  async function getCoaching() {\n"
            "    const res = await fetch(`/api/habits/${selectedHabit.id}/coaching`);\n"
            "    return res;\n"
            "  }\n"
            "  return null;\n"
            "}\n"
        )
    }
    error_logs = "./src/app/page.tsx:5:44\nType error: 'selectedHabit' is possibly 'null'.\n"

    repaired = _apply_deterministic_repairs(files, error_logs)

    assert "selectedHabit!.id" in repaired["web/src/app/page.tsx"]


def test_apply_deterministic_repairs_adds_missing_sqlalchemy_import():
    files = {
        "models.py": (
            "from sqlalchemy import (\n"
            "    Column,\n"
            "    String,\n"
            "    DateTime,\n"
            ")\n"
            "\n"
            "value = Column(Integer, nullable=False)\n"
        )
    }
    error_logs = (
        'File "/workspace/models.py", line 7, in HabitMilestone\n'
        "    value = Column(Integer, nullable=False)\n"
        "                   ^^^^^^^\n"
        "NameError: name 'Integer' is not defined\n"
    )

    repaired = _apply_deterministic_repairs(files, error_logs)

    assert "    Integer,\n" in repaired["models.py"]


def test_apply_deterministic_repairs_fixes_pydantic_field_type_clash():
    files = {
        "routes.py": (
            "from pydantic import BaseModel, Field\n"
            "from datetime import date\n"
            "\n"
            "class CheckInIn(BaseModel):\n"
            '    date: date = Field(..., description="Date of the check-in")\n'
        )
    }
    error_logs = (
        'File "/workspace/routes.py", line 4, in <module>\n'
        "    class CheckInIn(BaseModel):\n"
        '        date: date = Field(..., description="Date of the check-in")\n'
        "pydantic.errors.PydanticUserError: Error when building FieldInfo from annotated attribute. "
        "Make sure you don't have any field name clashing with a type annotation\n"
    )

    repaired = _apply_deterministic_repairs(files, error_logs)

    assert "from datetime import date as date_type" in repaired["routes.py"]
    assert "date: date_type = Field" in repaired["routes.py"]


def test_apply_deterministic_repairs_removes_use_client_from_layout_metadata_error():
    files = {
        "web/src/app/layout.tsx": (
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
    error_logs = (
        './src/app/layout.tsx:4:1\nYou are attempting to export "metadata" from a component marked with "use client"\n'
    )

    repaired = _apply_deterministic_repairs(files, error_logs)

    assert not repaired["web/src/app/layout.tsx"].lstrip().startswith('"use client";')


def test_apply_deterministic_repairs_canonicalizes_broken_use_client_directive():
    files = {
        "web/src/components/Rehearsal.tsx": (
            "\"use client';\nexport default function Rehearsal() {\n  return null;\n}\n"
        )
    }
    error_logs = "./src/components/Rehearsal.tsx:1:1\nError: Unterminated string constant\n"

    repaired = _apply_deterministic_repairs(files, error_logs)

    assert repaired["web/src/components/Rehearsal.tsx"].startswith('"use client";')


def test_apply_deterministic_repairs_avoids_duplicate_sslmode_query_params():
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
    error_logs = (
        "sqlalchemy.exc.OperationalError: (psycopg.OperationalError) "
        "connection is bad: invalid sslmode value: \"('require', 'require')\"\n"
    )

    repaired = _apply_deterministic_repairs(files, error_logs)

    assert 'and "sslmode=" not in _raw_url.lower()' in repaired["models.py"]
