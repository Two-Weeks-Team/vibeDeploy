import pytest


@pytest.mark.asyncio
async def test_save_and_get_meeting(store):
    data = {"score": 85, "verdict": "GO"}
    await store.save_meeting("t1", data)
    result = await store.get_meeting("t1")
    assert result == data


@pytest.mark.asyncio
async def test_get_meeting_not_found(store):
    result = await store.get_meeting("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_save_and_get_brainstorm(store):
    data = {"insights": [{"agent": "architect"}], "synthesis": {"themes": ["a"]}}
    await store.save_brainstorm("b1", data)
    result = await store.get_brainstorm("b1")
    assert result == data


@pytest.mark.asyncio
async def test_get_brainstorm_not_found(store):
    result = await store.get_brainstorm("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_upsert_overwrites(store):
    await store.save_meeting("t1", {"score": 50})
    await store.save_meeting("t1", {"score": 90})
    result = await store.get_meeting("t1")
    assert result["score"] == 90
