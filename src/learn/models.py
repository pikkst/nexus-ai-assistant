"""Learning models: lessons, proposals, quarantine, and reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class LessonStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    QUARANTINED = "quarantined"
    REJECTED = "rejected"
    APPLIED = "applied"


class ImprovementTarget(str, Enum):
    CODE = "code"
    PROMPT = "prompt"
    PERMISSION = "permission"
    SAFETY_RULE = "safety_rule"
    TOOL = "tool"
    MEMORY = "memory"


@dataclass(frozen=True, slots=True)
class Lesson:
    id: str
    text: str
    scope: str
    confidence: float
    provenance: tuple[str, ...]
    expected_benefit: str
    status: LessonStatus = LessonStatus.PENDING
    created_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ImprovementProposal:
    id: str
    lesson_id: str
    target: ImprovementTarget
    description: str
    proposed_change: str
    rationale: str
    requires_approval: bool = True
    status: str = "pending"
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class QuarantineRecord:
    id: str
    lesson_id: str
    reason: str
    conflicting_lesson_ids: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class DevReport:
    generated_at: str
    total_evaluations: int
    successful_verifications: int
    failed_verifications: int
    lessons_generated: int
    lessons_approved: int
    lessons_quarantined: int
    proposals_pending: int
    summary: str = ""
