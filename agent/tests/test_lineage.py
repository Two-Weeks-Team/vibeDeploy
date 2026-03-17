import pytest

from agent.db.store import LineageRecord, LineageStore


@pytest.fixture
def store() -> LineageStore:
    return LineageStore()


def make_record(
    record_id: str,
    record_type: str = "meeting",
    thread_id: str = "thread-1",
    parent_id: str | None = None,
    created_at: str = "2026-01-01T00:00:00",
    metadata: dict | None = None,
) -> LineageRecord:
    return LineageRecord(
        record_id=record_id,
        record_type=record_type,
        thread_id=thread_id,
        parent_id=parent_id,
        created_at=created_at,
        metadata=metadata or {},
    )


def test_save_and_retrieve_record(store: LineageStore) -> None:
    record = make_record("r1")
    returned_id = store.save_record(record)
    assert returned_id == "r1"
    retrieved = store.get_record("r1")
    assert retrieved == record


def test_save_returns_record_id(store: LineageStore) -> None:
    record = make_record("abc-123")
    result = store.save_record(record)
    assert result == "abc-123"


def test_unknown_record_id_returns_none(store: LineageStore) -> None:
    result = store.get_record("does-not-exist")
    assert result is None


def test_empty_store_get_lineage(store: LineageStore) -> None:
    assert store.get_lineage("thread-1") == []


def test_empty_store_get_children(store: LineageStore) -> None:
    assert store.get_children("r1") == []


def test_get_lineage_returns_records_for_thread(store: LineageStore) -> None:
    r1 = make_record("r1", thread_id="thread-A")
    r2 = make_record("r2", thread_id="thread-A")
    r3 = make_record("r3", thread_id="thread-B")
    store.save_record(r1)
    store.save_record(r2)
    store.save_record(r3)

    lineage = store.get_lineage("thread-A")
    ids = [r.record_id for r in lineage]
    assert "r1" in ids
    assert "r2" in ids
    assert "r3" not in ids


def test_get_lineage_sorted_by_created_at(store: LineageStore) -> None:
    r1 = make_record("r1", created_at="2026-01-03T00:00:00")
    r2 = make_record("r2", created_at="2026-01-01T00:00:00")
    r3 = make_record("r3", created_at="2026-01-02T00:00:00")
    store.save_record(r1)
    store.save_record(r2)
    store.save_record(r3)

    lineage = store.get_lineage("thread-1")
    assert [r.record_id for r in lineage] == ["r2", "r3", "r1"]


def test_get_children_returns_child_records(store: LineageStore) -> None:
    parent = make_record("parent")
    child1 = make_record("child1", parent_id="parent")
    child2 = make_record("child2", parent_id="parent")
    other = make_record("other", parent_id="different")
    store.save_record(parent)
    store.save_record(child1)
    store.save_record(child2)
    store.save_record(other)

    children = store.get_children("parent")
    child_ids = {r.record_id for r in children}
    assert child_ids == {"child1", "child2"}


def test_get_chain_traces_parent_chain(store: LineageStore) -> None:
    root = make_record("root", parent_id=None)
    mid = make_record("mid", parent_id="root")
    leaf = make_record("leaf", parent_id="mid")
    store.save_record(root)
    store.save_record(mid)
    store.save_record(leaf)

    chain = store.get_chain("leaf")
    assert [r.record_id for r in chain] == ["leaf", "mid", "root"]


def test_get_chain_stops_at_root(store: LineageStore) -> None:
    root = make_record("root", parent_id=None)
    child = make_record("child", parent_id="root")
    store.save_record(root)
    store.save_record(child)

    chain = store.get_chain("root")
    assert len(chain) == 1
    assert chain[0].record_id == "root"


def test_get_summary_counts_by_type(store: LineageStore) -> None:
    store.save_record(make_record("m1", record_type="meeting"))
    store.save_record(make_record("m2", record_type="meeting"))
    store.save_record(make_record("b1", record_type="brainstorm"))
    store.save_record(make_record("d1", record_type="deployment"))

    summary = store.get_summary()
    assert summary["total"] == 4
    assert summary["by_type"]["meeting"] == 2
    assert summary["by_type"]["brainstorm"] == 1
    assert summary["by_type"]["deployment"] == 1
    assert summary["by_type"]["zero_prompt_session"] == 0
    assert summary["by_type"]["build_job"] == 0


def test_multiple_threads_isolated(store: LineageStore) -> None:
    store.save_record(make_record("a1", thread_id="thread-A"))
    store.save_record(make_record("b1", thread_id="thread-B"))
    store.save_record(make_record("b2", thread_id="thread-B"))

    assert len(store.get_lineage("thread-A")) == 1
    assert len(store.get_lineage("thread-B")) == 2


def test_lineage_record_model_validation() -> None:
    record = LineageRecord(
        record_id="r1",
        record_type="build_job",
        thread_id="t1",
        parent_id="p1",
        metadata={"key": "value"},
        created_at="2026-03-17T12:00:00",
    )
    assert record.record_id == "r1"
    assert record.record_type == "build_job"
    assert record.parent_id == "p1"
    assert record.metadata == {"key": "value"}


def test_lineage_record_invalid_type_raises() -> None:
    with pytest.raises(Exception):
        LineageRecord(
            record_id="r1",
            record_type="invalid_type",
            thread_id="t1",
            created_at="2026-03-17T12:00:00",
        )
