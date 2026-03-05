"""LLM factory — strips 'openai-' prefix from DO Gradient model names for local OpenAI API use."""

import os


def _gradient_to_openai(model: str) -> str:
    if model.startswith("openai-"):
        return model[len("openai-") :]
    return model


def content_to_str(content) -> str:
    """Normalize LLM response content — some models return list of content blocks."""
    if isinstance(content, list):
        return "".join(block.get("text", "") if isinstance(block, dict) else str(block) for block in content)
    return str(content) if not isinstance(content, str) else content


def get_llm(model: str, temperature: float = 0.5, max_tokens: int = 3000):
    provider = os.getenv("LLM_PROVIDER", "openai")

    if provider == "gradient":
        from langchain_gradient import ChatGradient

        return ChatGradient(model=model, temperature=temperature, max_tokens=max_tokens)

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=_gradient_to_openai(model),
        temperature=temperature,
        max_tokens=max_tokens,
    )
