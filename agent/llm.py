"""LLM factory — routes all calls through DO Serverless Inference with direct OpenAI fallback."""

import asyncio
import logging
import os
from collections.abc import Iterator

from .model_capabilities import model_endpoint_type, selected_runtime_model

DO_INFERENCE_BASE_URL = "https://inference.do-ai.run/v1"
DEFAULT_LLM_REQUEST_TIMEOUT_SECONDS = float(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "180"))
DEFAULT_LLM_MAX_CONCURRENCY = max(1, int(os.getenv("LLM_MAX_CONCURRENCY", "1")))
DEFAULT_LLM_MIN_INTERVAL_SECONDS = max(0.0, float(os.getenv("LLM_MIN_INTERVAL_SECONDS", "4.0")))
RATE_LIMIT_FALLBACK_SWITCH_ATTEMPTS = max(1, int(os.getenv("LLM_RATE_LIMIT_FALLBACK_SWITCH_ATTEMPTS", "2")))
logger = logging.getLogger(__name__)
_llm_semaphore: asyncio.Semaphore | None = None
_llm_rate_lock: asyncio.Lock | None = None
_llm_next_request_at = 0.0

# Text generation defaults are unified on gpt-oss-120b so every LLM stage follows
# the same runtime profile unless an explicit env override is provided.
DEFAULT_MODEL_CONFIG = {
    "council": selected_runtime_model(),
    "strategist": selected_runtime_model(),
    "cross_exam": selected_runtime_model(),
    "code_gen": selected_runtime_model(),
    "code_gen_frontend": selected_runtime_model(),
    "code_gen_backend": selected_runtime_model(),
    "ci_repair": selected_runtime_model(),
    "doc_gen": selected_runtime_model(),
    "image": "fal-ai/flux/schnell",
    "brainstorm": selected_runtime_model(),
    "brainstorm_synthesis": selected_runtime_model(),
    "input": selected_runtime_model(),
    "decision": selected_runtime_model(),
    "web_search": selected_runtime_model(),
}

_MODEL_ENV_OVERRIDES = {
    "council": ("VIBEDEPLOY_MODEL_COUNCIL", "VIBEDEPLOY_MODEL_ANALYSIS", "VIBEDEPLOY_MODEL_ALL", "VIBEDEPLOY_MODEL"),
    "strategist": (
        "VIBEDEPLOY_MODEL_STRATEGIST",
        "VIBEDEPLOY_MODEL_ANALYSIS",
        "VIBEDEPLOY_MODEL_ALL",
        "VIBEDEPLOY_MODEL",
    ),
    "cross_exam": (
        "VIBEDEPLOY_MODEL_CROSS_EXAM",
        "VIBEDEPLOY_MODEL_ANALYSIS",
        "VIBEDEPLOY_MODEL_ALL",
        "VIBEDEPLOY_MODEL",
    ),
    "code_gen": ("VIBEDEPLOY_MODEL_CODE_GEN", "DO_INFERENCE_MODEL", "VIBEDEPLOY_MODEL_ALL", "VIBEDEPLOY_MODEL"),
    "code_gen_frontend": (
        "VIBEDEPLOY_MODEL_CODE_GEN_FRONTEND",
        "VIBEDEPLOY_MODEL_CODE_GEN",
        "DO_INFERENCE_MODEL",
        "VIBEDEPLOY_MODEL_ALL",
        "VIBEDEPLOY_MODEL",
    ),
    "code_gen_backend": (
        "VIBEDEPLOY_MODEL_CODE_GEN_BACKEND",
        "VIBEDEPLOY_MODEL_CODE_GEN",
        "DO_INFERENCE_MODEL",
        "VIBEDEPLOY_MODEL_ALL",
        "VIBEDEPLOY_MODEL",
    ),
    "ci_repair": ("VIBEDEPLOY_MODEL_CI_REPAIR", "VIBEDEPLOY_MODEL_ALL", "VIBEDEPLOY_MODEL"),
    "doc_gen": ("VIBEDEPLOY_MODEL_DOC_GEN", "VIBEDEPLOY_MODEL_ALL", "VIBEDEPLOY_MODEL"),
    "image": ("VIBEDEPLOY_MODEL_IMAGE",),
    "brainstorm": ("VIBEDEPLOY_MODEL_BRAINSTORM", "VIBEDEPLOY_MODEL_ALL", "VIBEDEPLOY_MODEL"),
    "brainstorm_synthesis": ("VIBEDEPLOY_MODEL_BRAINSTORM_SYNTHESIS", "VIBEDEPLOY_MODEL_ALL", "VIBEDEPLOY_MODEL"),
    "input": ("VIBEDEPLOY_MODEL_INPUT", "VIBEDEPLOY_MODEL_ALL", "VIBEDEPLOY_MODEL"),
    "decision": ("VIBEDEPLOY_MODEL_DECISION", "VIBEDEPLOY_MODEL_ALL", "VIBEDEPLOY_MODEL"),
    "web_search": ("VIBEDEPLOY_MODEL_WEB_SEARCH", "VIBEDEPLOY_MODEL_ALL", "VIBEDEPLOY_MODEL"),
}


def get_model_for_role(role: str, default: str | None = None) -> str:
    fallback = DEFAULT_MODEL_CONFIG.get(role, default or "")
    for env_key in _MODEL_ENV_OVERRIDES.get(role, ()):
        value = os.getenv(env_key, "").strip()
        if value:
            return value
    return fallback


def get_runtime_model_config() -> dict[str, str]:
    return {role: get_model_for_role(role, default=value) for role, value in DEFAULT_MODEL_CONFIG.items()}


class _RuntimeModelConfig(dict):
    def __init__(self, defaults: dict[str, str]):
        super().__init__(defaults)
        self._defaults = dict(defaults)

    def __getitem__(self, key: str) -> str:
        if key not in self._defaults:
            raise KeyError(key)
        return get_model_for_role(key, default=self._defaults[key])

    def get(self, key: str, default=None) -> str | None:
        if key in self._defaults:
            return get_model_for_role(key, default=self._defaults[key])
        return default

    def items(self):
        for key in self._defaults:
            yield key, self[key]

    def keys(self):
        return self._defaults.keys()

    def values(self):
        for key in self._defaults:
            yield self[key]

    def copy(self):
        return get_runtime_model_config()

    def __iter__(self) -> Iterator[str]:
        return iter(self._defaults)

    def __len__(self) -> int:
        return len(self._defaults)


MODEL_CONFIG = _RuntimeModelConfig(DEFAULT_MODEL_CONFIG)


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


def _get_llm_rate_lock() -> asyncio.Lock:
    global _llm_rate_lock
    if _llm_rate_lock is None:
        _llm_rate_lock = asyncio.Lock()
    return _llm_rate_lock


async def _wait_for_llm_turn():
    if DEFAULT_LLM_MIN_INTERVAL_SECONDS <= 0:
        return

    global _llm_next_request_at
    loop = asyncio.get_running_loop()
    async with _get_llm_rate_lock():
        now = loop.time()
        if _llm_next_request_at > now:
            await asyncio.sleep(_llm_next_request_at - now)
            now = loop.time()
        _llm_next_request_at = now + DEFAULT_LLM_MIN_INTERVAL_SECONDS


async def _defer_llm_turn(delay_seconds: float):
    if delay_seconds <= 0:
        return

    global _llm_next_request_at
    loop = asyncio.get_running_loop()
    async with _get_llm_rate_lock():
        _llm_next_request_at = max(
            _llm_next_request_at,
            loop.time() + max(DEFAULT_LLM_MIN_INTERVAL_SECONDS, delay_seconds),
        )


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


def _rate_limit_model_fallbacks_enabled() -> bool:
    return os.getenv("VIBEDEPLOY_ENABLE_RATE_LIMIT_MODEL_FALLBACKS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def get_rate_limit_fallback_models(model: str) -> list[str]:
    if not _rate_limit_model_fallbacks_enabled():
        return []

    fallbacks = {
        "anthropic-claude-4.6-sonnet": ["openai-gpt-oss-120b", "anthropic-claude-opus-4.6"],
        "anthropic-claude-opus-4.6": ["anthropic-claude-4.6-sonnet", "openai-gpt-oss-120b"],
        "openai-gpt-oss-120b": ["anthropic-claude-4.6-sonnet", "openai-gpt-oss-20b"],
        "openai-gpt-oss-20b": ["openai-gpt-oss-120b", "anthropic-claude-4.6-sonnet"],
        "alibaba-qwen3-32b": ["openai-gpt-oss-20b", "openai-gpt-oss-120b"],
        "deepseek-r1-distill-llama-70b": ["openai-gpt-oss-120b", "anthropic-claude-4.6-sonnet"],
    }
    return list(fallbacks.get(model, []))


async def _ainvoke_with_semaphore(llm, messages: list[dict]):
    async with _get_llm_semaphore():
        await _wait_for_llm_turn()
        return await llm.ainvoke(messages)


async def ainvoke_with_retry(
    llm,
    messages: list[dict],
    *,
    max_attempts: int = 6,
    initial_delay_seconds: float = 10.0,
    fallback_models: list[str] | None = None,
    rate_limit_switch_after_attempts: int | None = None,
):
    last_exc = None
    switch_after_attempts = max(1, rate_limit_switch_after_attempts or RATE_LIMIT_FALLBACK_SWITCH_ATTEMPTS)

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
        has_more_models = llm_index < len(llms_to_try) - 1

        for attempt in range(1, attempts_for_model + 1):
            try:
                return await _ainvoke_with_semaphore(target_llm, messages)
            except Exception as exc:
                last_exc = exc
                if not _is_retryable_llm_error(exc):
                    raise

                if attempt < attempts_for_model:
                    retry_label = "rate limit" if _is_rate_limit_error(exc) else "transient transport error"
                    if _is_rate_limit_error(exc) and has_more_models and attempt >= switch_after_attempts:
                        next_model = _get_llm_model_name(llms_to_try[llm_index + 1]) or f"llm-{llm_index + 2}"
                        logger.warning(
                            "LLM rate limit persisted on %s after %d attempts; switching early to %s",
                            model_name,
                            attempt,
                            next_model,
                        )
                        break
                    await _defer_llm_turn(delay)
                    logger.warning(
                        "LLM %s on %s; retrying in %.1fs (attempt %d/%d): %s",
                        retry_label,
                        model_name,
                        delay,
                        attempt,
                        attempts_for_model,
                        exc,
                    )
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 60.0)
                    continue

                if has_more_models:
                    next_model = _get_llm_model_name(llms_to_try[llm_index + 1]) or f"llm-{llm_index + 2}"
                    failure_label = "rate limit" if _is_rate_limit_error(exc) else "transient transport error"
                    logger.warning(
                        "LLM %s persisted on %s after %d attempts; switching to %s",
                        failure_label,
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


def _is_retryable_llm_error(exc: Exception) -> bool:
    if _is_rate_limit_error(exc):
        return True

    message = str(exc).lower()
    transient_markers = (
        "incomplete chunked read",
        "peer closed connection",
        "server disconnected",
        "remoteprotocolerror",
        "connection reset",
        "connection aborted",
        "temporarily unavailable",
        "read timeout",
        "timed out",
        "timeout",
        "overloaded",
        "502",
        "503",
        "504",
        "529",
    )
    return any(marker in message for marker in transient_markers)


def get_llm(
    model: str,
    temperature: float = 0.5,
    max_tokens: int = 3000,
    request_timeout: float | None = None,
):
    """Route LLM calls through the provider adapter registry, then DO Inference, then direct OpenAI."""
    from .providers.registry import registry, resolve_canonical

    effective_max_tokens = max(256, max_tokens)
    effective_timeout = request_timeout or DEFAULT_LLM_REQUEST_TIMEOUT_SECONDS

    canonical = resolve_canonical(model)
    result = registry.get_llm(
        canonical,
        temperature=temperature,
        max_tokens=effective_max_tokens,
        timeout=effective_timeout,
    )
    if result is not None:
        return result

    inference_key = os.getenv("GRADIENT_MODEL_ACCESS_KEY", "") or os.getenv("DIGITALOCEAN_INFERENCE_KEY", "")

    if inference_key and inference_key not in ("test-key", ""):
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=canonical,
            api_key=inference_key,
            base_url=DO_INFERENCE_BASE_URL,
            temperature=float(temperature),
            max_tokens=effective_max_tokens,
            request_timeout=effective_timeout,
            use_responses_api=model_endpoint_type(canonical) == "responses",
        )

    from langchain_openai import ChatOpenAI

    stripped = canonical[len("openai-") :] if canonical.startswith("openai-") else canonical
    return ChatOpenAI(
        model=stripped,
        temperature=float(temperature),
        max_tokens=effective_max_tokens,
        request_timeout=effective_timeout,
        use_responses_api=model_endpoint_type(canonical) == "responses",
    )
