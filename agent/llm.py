"""LLM factory — routes all calls through DO Serverless Inference with direct OpenAI fallback."""

import os

DO_INFERENCE_BASE_URL = "https://inference.do-ai.run/v1"

MODEL_CONFIG = {
    "council": "anthropic-claude-4.6-sonnet",
    "strategist": "openai-gpt-5.2",
    "cross_exam": "openai-gpt-5.2",
    "code_gen": "anthropic-claude-opus-4.6",
    "ci_repair": "anthropic-claude-opus-4.6",
    "doc_gen": "anthropic-claude-4.6-sonnet",
    "image": "openai-gpt-image-1",
    "brainstorm": "anthropic-claude-4.6-sonnet",
    "brainstorm_synthesis": "openai-gpt-5.2",
    "input": "anthropic-claude-4.6-sonnet",
    "decision": "anthropic-claude-4.6-sonnet",
    "web_search": "openai-gpt-5-mini",
}


def _strip_openai_prefix(model: str) -> str:
    """Strip 'openai-' prefix for direct OpenAI API calls."""
    if model.startswith("openai-"):
        return model[len("openai-") :]
    return model


def content_to_str(content) -> str:
    """Normalize LLM response content — some models return list of content blocks."""
    if isinstance(content, list):
        return "".join(block.get("text", "") if isinstance(block, dict) else str(block) for block in content)
    return str(content) if not isinstance(content, str) else content


def get_llm(model: str, temperature: float = 0.5, max_tokens: int = 3000):
    """Route LLM calls through DO Inference when key is available, else direct OpenAI."""
    inference_key = os.getenv("DIGITALOCEAN_INFERENCE_KEY", "")

    if inference_key and inference_key not in ("test-key", ""):
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            api_key=inference_key,
            base_url=DO_INFERENCE_BASE_URL,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=_strip_openai_prefix(model),
        temperature=temperature,
        max_tokens=max_tokens,
    )
