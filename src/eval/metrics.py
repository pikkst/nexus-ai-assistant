"""Local metrics tracking for evaluation quality."""

from __future__ import annotations

from src.eval.models import EvalMetrics


class MetricsTracker:
    """Track success, corrections, latency, and memory usefulness."""

    def __init__(self) -> None:
        self._metrics = EvalMetrics()

    def record_verification(self, passed: bool, latency_ms: float) -> None:
        self._metrics.record_verification(passed, latency_ms)

    def record_correction(self) -> None:
        self._metrics.record_correction()

    def record_memory_usefulness(self, score: float) -> None:
        self._metrics.record_memory_usefulness(score)

    def snapshot(self) -> EvalMetrics:
        return self._metrics
