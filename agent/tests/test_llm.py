import pytest

from agent.llm import MODEL_CONFIG, ainvoke_with_retry, get_rate_limit_fallback_models, get_runtime_model_config


class _RetryLLM:
    def __init__(self, model_name: str = "primary-model"):
        self.calls = 0
        self.model_name = model_name
        self.temperature = 0.3
        self.max_tokens = 1024
        self.request_timeout = 30.0

    async def ainvoke(self, messages):
        self.calls += 1
        if self.calls < 3:
            raise RuntimeError("Error code: 429 - rate limit exceeded")
        return {"ok": True, "messages": messages}


class _AlwaysRateLimitLLM(_RetryLLM):
    async def ainvoke(self, messages):
        self.calls += 1
        raise RuntimeError("Error code: 429 - rate limit exceeded")


class _RetryTransportLLM(_RetryLLM):
    async def ainvoke(self, messages):
        self.calls += 1
        if self.calls < 3:
            raise RuntimeError("peer closed connection without sending complete message body (incomplete chunked read)")
        return {"ok": True, "messages": messages}


@pytest.mark.asyncio
async def test_ainvoke_with_retry_retries_rate_limit():
    llm = _RetryLLM()

    response = await ainvoke_with_retry(llm, [{"role": "user", "content": "hello"}], initial_delay_seconds=0.01)

    assert llm.calls == 3
    assert response["ok"] is True


@pytest.mark.asyncio
async def test_ainvoke_with_retry_uses_fallback_model(monkeypatch):
    primary = _AlwaysRateLimitLLM()
    fallback = _RetryLLM(model_name="fallback-model")

    def _fake_get_llm(model: str, temperature: float = 0.5, max_tokens: int = 3000, request_timeout=None):
        assert model == "fallback-model"
        fallback.temperature = temperature
        fallback.max_tokens = max_tokens
        fallback.request_timeout = request_timeout
        return fallback

    monkeypatch.setattr("agent.llm.get_llm", _fake_get_llm)

    response = await ainvoke_with_retry(
        primary,
        [{"role": "user", "content": "hello"}],
        max_attempts=1,
        initial_delay_seconds=0.01,
        fallback_models=["fallback-model"],
    )

    assert primary.calls == 1
    assert fallback.calls == 3
    assert response["ok"] is True


@pytest.mark.asyncio
async def test_ainvoke_with_retry_switches_early_to_fallback_on_rate_limit(monkeypatch):
    primary = _AlwaysRateLimitLLM()
    fallback = _RetryLLM(model_name="fallback-model")

    def _fake_get_llm(model: str, temperature: float = 0.5, max_tokens: int = 3000, request_timeout=None):
        assert model == "fallback-model"
        fallback.temperature = temperature
        fallback.max_tokens = max_tokens
        fallback.request_timeout = request_timeout
        return fallback

    monkeypatch.setattr("agent.llm.get_llm", _fake_get_llm)
    monkeypatch.setattr("agent.llm.RATE_LIMIT_FALLBACK_SWITCH_ATTEMPTS", 2)

    response = await ainvoke_with_retry(
        primary,
        [{"role": "user", "content": "hello"}],
        max_attempts=6,
        initial_delay_seconds=0.01,
        fallback_models=["fallback-model"],
    )

    assert primary.calls == 2
    assert fallback.calls == 3
    assert response["ok"] is True


@pytest.mark.asyncio
async def test_ainvoke_with_retry_retries_transient_transport_errors():
    llm = _RetryTransportLLM()

    response = await ainvoke_with_retry(llm, [{"role": "user", "content": "hello"}], initial_delay_seconds=0.01)

    assert llm.calls == 3
    assert response["ok"] is True


def test_rate_limit_fallbacks_disabled_by_default(monkeypatch):
    monkeypatch.delenv("VIBEDEPLOY_ENABLE_RATE_LIMIT_MODEL_FALLBACKS", raising=False)

    assert get_rate_limit_fallback_models("openai-gpt-oss-120b") == []


def test_rate_limit_fallbacks_can_be_enabled(monkeypatch):
    monkeypatch.setenv("VIBEDEPLOY_ENABLE_RATE_LIMIT_MODEL_FALLBACKS", "1")

    assert get_rate_limit_fallback_models("anthropic-claude-4.6-sonnet") == [
        "openai-gpt-oss-120b",
        "anthropic-claude-opus-4.6",
    ]
    assert get_rate_limit_fallback_models("openai-gpt-oss-120b") == [
        "anthropic-claude-4.6-sonnet",
        "openai-gpt-oss-20b",
    ]


def test_runtime_model_config_prefers_env_overrides(monkeypatch):
    monkeypatch.setenv("VIBEDEPLOY_MODEL_CODE_GEN", "alibaba-qwen3-32b")
    monkeypatch.setenv("VIBEDEPLOY_MODEL_CODE_GEN_FRONTEND", "openai-gpt-oss-20b")
    monkeypatch.setenv("VIBEDEPLOY_MODEL_COUNCIL", "deepseek-r1-distill-llama-70b")

    runtime = get_runtime_model_config()

    assert runtime["code_gen"] == "alibaba-qwen3-32b"
    assert runtime["code_gen_frontend"] == "openai-gpt-oss-20b"
    assert MODEL_CONFIG["code_gen_backend"] == "alibaba-qwen3-32b"
    assert MODEL_CONFIG["council"] == "deepseek-r1-distill-llama-70b"
