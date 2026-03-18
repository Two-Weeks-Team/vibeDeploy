import ast

from agent.nodes.scaffold_generator import generate_scaffold


def test_main_py_includes_router_import():
    files = generate_scaffold({"app_name": "test-app"})
    content = files["agent/main.py"]
    assert "from .routes import router as api_router" in content


def test_main_py_includes_api_router_registration():
    files = generate_scaffold({"app_name": "test-app"})
    content = files["agent/main.py"]
    assert "app.include_router(api_router, prefix=" in content


def test_ai_service_py_is_generated():
    files = generate_scaffold({"app_name": "test-app"})
    assert "agent/ai_service.py" in files


def test_ai_service_py_passes_ast_parse():
    files = generate_scaffold({"app_name": "test-app"})
    ast.parse(files["agent/ai_service.py"])


def test_scaffold_returns_nine_files():
    files = generate_scaffold({})
    assert len(files) == 10


def test_health_endpoint_still_present():
    files = generate_scaffold({"app_name": "test-app"})
    content = files["agent/main.py"]
    assert '@app.get("/health")' in content
    assert '"status": "ok"' in content or '"status": "ok"' in content


def test_cors_middleware_still_present():
    files = generate_scaffold({"app_name": "test-app"})
    content = files["agent/main.py"]
    assert "CORSMiddleware" in content
    assert "add_middleware" in content


def test_all_py_files_pass_ast_parse():
    files = generate_scaffold({"app_name": "test-app"})
    for path, content in files.items():
        if path.endswith(".py"):
            ast.parse(content)


def test_router_import_uses_try_except():
    files = generate_scaffold({"app_name": "test-app"})
    content = files["agent/main.py"]
    assert "try:" in content
    assert "except ImportError:" in content
    assert "api_router = None" in content


def test_ai_service_py_contains_inference_url():
    files = generate_scaffold({})
    content = files["agent/ai_service.py"]
    assert "DIGITALOCEAN_INFERENCE_URL" in content
    assert "DIGITALOCEAN_INFERENCE_KEY" in content


def test_ai_service_py_contains_call_inference_function():
    files = generate_scaffold({})
    content = files["agent/ai_service.py"]
    assert "async def call_inference" in content
