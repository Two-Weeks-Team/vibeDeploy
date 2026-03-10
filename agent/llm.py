"""LLM factory — routes all calls through DO Serverless Inference with direct OpenAI fallback."""

import asyncio
import logging
import os

DO_INFERENCE_BASE_URL = "https://inference.do-ai.run/v1"
DEFAULT_LLM_REQUEST_TIMEOUT_SECONDS = float(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "90"))
DEFAULT_LLM_MAX_CONCURRENCY = max(1, int(os.getenv("LLM_MAX_CONCURRENCY", "2")))
logger = logging.getLogger(__name__)
_llm_semaphore: asyncio.Semaphore | None = None

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
    "council": "deepseek-r1-distill-llama-70b",
    "strategist": "deepseek-r1-distill-llama-70b",
    "cross_exam": "deepseek-r1-distill-llama-70b",
    "code_gen": "openai-gpt-oss-120b",
    "code_gen_frontend": "openai-gpt-oss-120b",
    "code_gen_backend": "openai-gpt-oss-120b",
    "ci_repair": "deepseek-r1-distill-llama-70b",
    "doc_gen": "deepseek-r1-distill-llama-70b",
    "image": "fal-ai/flux/schnell",
    "brainstorm": "deepseek-r1-distill-llama-70b",
    "brainstorm_synthesis": "deepseek-r1-distill-llama-70b",
    "input": "deepseek-r1-distill-llama-70b",
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


def _get_llm_semaphore() -> asyncio.Semaphore:
    global _llm_semaphore
    if _llm_semaphore is None:
        _llm_semaphore = asyncio.Semaphore(DEFAULT_LLM_MAX_CONCURRENCY)
    return _llm_semaphore


def _get_llm_model_name(llm) -> str:
    for attr in ("model_name", "model"):
        value = getattr(llm, attr, "")
        if isinstance(value, str) and value:
            return value

    bound = getattr(llm, "bound", None)
    if bound is not None and bound is not llm:
        return _get_llm_model_name(bound)

    return ""


def _clone_llm_with_model(llm, model: str):
    temperature = getattr(llm, "temperature", 0.5)
    max_tokens = getattr(llm, "max_tokens", 3000)
    request_timeout = getattr(llm, "request_timeout", None)

    if not isinstance(temperature, (int, float)):
        temperature = 0.5
    if not isinstance(max_tokens, int) or max_tokens <= 0:
        max_tokens = 3000
    if not isinstance(request_timeout, (int, float)) or request_timeout <= 0:
        request_timeout = None

    return get_llm(
        model=model,
        temperature=float(temperature),
        max_tokens=max_tokens,
        request_timeout=request_timeout,
    )


def get_rate_limit_fallback_models(model: str) -> list[str]:
    fallbacks = {
        "openai-gpt-oss-120b": ["alibaba-qwen3-32b", "deepseek-r1-distill-llama-70b"],
        "deepseek-r1-distill-llama-70b": ["alibaba-qwen3-32b", "openai-gpt-oss-120b"],
        "alibaba-qwen3-32b": ["deepseek-r1-distill-llama-70b", "openai-gpt-oss-120b"],
    }
    return list(fallbacks.get(model, []))


async def _ainvoke_with_semaphore(llm, messages: list[dict]):
    async with _get_llm_semaphore():
        return await llm.ainvoke(messages)


async def ainvoke_with_retry(
    llm,
    messages: list[dict],
    *,
    max_attempts: int = 6,
    initial_delay_seconds: float = 5.0,
    fallback_models: list[str] | None = None,
):
    last_exc = None

    llms_to_try = [llm]
    primary_model = _get_llm_model_name(llm)
    seen_models = {primary_model} if primary_model else set()
    for fallback_model in fallback_models or []:
        if not fallback_model or fallback_model in seen_models:
            continue
        llms_to_try.append(_clone_llm_with_model(llm, fallback_model))
        seen_models.add(fallback_model)

    for llm_index, target_llm in enumerate(llms_to_try):
        model_name = _get_llm_model_name(target_llm) or f"llm-{llm_index + 1}"
        delay = initial_delay_seconds
        attempts_for_model = max_attempts if llm_index == 0 else max(3, max_attempts // 2)

        for attempt in range(1, attempts_for_model + 1):
            try:
                return await _ainvoke_with_semaphore(target_llm, messages)
            except Exception as exc:
                last_exc = exc
                if not _is_rate_limit_error(exc):
                    raise

                if attempt < attempts_for_model:
                    logger.warning(
                        "LLM rate limit hit on %s; retrying in %.1fs (attempt %d/%d): %s",
                        model_name,
                        delay,
                        attempt,
                        attempts_for_model,
                        exc,
                    )
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 15.0)
                    continue

                if llm_index < len(llms_to_try) - 1:
                    next_model = _get_llm_model_name(llms_to_try[llm_index + 1]) or f"llm-{llm_index + 2}"
                    logger.warning(
                        "LLM rate limit persisted on %s after %d attempts; switching to %s",
                        model_name,
                        attempts_for_model,
                        next_model,
                    )
                    break

                raise

    if last_exc:
        raise last_exc
    raise RuntimeError("LLM invocation failed without an exception")


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
