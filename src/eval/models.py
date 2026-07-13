"""Evaluation models for result verification, feedback, and metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FeedbackKind(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    EXPLANATORY = "explanatory"


@dataclass(frozen=True, slots=True)
class SuccessCriterion:
    """One machine-checkable or user-confirmed success condition for a step."""

    id: str
    description: str
    check_type: str = "machine"
    expression: str | None = None


@dataclass(frozen=True, slots=True)
class CriterionResult:
    """Outcome of evaluating a single success criterion."""

    criterion_id: str
    passed: bool
    explanation: str


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """Outcome of verifying a step against its success criteria."""

    passed: bool
    criteria_results: tuple[CriterionResult, ...]
    confidence: float
    failure_explanation: str
    verified_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class FeedbackSignal:
    """User feedback about completed or failed work."""

    kind: FeedbackKind
    message: str
    rating: float | None = None
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class EvaluationRecord:
    """One verification attempt plus optional user feedback."""

    goal_id: str
    step_id: str
    verification: VerificationResult
    feedback: FeedbackSignal | None = None
    created_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class EvalMetrics:
    """Local counters for evaluation quality."""

    total_evaluations: int = 0
    successful_verifications: int = 0
    failed_verifications: int = 0
    corrections: int = 0
    total_latency_ms: float = 0.0
    memory_usefulness_scores: list[float] = field(default_factory=list)

    def record_verification(self, passed: bool, latency_ms: float) -> None:
        self.total_evaluations += 1
        if passed:
            self.successful_verifications += 1
        else:
            self.failed_verifications += 1
        self.total_latency_ms += latency_ms

    def record_correction(self) -> None:
        self.corrections += 1

    def record_memory_usefulness(self, score: float) -> None:
        self.memory_usefulness_scores.append(score)

    @property
    def average_latency_ms(self) -> float:
        if self.total_evaluations == 0:
            return 0.0
        return self.total_latency_ms / self.total_evaluations

    @property
    def average_memory_usefulness(self) -> float:
        if not self.memory_usefulness_scores:
            return 0.0
        return sum(self.memory_usefulness_scores) / len(self.memory_usefulness_scores)

    @property
    def success_rate(self) -> float:
        if self.total_evaluations == 0:
            return 0.0
        return self.successful_verifications / self.total_evaluations
