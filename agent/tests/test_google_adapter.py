"""Tests for Google Gemini adapter (issue #53)."""

import pytest

from agent.providers.google_adapter import GoogleAdapter
from agent.providers.registry import CAPABILITY_REGISTRY, resolve_canonical


def test_google_adapter_provider_name():
    adapter = GoogleAdapter()
    assert adapter.provider_name == "google"


def test_google_adapter_raises_for_langchain():
    adapter = GoogleAdapter()
    with pytest.raises(NotImplementedError, match="does not use LangChain"):
        adapter.create_langchain_llm("gemini-3.1-pro-preview", temperature=0.5, max_tokens=4000, timeout=60.0)


def test_google_adapter_get_client_requires_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    adapter = GoogleAdapter()
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        adapter.get_client()


def test_google_adapter_get_client_uses_gemini_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    adapter = GoogleAdapter()
    client = adapter.get_client()
    assert client is not None


def test_google_adapter_get_client_uses_google_key_fallback(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    adapter = GoogleAdapter()
    client = adapter.get_client()
    assert client is not None


def test_canonical_gemini_models_in_registry():
    required = {
        "gemini-3.1-pro-preview",
        "gemini-3.1-pro-preview-customtools",
        "gemini-3.1-flash-lite-preview",
    }
    assert required <= set(CAPABILITY_REGISTRY.keys())


def test_all_gemini_models_route_to_google():
    for model_id, spec in CAPABILITY_REGISTRY.items():
        if "gemini" in model_id:
            assert spec["provider"] == "google"
            assert spec["api_style"] == "google_generate_content"


def test_legacy_gemini_alias_resolves():
    assert resolve_canonical("google-gemini-3.1-pro") == "gemini-3.1-pro-preview"
    assert resolve_canonical("google-gemini-3.1-flash-lite-preview") == "gemini-3.1-flash-lite-preview"


def test_canonical_gemini_id_is_identity():
    assert resolve_canonical("gemini-3.1-pro-preview") == "gemini-3.1-pro-preview"
    assert resolve_canonical("gemini-3.1-flash-lite-preview") == "gemini-3.1-flash-lite-preview"


def test_flash_lite_does_not_support_tools():
    spec = CAPABILITY_REGISTRY["gemini-3.1-flash-lite-preview"]
    assert spec["supports_tools"] is False


def test_pro_preview_supports_tools():
    spec = CAPABILITY_REGISTRY["gemini-3.1-pro-preview"]
    assert spec["supports_tools"] is True
