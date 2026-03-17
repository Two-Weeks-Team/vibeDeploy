"""Base protocol for provider adapters."""

from typing import Protocol, runtime_checkable

from langchain_core.language_models.chat_models import BaseChatModel


@runtime_checkable
class ProviderAdapter(Protocol):
    """Adapter protocol all provider implementations must satisfy."""

    @property
    def provider_name(self) -> str:
        """Canonical provider name, e.g. 'anthropic', 'openai', 'google'."""
        ...

    def create_langchain_llm(
        self,
        model_id: str,
        *,
        temperature: float,
        max_tokens: int,
        timeout: float,
        **kwargs,
    ) -> BaseChatModel:
        """Instantiate and return a LangChain chat model for the given model_id.

        Args:
            model_id: Canonical model identifier (already resolved from alias).
            temperature: Sampling temperature.
            max_tokens: Maximum output tokens.
            timeout: Request timeout in seconds.
            **kwargs: Additional provider-specific parameters.

        Returns:
            A configured BaseChatModel instance.

        Raises:
            NotImplementedError: If the provider does not support LangChain integration.
        """
        ...
