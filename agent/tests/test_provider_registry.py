import pytest

from agent.providers.registry import (
    CAPABILITY_REGISTRY,
    _ensure_adapters_registered,
    registry,
    resolve_canonical,
)


def test_resolve_legacy_anthropic_alias():
    assert resolve_canonical("anthropic-claude-4.6-sonnet") == "claude-sonnet-4-6"


def test_resolve_legacy_openai_alias():
    assert resolve_canonical("openai-gpt-5.4") == "gpt-5.4"


def test_resolve_unknown_passes_through():
    assert resolve_canonical("openai-gpt-oss-120b") == "openai-gpt-oss-120b"


def test_resolve_canonical_is_identity():
    assert resolve_canonical("claude-sonnet-4-6") == "claude-sonnet-4-6"


def test_registry_routes_anthropic():
    _ensure_adapters_registered()
    adapter = registry.get_adapter("anthropic-claude-4.6-sonnet")
    assert adapter is not None
    assert adapter.provider_name == "anthropic"


def test_registry_routes_openai():
    _ensure_adapters_registered()
    adapter = registry.get_adapter("openai-gpt-5.4")
    assert adapter is not None
    assert adapter.provider_name == "openai"


def test_registry_routes_google():
    _ensure_adapters_registered()
    adapter = registry.get_adapter("gemini-3.1-pro-preview")
    assert adapter is not None
    assert adapter.provider_name == "google"


def test_registry_returns_none_for_do_only():
    _ensure_adapters_registered()
    adapter = registry.get_adapter("openai-gpt-oss-120b")
    assert adapter is None


def test_anthropic_adapter_creates_llm(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    _ensure_adapters_registered()
    adapter = registry.get_adapter("anthropic-claude-4.6-sonnet")
    assert adapter is not None
    llm = adapter.create_langchain_llm("claude-sonnet-4-6", temperature=0.5, max_tokens=1024, timeout=30.0)
    assert hasattr(llm, "ainvoke") or hasattr(llm, "bind_tools")


def test_openai_adapter_creates_llm(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    _ensure_adapters_registered()
    adapter = registry.get_adapter("openai-gpt-5.4")
    assert adapter is not None
    llm = adapter.create_langchain_llm("gpt-5.4", temperature=0.5, max_tokens=1024, timeout=30.0)
    assert hasattr(llm, "ainvoke") or hasattr(llm, "bind_tools")


def test_google_adapter_raises_for_langchain():
    _ensure_adapters_registered()
    adapter = registry.get_adapter("gemini-3.1-pro-preview")
    assert adapter is not None
    with pytest.raises(NotImplementedError):
        adapter.create_langchain_llm("gemini-3.1-pro-preview", temperature=0.5, max_tokens=1024, timeout=30.0)


def test_all_doc17_models_in_registry():
    required = {
        "gpt-5.4",
        "gpt-5.3-codex",
        "gpt-5.2",
        "claude-sonnet-4-6",
        "claude-opus-4-6",
        "gemini-3.1-pro-preview",
        "gemini-3.1-pro-preview-customtools",
        "gemini-3.1-flash-lite-preview",
    }
    assert required.issubset(CAPABILITY_REGISTRY.keys())
