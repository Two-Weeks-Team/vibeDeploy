"""LLM factory — routes all calls through DO Serverless Inference with direct OpenAI fallback."""

import asyncio
import logging
import os

DO_INFERENCE_BASE_URL = "https://inference.do-ai.run/v1"
DEFAULT_LLM_REQUEST_TIMEOUT_SECONDS = float(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "90"))
logger = logging.getLogger(__name__)

# Open-source models via DO Serverless Inference (no subscription tier restrictions)
# Commercial models (Anthropic/OpenAI) temporarily unavailable — DO Support ticket pending.
# When commercial access is restored, switch back to:
#   council/brainstorm/input: anthropic-claude-4.6-sonnet
#   strategist/cross_exam/brainstorm_synthesis/decision: openai-gpt-5.2
#   code_gen/ci_repair: anthropic-claude-opus-4.6
#   doc_gen: anthropic-claude-4.6-sonnet
#   web_search: openai-gpt-5-mini
#   image: openai-gpt-image-1
MODEL_CONFIG = {
    "council": "openai-gpt-oss-120b",
    "strategist": "deepseek-r1-distill-llama-70b",
    "cross_exam": "deepseek-r1-distill-llama-70b",
    "code_gen": "openai-gpt-oss-120b",
    "code_gen_frontend": "alibaba-qwen3-32b",
    "code_gen_backend": "openai-gpt-oss-120b",
    "ci_repair": "alibaba-qwen3-32b",
    "doc_gen": "alibaba-qwen3-32b",
    "image": "fal-ai/flux/schnell",
    "brainstorm": "openai-gpt-oss-120b",
    "brainstorm_synthesis": "deepseek-r1-distill-llama-70b",
    "input": "openai-gpt-oss-120b",
    "decision": "deepseek-r1-distill-llama-70b",
    "web_search": "mistral-nemo-instruct-2407",
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


async def ainvoke_with_retry(
    llm,
    messages: list[dict],
    *,
    max_attempts: int = 6,
    initial_delay_seconds: float = 5.0,
):
    delay = initial_delay_seconds
    last_exc = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await llm.ainvoke(messages)
        except Exception as exc:
            last_exc = exc
            if attempt >= max_attempts or not _is_rate_limit_error(exc):
                raise

            logger.warning(
                "LLM rate limit hit; retrying in %.1fs (attempt %d/%d): %s",
                delay,
                attempt,
                max_attempts,
                exc,
            )
            await asyncio.sleep(delay)
            delay = min(delay * 2, 15.0)

    raise last_exc


def _is_rate_limit_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "rate limit" in message or "429" in message


def get_llm(
    model: str,
    temperature: float = 0.5,
    max_tokens: int = 3000,
    request_timeout: float | None = None,
):
    """Route LLM calls through DO Inference when key is available, else direct OpenAI."""
    inference_key = os.getenv("DIGITALOCEAN_INFERENCE_KEY", "")
    effective_max_tokens = max(256, max_tokens)
    effective_timeout = request_timeout or DEFAULT_LLM_REQUEST_TIMEOUT_SECONDS

    if inference_key and inference_key not in ("test-key", ""):
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            api_key=inference_key,
            base_url=DO_INFERENCE_BASE_URL,
            temperature=temperature,
            max_tokens=effective_max_tokens,
            request_timeout=effective_timeout,
        )

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=_strip_openai_prefix(model),
        temperature=temperature,
        max_tokens=effective_max_tokens,
        request_timeout=effective_timeout,
    )
