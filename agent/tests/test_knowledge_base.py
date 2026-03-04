import pytest

from agent.tools.knowledge_base import query_do_knowledge_base, query_framework_patterns


@pytest.mark.asyncio
async def test_query_do_kb_returns_error_without_env():
    result = await query_do_knowledge_base("test query")
    assert "error" in result
    assert result["matches"] == []


@pytest.mark.asyncio
async def test_query_framework_patterns_returns_error_without_env():
    result = await query_framework_patterns("test query")
    assert "error" in result
    assert result["matches"] == []
