"""OpenAI provider adapter — direct API (not DO Inference) via ChatOpenAI."""

from __future__ import annotations

import os

from langchain_core.language_models.chat_models import BaseChatModel

from .registry import CAPABILITY_REGISTRY


class OpenAIAdapter:
    @property
    def provider_name(self) -> str:
        return "openai"

    def create_langchain_llm(
        self,
        model_id: str,
        *,
        temperature: float,
        max_tokens: int,
        timeout: float,
        **kwargs,
    ) -> BaseChatModel:
        from langchain_openai import ChatOpenAI

        api_key = os.environ.get("OPENAI_API_KEY", "")
        spec = CAPABILITY_REGISTRY.get(model_id, {})
        uses_responses_api = spec.get("api_style") == "openai_responses"

        return ChatOpenAI(
            model=model_id,
            api_key=api_key,
            temperature=float(temperature),
            max_tokens=max(256, max_tokens),
            request_timeout=timeout,
            use_responses_api=uses_responses_api,
        )
