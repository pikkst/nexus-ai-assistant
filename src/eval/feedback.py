"""Feedback collection for evaluation records."""

from __future__ import annotations

from collections.abc import Iterable

from src.eval.models import FeedbackKind, FeedbackSignal


class FeedbackCollector:
    """Collect and summarize user feedback signals."""

    def __init__(self) -> None:
        self._signals: list[FeedbackSignal] = []

    def collect(self, signal: FeedbackSignal) -> None:
        self._signals.append(signal)

    def collect_kind(
        self,
        kind: FeedbackKind | str,
        message: str,
        rating: float | None = None,
    ) -> FeedbackSignal:
        resolved_kind = kind if isinstance(kind, FeedbackKind) else FeedbackKind(kind)
        signal = FeedbackSignal(kind=resolved_kind, message=message, rating=rating)
        self.collect(signal)
        return signal

    def all(self) -> tuple[FeedbackSignal, ...]:
        return tuple(self._signals)

    def summary(self) -> dict:
        counts: dict[str, int] = {}
        for signal in self._signals:
            key = signal.kind.value if isinstance(signal.kind, FeedbackKind) else str(signal.kind)
            counts[key] = counts.get(key, 0) + 1
        ratings = [s.rating for s in self._signals if s.rating is not None]
        return {
            "counts": counts,
            "average_rating": sum(ratings) / len(ratings) if ratings else None,
        }
