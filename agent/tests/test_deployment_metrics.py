from datetime import datetime, timedelta, timezone

import pytest
from db.deployment_metrics import DeploymentMetric, MetricsStore, compute_avg_duration, compute_success_rate


def _make_metric(
    thread_id: str = "t1",
    app_name: str = "myapp",
    status: str = "success",
    duration_seconds: float = 10.0,
    deploy_method: str = "app_platform",
    error_message: str = "",
    hours_ago: float = 0,
) -> DeploymentMetric:
    created_at = (datetime.now(tz=timezone.utc) - timedelta(hours=hours_ago)).isoformat()
    return DeploymentMetric(
        thread_id=thread_id,
        app_name=app_name,
        status=status,
        duration_seconds=duration_seconds,
        deploy_method=deploy_method,
        error_message=error_message,
        created_at=created_at,
    )


def test_metric_defaults():
    m = _make_metric()
    assert m.error_message == ""
    assert m.deploy_method == "app_platform"


def test_metric_fields():
    m = _make_metric(thread_id="abc", app_name="coolapp", status="failed", duration_seconds=42.5)
    assert m.thread_id == "abc"
    assert m.app_name == "coolapp"
    assert m.status == "failed"
    assert m.duration_seconds == 42.5


def test_metric_invalid_status():
    with pytest.raises(Exception):
        DeploymentMetric(
            thread_id="t",
            app_name="a",
            status="unknown",
            duration_seconds=1.0,
            deploy_method="local",
            created_at=datetime.now(tz=timezone.utc).isoformat(),
        )


def test_success_rate_empty():
    assert compute_success_rate([]) == 0.0


def test_success_rate_all_success():
    metrics = [_make_metric(status="success") for _ in range(5)]
    assert compute_success_rate(metrics) == 1.0


def test_success_rate_all_failed():
    metrics = [_make_metric(status="failed") for _ in range(3)]
    assert compute_success_rate(metrics) == 0.0


def test_success_rate_mixed():
    metrics = [
        _make_metric(status="success"),
        _make_metric(status="success"),
        _make_metric(status="failed"),
        _make_metric(status="timeout"),
    ]
    assert compute_success_rate(metrics) == pytest.approx(0.5)


def test_avg_duration_empty():
    assert compute_avg_duration([]) == 0.0


def test_avg_duration_single():
    assert compute_avg_duration([_make_metric(duration_seconds=30.0)]) == pytest.approx(30.0)


def test_avg_duration_multiple():
    metrics = [_make_metric(duration_seconds=d) for d in [10.0, 20.0, 30.0]]
    assert compute_avg_duration(metrics) == pytest.approx(20.0)


def test_store_record_and_retrieve():
    store = MetricsStore()
    m = _make_metric(thread_id="x1")
    store.record(m)
    result = store.get_metrics()
    assert len(result) == 1
    assert result[0].thread_id == "x1"


def test_store_get_metrics_returns_newest_first():
    store = MetricsStore()
    for i in range(3):
        store.record(_make_metric(thread_id=f"t{i}", app_name=f"app{i}"))
    result = store.get_metrics()
    assert result[0].thread_id == "t2"
    assert result[1].thread_id == "t1"
    assert result[2].thread_id == "t0"


def test_store_get_metrics_limit():
    store = MetricsStore()
    for i in range(10):
        store.record(_make_metric(thread_id=f"t{i}"))
    result = store.get_metrics(limit=3)
    assert len(result) == 3


def test_store_get_metrics_empty():
    store = MetricsStore()
    assert store.get_metrics() == []


def test_store_success_rate_empty():
    store = MetricsStore()
    assert store.get_success_rate() == 0.0


def test_store_success_rate_within_window():
    store = MetricsStore()
    store.record(_make_metric(status="success", hours_ago=1))
    store.record(_make_metric(status="failed", hours_ago=1))
    assert store.get_success_rate(window_hours=24) == pytest.approx(0.5)


def test_store_success_rate_excludes_old_metrics():
    store = MetricsStore()
    store.record(_make_metric(status="failed", hours_ago=48))
    store.record(_make_metric(status="success", hours_ago=1))
    assert store.get_success_rate(window_hours=24) == pytest.approx(1.0)


def test_store_summary_empty():
    store = MetricsStore()
    summary = store.get_summary()
    assert summary["total"] == 0
    assert summary["success"] == 0
    assert summary["failed"] == 0
    assert summary["timeout"] == 0
    assert summary["success_rate"] == 0.0
    assert summary["avg_duration"] == 0.0


def test_store_summary_counts():
    store = MetricsStore()
    store.record(_make_metric(status="success", duration_seconds=10.0))
    store.record(_make_metric(status="success", duration_seconds=20.0))
    store.record(_make_metric(status="failed", duration_seconds=5.0))
    store.record(_make_metric(status="timeout", duration_seconds=60.0))
    summary = store.get_summary()
    assert summary["total"] == 4
    assert summary["success"] == 2
    assert summary["failed"] == 1
    assert summary["timeout"] == 1
    assert summary["success_rate"] == pytest.approx(0.5)
    assert summary["avg_duration"] == pytest.approx(23.75)


def test_store_summary_keys():
    store = MetricsStore()
    summary = store.get_summary()
    assert set(summary.keys()) == {"total", "success", "failed", "timeout", "success_rate", "avg_duration"}
