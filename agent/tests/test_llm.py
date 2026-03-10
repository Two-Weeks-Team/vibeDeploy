import pytest

from agent.llm import ainvoke_with_retry


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
