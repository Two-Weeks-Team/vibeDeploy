from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel


class DeploymentMetric(BaseModel):
    thread_id: str
    app_name: str
    status: Literal["success", "failed", "timeout"]
    duration_seconds: float
    deploy_method: str
    error_message: str = ""
    created_at: str


def compute_success_rate(metrics: list[DeploymentMetric]) -> float:
    """Return fraction of metrics with status 'success' (0.0 if empty)."""
    if not metrics:
        return 0.0
    success_count = sum(1 for m in metrics if m.status == "success")
    return success_count / len(metrics)


def compute_avg_duration(metrics: list[DeploymentMetric]) -> float:
    """Return mean duration_seconds across metrics (0.0 if empty)."""
    if not metrics:
        return 0.0
    return sum(m.duration_seconds for m in metrics) / len(metrics)


class MetricsStore:
    """Thread-safe in-memory store for DeploymentMetric records."""

    def __init__(self) -> None:
        self._metrics: list[DeploymentMetric] = []
        self._lock = threading.Lock()

    def record(self, metric: DeploymentMetric) -> None:
        """Append a metric to the store."""
        with self._lock:
            self._metrics.append(metric)

    def get_metrics(self, limit: int = 50) -> list[DeploymentMetric]:
        """Return the most recent *limit* metrics (newest first)."""
        with self._lock:
            return list(reversed(self._metrics[-limit:])) if self._metrics else []

    def get_success_rate(self, window_hours: int = 24) -> float:
        """Return success rate for metrics created within the last *window_hours* hours."""
        with self._lock:
            now = datetime.now(tz=timezone.utc)
            window_metrics = [
                m
                for m in self._metrics
                if (now - datetime.fromisoformat(m.created_at)).total_seconds() <= window_hours * 3600
            ]
        return compute_success_rate(window_metrics)

    def get_summary(self) -> dict:
        """Return aggregate statistics over all stored metrics."""
        with self._lock:
            metrics = list(self._metrics)

        total = len(metrics)
        success = sum(1 for m in metrics if m.status == "success")
        failed = sum(1 for m in metrics if m.status == "failed")
        timeout = sum(1 for m in metrics if m.status == "timeout")
        success_rate = compute_success_rate(metrics)
        avg_duration = compute_avg_duration(metrics)

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "timeout": timeout,
            "success_rate": success_rate,
            "avg_duration": avg_duration,
        }
