from unittest.mock import MagicMock, patch

import pytest

from agent.nodes.build_validator import (
    _ast_check_python_files,
    _check_design_quality,
    _write_files_to_tmpdir,
    build_validator,
)


def test_ast_check_python_files_passes_valid_code():
    files = {"main.py": "from fastapi import FastAPI\napp = FastAPI()\n"}
    assert _ast_check_python_files(files) == []


def test_ast_check_python_files_catches_syntax_error():
    files = {"main.py": "def broken(\n    pass\n"}
    errors = _ast_check_python_files(files)
    assert len(errors) == 1
    assert "main.py" in errors[0]
    assert "SyntaxError" in errors[0]


def test_ast_check_python_files_skips_non_python_files():
    files = {"requirements.txt": "fastapi\nuvicorn\n", "main.py": "x = 1\n"}
    assert _ast_check_python_files(files) == []


def test_ast_check_python_files_returns_all_errors_for_multiple_bad_files():
    files = {
        "main.py": "def ok(): pass\n",
        "routes.py": "def broken(\n    pass\n",
        "models.py": "class Bad(:\n    pass\n",
    }
    errors = _ast_check_python_files(files)
    assert len(errors) == 2
    paths = [e.split(":")[0] for e in errors]
    assert "routes.py" in paths
    assert "models.py" in paths


@pytest.mark.asyncio
async def test_build_validator_returns_skipped_when_docker_not_installed():
    with patch.dict("sys.modules", {"docker": None, "docker.errors": None}):
        result = await build_validator(
            {
                "backend_code": {"main.py": "x = 1\n", "requirements.txt": "fastapi\n"},
                "frontend_code": {},
            }
        )

    assert result["build_validation"]["passed"] is True
    assert result["build_validation"]["skipped"] is True
    assert result["build_validation"]["reason"] == "Docker not available"


@pytest.mark.asyncio
async def test_build_validator_returns_skipped_when_docker_daemon_unavailable():
    mock_docker = MagicMock()
    mock_docker.from_env.side_effect = Exception("Cannot connect to Docker daemon")

    with patch.dict("sys.modules", {"docker": mock_docker, "docker.errors": MagicMock()}):
        result = await build_validator(
            {
                "backend_code": {"main.py": "x = 1\n", "requirements.txt": "fastapi\n"},
                "frontend_code": {},
            }
        )

    assert result["build_validation"]["passed"] is True
    assert result["build_validation"]["skipped"] is True
    assert result["build_validation"]["reason"] == "Docker not available"


@pytest.mark.asyncio
async def test_build_validator_catches_python_syntax_error_before_docker():
    result = await build_validator(
        {
            "backend_code": {"main.py": "def broken(\n    pass\n", "requirements.txt": "fastapi\n"},
            "frontend_code": {},
        }
    )

    assert result["build_validation"]["passed"] is False
    assert result["build_validation"]["backend_ok"] is False
    assert len(result["build_validation"]["errors"]) >= 1
    assert "main.py" in result["build_validation"]["errors"][0]


@pytest.mark.asyncio
async def test_build_validator_returns_passed_when_docker_succeeds():
    mock_docker_module = MagicMock()
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    mock_client.containers.run.return_value = b""
    mock_docker_module.from_env.return_value = mock_client

    with patch.dict("sys.modules", {"docker": mock_docker_module, "docker.errors": MagicMock()}):
        result = await build_validator(
            {
                "backend_code": {
                    "main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
                    "requirements.txt": "fastapi\n",
                },
                "frontend_code": {"package.json": '{"name":"demo","scripts":{"build":"echo ok"}}'},
            }
        )

    assert result["build_validation"]["passed"] is True
    assert result["build_validation"]["backend_ok"] is True
    assert result["build_validation"]["frontend_ok"] is True


@pytest.mark.asyncio
async def test_build_validator_returns_failed_when_backend_docker_fails():
    mock_docker_module = MagicMock()
    mock_client = MagicMock()
    mock_client.ping.return_value = True

    container_error = Exception("ModuleNotFoundError: No module named 'fastapi'")
    container_error.stderr = b"ModuleNotFoundError: No module named 'fastapi'"
    mock_client.containers.run.side_effect = container_error
    mock_docker_module.from_env.return_value = mock_client

    with patch.dict("sys.modules", {"docker": mock_docker_module, "docker.errors": MagicMock()}):
        result = await build_validator(
            {
                "backend_code": {"main.py": "import fastapi\n", "requirements.txt": "fastapi\n"},
                "frontend_code": {},
            }
        )

    assert result["build_validation"]["passed"] is False
    assert result["build_validation"]["backend_ok"] is False
    assert len(result["build_validation"]["errors"]) >= 1


@pytest.mark.asyncio
async def test_build_validator_returns_failed_when_frontend_docker_fails():
    mock_docker_module = MagicMock()
    mock_client = MagicMock()
    mock_client.ping.return_value = True

    frontend_error = Exception("npm ERR! missing script: build")
    frontend_error.stderr = b"npm ERR! missing script: build"
    mock_client.containers.run.side_effect = frontend_error
    mock_docker_module.from_env.return_value = mock_client

    with patch.dict("sys.modules", {"docker": mock_docker_module, "docker.errors": MagicMock()}):
        result = await build_validator(
            {
                "backend_code": {},
                "frontend_code": {"package.json": '{"name":"demo"}'},
            }
        )

    assert result["build_validation"]["passed"] is False
    assert result["build_validation"]["frontend_ok"] is False
    assert len(result["build_validation"]["errors"]) >= 1


@pytest.mark.asyncio
async def test_build_validator_skips_backend_docker_when_missing_required_files():
    mock_docker_module = MagicMock()
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    mock_client.containers.run.return_value = b""
    mock_docker_module.from_env.return_value = mock_client

    with patch.dict("sys.modules", {"docker": mock_docker_module, "docker.errors": MagicMock()}):
        result = await build_validator(
            {
                "backend_code": {"utils.py": "def helper(): pass\n"},
                "frontend_code": {},
            }
        )

    mock_client.containers.run.assert_not_called()
    assert result["build_validation"]["passed"] is True


@pytest.mark.asyncio
async def test_build_validator_handles_empty_state():
    result = await build_validator({})

    assert "build_validation" in result
    assert result["build_validation"]["passed"] is True


def test_write_files_to_tmpdir_creates_nested_paths(tmp_path):
    files = {
        "main.py": "x = 1\n",
        "sub/utils.py": "y = 2\n",
    }
    _write_files_to_tmpdir(files, str(tmp_path))

    assert (tmp_path / "main.py").read_text() == "x = 1\n"
    assert (tmp_path / "sub" / "utils.py").read_text() == "y = 2\n"


def test_write_files_to_tmpdir_skips_non_string_values(tmp_path):
    files = {"main.py": "x = 1\n", "bad.py": None}
    _write_files_to_tmpdir(files, str(tmp_path))

    assert (tmp_path / "main.py").exists()
    assert not (tmp_path / "bad.py").exists()


@pytest.mark.asyncio
async def test_build_validator_emits_events_when_config_provided():
    """Verify that build_validator emits SSE events when a config is supplied."""
    emitted_events = []

    async def _capture_event(name, payload, *, config):
        emitted_events.append({"name": name, "payload": payload})

    with (
        patch("agent.nodes.build_validator.adispatch_custom_event", side_effect=_capture_event),
        patch.dict("sys.modules", {"docker": None, "docker.errors": None}),
    ):
        result = await build_validator(
            {
                "backend_code": {"main.py": "x = 1\n", "requirements.txt": "fastapi\n"},
                "frontend_code": {},
            },
            config={"configurable": {"thread_id": "test-thread"}},
        )

    assert result["build_validation"]["passed"] is True  # Docker skipped
    assert len(emitted_events) >= 2  # At least node.start and node.complete
    event_types = [e["payload"]["type"] for e in emitted_events]
    assert "build.node.start" in event_types
    # Should have complete or skip event
    assert any(t in event_types for t in ("build.node.complete",))


@pytest.mark.asyncio
async def test_build_validator_emits_error_event_on_syntax_failure():
    """Verify that build_validator emits an error event when Python syntax check fails."""
    emitted_events = []

    async def _capture_event(name, payload, *, config):
        emitted_events.append({"name": name, "payload": payload})

    with patch("agent.nodes.build_validator.adispatch_custom_event", side_effect=_capture_event):
        result = await build_validator(
            {
                "backend_code": {"main.py": "def broken(\n    pass\n", "requirements.txt": "fastapi\n"},
                "frontend_code": {},
            },
            config={"configurable": {"thread_id": "test-thread"}},
        )

    assert result["build_validation"]["passed"] is False
    event_types = [e["payload"]["type"] for e in emitted_events]
    assert "build.node.start" in event_types
    assert "build.node.error" in event_types


_GOOD_GLOBALS_CSS = """:root {
  --background: 0 0% 100%;
  --foreground: 222.2 84% 4.9%;
  --card: 0 0% 100%;
  --card-foreground: 222.2 84% 4.9%;
  --popover: 0 0% 100%;
  --popover-foreground: 222.2 84% 4.9%;
  --primary: 222.2 47.4% 11.2%;
  --primary-foreground: 210 40% 98%;
  --secondary: 210 40% 96%;
  --secondary-foreground: 222.2 47.4% 11.2%;
  --muted: 210 40% 96%;
  --muted-foreground: 215.4 16.3% 46.9%;
}
.dark {
  --background: 222.2 84% 4.9%;
}
"""


def test_check_design_quality_passes_with_valid_code():
    frontend_code = {
        "src/app/globals.css": _GOOD_GLOBALS_CSS,
        "page.tsx": "export default function Page() { return <div className='bg-background p-4'>OK</div>; }\n",
    }
    assert _check_design_quality(frontend_code) == []


def test_check_design_quality_fails_when_css_variables_below_minimum():
    sparse_css = (
        ":root {\n  --primary: 222 47% 11%;\n  --secondary: 210 40% 96%;\n}\n.dark {\n  --primary: 210 40% 98%;\n}\n"
    )
    errors = _check_design_quality({"src/app/globals.css": sparse_css})
    assert len(errors) == 1
    assert "globals.css has only 3 CSS variables (minimum 12)" in errors[0]
    assert errors[0].startswith("DESIGN:")


def test_check_design_quality_fails_when_bg_white_hardcoded_in_tsx():
    frontend_code = {
        "src/app/globals.css": _GOOD_GLOBALS_CSS,
        "page.tsx": 'export default function Page() { return <div className="bg-white p-4">Bad</div>; }\n',
    }
    errors = _check_design_quality(frontend_code)
    assert len(errors) == 1
    assert "page.tsx contains bg-white" in errors[0]
    assert errors[0].startswith("DESIGN:")
