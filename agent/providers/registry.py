"""Provider adapter registry — canonical model routing and capability metadata."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from .base import ProviderAdapter


class ProviderModelSpec(TypedDict):
    provider: str
    model_id: str
    api_style: str
    supports_tools: bool
    max_context_tokens: int
    max_output_tokens: int


CAPABILITY_REGISTRY: dict[str, ProviderModelSpec] = {
    # --- OpenAI (doc 17 §4) ---
    "gpt-5.4": {
        "provider": "openai",
        "model_id": "gpt-5.4",
        "api_style": "openai_responses",
        "supports_tools": True,
        "max_context_tokens": 1_050_000,
        "max_output_tokens": 128_000,
    },
    "gpt-5.3-codex": {
        "provider": "openai",
        "model_id": "gpt-5.3-codex",
        "api_style": "openai_responses",
        "supports_tools": True,
        "max_context_tokens": 400_000,
        "max_output_tokens": 128_000,
    },
    "gpt-5.2": {
        "provider": "openai",
        "model_id": "gpt-5.2",
        "api_style": "openai_responses",
        "supports_tools": True,
        "max_context_tokens": 1_050_000,
        "max_output_tokens": 128_000,
    },
    # --- Anthropic (doc 17 §5) ---
    "claude-sonnet-4-6": {
        "provider": "anthropic",
        "model_id": "claude-sonnet-4-6",
        "api_style": "anthropic_messages",
        "supports_tools": True,
        "max_context_tokens": 1_000_000,
        "max_output_tokens": 64_000,
    },
    "claude-opus-4-6": {
        "provider": "anthropic",
        "model_id": "claude-opus-4-6",
        "api_style": "anthropic_messages",
        "supports_tools": True,
        "max_context_tokens": 1_000_000,
        "max_output_tokens": 64_000,
    },
    # --- Google (doc 17 §3) ---
    "gemini-3.1-pro-preview": {
        "provider": "google",
        "model_id": "gemini-3.1-pro-preview",
        "api_style": "google_generate_content",
        "supports_tools": True,
        "max_context_tokens": 1_000_000,
        "max_output_tokens": 65_536,
    },
    "gemini-3.1-pro-preview-customtools": {
        "provider": "google",
        "model_id": "gemini-3.1-pro-preview-customtools",
        "api_style": "google_generate_content",
        "supports_tools": True,
        "max_context_tokens": 1_000_000,
        "max_output_tokens": 65_536,
    },
    "gemini-3.1-flash-lite-preview": {
        "provider": "google",
        "model_id": "gemini-3.1-flash-lite-preview",
        "api_style": "google_generate_content",
        "supports_tools": False,
        "max_context_tokens": 1_000_000,
        "max_output_tokens": 65_536,
    },
}


LEGACY_MODEL_ALIASES: dict[str, str] = {}


def resolve_canonical(model_id: str) -> str:
    return LEGACY_MODEL_ALIASES.get(model_id, model_id)


def get_provider(model_id: str) -> str | None:
    """Return the provider name for a canonical model ID, or None if unknown."""
    canonical = resolve_canonical(model_id)
    spec = CAPABILITY_REGISTRY.get(canonical)
    return spec["provider"] if spec else None


class ProviderRegistry:
    """Routes model IDs to registered provider adapters."""

    def __init__(self) -> None:
        self._adapters: dict[str, "ProviderAdapter"] = {}
        self._initialized = False
        self._init_lock = threading.Lock()

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return

            from .anthropic_adapter import AnthropicAdapter
            from .google_adapter import GoogleAdapter
            from .openai_adapter import OpenAIAdapter

            self.register(AnthropicAdapter())
            self.register(OpenAIAdapter())
            self.register(GoogleAdapter())
            self._initialized = True

    def register(self, adapter: "ProviderAdapter") -> None:
        """Register a provider adapter under its provider_name."""
        self._adapters[adapter.provider_name] = adapter

    def get_adapter(self, model_id: str) -> "ProviderAdapter | None":
        """Return the adapter for model_id, or None if not in CAPABILITY_REGISTRY."""
        self._ensure_initialized()
        canonical = resolve_canonical(model_id)
        spec = CAPABILITY_REGISTRY.get(canonical)
        if spec is None:
            return None
        return self._adapters.get(spec["provider"])

    def get_llm(self, model_id: str, *, temperature: float, max_tokens: int, timeout: float, **kwargs):
        """Instantiate an LLM for model_id via the registered adapter.

        Returns None if model_id is not in CAPABILITY_REGISTRY or adapter raises NotImplementedError.
        """
        adapter = self.get_adapter(model_id)
        if adapter is None:
            return None
        canonical = resolve_canonical(model_id)
        try:
            return adapter.create_langchain_llm(
                canonical, temperature=temperature, max_tokens=max_tokens, timeout=timeout, **kwargs
            )
        except NotImplementedError:
            return None


registry = ProviderRegistry()


def _ensure_adapters_registered() -> None:
    """Backward-compatible shim — delegates to registry._ensure_initialized()."""
    registry._ensure_initialized()
