"""Anthropic provider adapter — wraps ChatAnthropic for the registry."""

from __future__ import annotations

import os

from langchain_core.language_models.chat_models import BaseChatModel


class AnthropicAdapter:
    @property
    def provider_name(self) -> str:
        return "anthropic"

    def create_langchain_llm(
        self,
        model_id: str,
        *,
        temperature: float,
        max_tokens: int,
        timeout: float,
        **kwargs,
    ) -> BaseChatModel:
        from langchain_anthropic import ChatAnthropic

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        coerced_temp = min(max(float(temperature), 0.0), 1.0)

        chat_kwargs: dict = {
            "model": model_id,
            "api_key": api_key,
            "temperature": coerced_temp,
            "max_tokens": max(256, max_tokens),
            "timeout": timeout,
            "max_retries": 3,
        }

        if os.getenv("VIBEDEPLOY_ENABLE_THINKING", "").strip().lower() in {"1", "true", "yes"}:
            chat_kwargs["model_kwargs"] = {"thinking": {"type": "adaptive"}}

        return ChatAnthropic(**chat_kwargs)
