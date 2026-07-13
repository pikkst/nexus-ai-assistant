"""Typed goal, plan, evidence, result, and blocker models."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GoalStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    WAITING = "waiting"
    PAUSED = "paused"
    BLOCKED = "blocked"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    WAITING = "waiting"
    PAUSED = "paused"
    BLOCKED = "blocked"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class SuccessCriterion:
    """One machine-checkable or user-confirmed success condition for a step."""

    id: str
    description: str
    check_type: str = "machine"
    expression: str | None = None


@dataclass(frozen=True, slots=True)
class Evidence:
    """One verification artifact supporting a result."""

    kind: str
    summary: str
    verified: bool = False
    confidence: float = 1.0
    reference: str | None = None
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class StepResult:
    """Structured outcome of a plan step."""

    success: bool
    summary: str
    evidence: tuple[Evidence, ...] = ()
    completed_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class Blocker:
    """Reason a plan step cannot currently progress."""

    reason: str
    needs_user: bool = False
    created_at: datetime = field(default_factory=utc_now)
    resolved_at: datetime | None = None


@dataclass(slots=True)
class PlanStep:
    """One dependency-aware unit of work."""

    title: str
    description: str = ""
    dependencies: tuple[str, ...] = ()
    verification_required: bool = True
    success_criteria: tuple[SuccessCriterion, ...] = ()
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    status: StepStatus = StepStatus.PENDING
    result: StepResult | None = None
    blocker: Blocker | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class Goal:
    """Persistent user objective and its ordered plan."""

    objective: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    status: GoalStatus = GoalStatus.PENDING
    steps: list[PlanStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    revision: int = 1


@dataclass(frozen=True, slots=True)
class TaskEvent:
    """Observable goal or step state change."""

    goal_id: str
    action: str
    goal_status: GoalStatus
    step_id: str | None = None
    message: str = ""
    created_at: datetime = field(default_factory=utc_now)


class TaskStateError(RuntimeError):
    """Raised when a requested goal or plan transition is invalid."""
