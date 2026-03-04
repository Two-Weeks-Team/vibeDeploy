"""LLM factory — abstracts provider selection for local dev vs DigitalOcean production.

Usage:
    from ..llm import get_llm

    llm = get_llm(model="openai-gpt-5-mini", temperature=0.5, max_tokens=3000)

Environment variables:
    LLM_PROVIDER: "openai" (default, local) or "gradient" (DO production)
    OPENAI_API_KEY: Required when LLM_PROVIDER=openai
    DIGITALOCEAN_INFERENCE_KEY: Required when LLM_PROVIDER=gradient
"""

import os

# DO Gradient model names → OpenAI equivalents
_OPENAI_MODEL_MAP: dict[str, str] = {
    "openai-gpt-5-mini": "gpt-4o-mini",
    "openai-gpt-5": "gpt-4o",
    "openai-gpt-5.3-codex": "gpt-4o",
    "anthropic-claude-4.6-sonnet": "gpt-4o",
    "openai-gpt-4o": "gpt-4o",
}


def get_llm(model: str, temperature: float = 0.5, max_tokens: int = 3000):
    provider = os.getenv("LLM_PROVIDER", "openai")

    if provider == "gradient":
        from langchain_gradient import ChatGradient

        return ChatGradient(model=model, temperature=temperature, max_tokens=max_tokens)

    from langchain_openai import ChatOpenAI

    mapped_model = _OPENAI_MODEL_MAP.get(model, "gpt-4o-mini")
    return ChatOpenAI(model=mapped_model, temperature=temperature, max_tokens=max_tokens)
