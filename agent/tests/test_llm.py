import pytest

from agent.llm import ainvoke_with_retry


class _RetryLLM:
    def __init__(self):
        self.calls = 0

    async def ainvoke(self, messages):
        self.calls += 1
        if self.calls < 3:
            raise RuntimeError("Error code: 429 - rate limit exceeded")
        return {"ok": True, "messages": messages}


@pytest.mark.asyncio
async def test_ainvoke_with_retry_retries_rate_limit():
    llm = _RetryLLM()

    response = await ainvoke_with_retry(llm, [{"role": "user", "content": "hello"}], initial_delay_seconds=0.01)

    assert llm.calls == 3
    assert response["ok"] is True
