"""Google provider adapter — native genai SDK; no LangChain pipeline integration."""

from __future__ import annotations

import os
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel


class GoogleAdapter:
    _client = None

    @property
    def provider_name(self) -> str:
        return "google"

    def create_langchain_llm(
        self,
        model_id: str,
        *,
        temperature: float,
        max_tokens: int,
        timeout: float,
        **kwargs,
    ) -> BaseChatModel:
        raise NotImplementedError(
            f"Google model '{model_id}' does not use LangChain pipeline. Use get_client() + generate_content() instead."
        )

    def get_client(self):
        if self._client is not None:
            return self._client
        import google.genai as genai

        api_key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY environment variable is required")
        self._client = genai.Client(api_key=api_key)
        return self._client

    async def generate_content(
        self,
        model_id: str,
        prompt: str,
        *,
        response_schema: Any | None = None,
        temperature: float = 0.5,
        max_output_tokens: int = 8192,
    ) -> Any:
        import google.genai.types as genai_types

        client = self.get_client()
        generation_config_kwargs: dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }
        if response_schema is not None:
            generation_config_kwargs["response_schema"] = response_schema
            generation_config_kwargs["response_mime_type"] = "application/json"

        config = genai_types.GenerateContentConfig(**generation_config_kwargs)
        return await client.aio.models.generate_content(
            model=model_id,
            contents=prompt,
            config=config,
        )
