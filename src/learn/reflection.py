"""Reflection engine that converts verified outcomes into procedural lessons."""

from __future__ import annotations

import uuid

from src.eval.models import EvaluationRecord, FeedbackKind
from src.tasks.models import Goal, PlanStep
from .models import ImprovementProposal, ImprovementTarget, Lesson, LessonStatus, utc_now
from .quarantine import QuarantineManager


class ReflectionEngine:
    def __init__(self, memory_manager, lesson_store, quarantine: QuarantineManager | None = None) -> None:
        self.memory_manager = memory_manager
        self.lesson_store = lesson_store
        self.quarantine = quarantine or QuarantineManager(lesson_store)

    def reflect(
        self,
        eval_records: list[EvaluationRecord],
        goals: list[Goal],
    ) -> tuple[list[Lesson], list[ImprovementProposal]]:
        lessons: list[Lesson] = []
        proposals: list[ImprovementProposal] = []
        existing_lessons = self.lesson_store.load_lessons()

        for record in eval_records:
            lesson = self._record_to_lesson(record, goals)
            if lesson is None:
                continue

            quarantine_record = self.quarantine.evaluate(lesson, existing_lessons)
            if quarantine_record:
                lesson = Lesson(
                    id=lesson.id,
                    text=lesson.text,
                    scope=lesson.scope,
                    confidence=lesson.confidence,
                    provenance=lesson.provenance,
                    expected_benefit=lesson.expected_benefit,
                    status=LessonStatus.QUARANTINED,
                    created_at=lesson.created_at,
                    metadata={**lesson.metadata, "quarantine_reason": quarantine_record.reason},
                )

            self.lesson_store.add_lesson(lesson)
            existing_lessons.append(lesson)
            lessons.append(lesson)

            if lesson.status is not LessonStatus.QUARANTINED and lesson.confidence >= 0.7:
                proposal = self._propose_improvement(lesson)
                if proposal:
                    self.lesson_store.add_proposal(proposal)
                    proposals.append(proposal)

        return lessons, proposals

    def _record_to_lesson(self, record: EvaluationRecord, goals: list[Goal]) -> Lesson | None:
        step = self._find_step(record.goal_id, record.step_id, goals)
        if step is None:
            return None

        confidence = record.verification.confidence
        if record.feedback and record.feedback.rating is not None:
            confidence = (confidence + record.feedback.rating) / 2.0

        scope = step.title
        if step.success_criteria:
            scope = f"{step.title}: {', '.join(c.description for c in step.success_criteria)}"

        if record.verification.passed:
            if record.feedback and record.feedback.kind is FeedbackKind.NEGATIVE:
                text = (
                    f"Step '{step.title}' passed verification but received negative feedback: "
                    f"{record.feedback.message}. Investigate edge cases or user expectations."
                )
                expected_benefit = "Reduce future negative feedback by addressing the reported issue."
            else:
                text = (
                    f"Step '{step.title}' completed successfully with verified evidence. "
                    "Repeat this approach for similar tasks."
                )
                expected_benefit = (
                    "Improve success rate for similar task patterns by reusing verified approach."
                )
        else:
            text = (
                f"Step '{step.title}' failed verification: "
                f"{record.verification.failure_explanation}. Avoid repeating the causes of this failure."
            )
            expected_benefit = "Reduce failure rate by applying the learned correction to future attempts."

        return Lesson(
            id=uuid.uuid4().hex,
            text=text,
            scope=scope,
            confidence=confidence,
            provenance=(record.goal_id, record.step_id),
            expected_benefit=expected_benefit,
            metadata={
                "goal_id": record.goal_id,
                "step_id": record.step_id,
                "verification_passed": record.verification.passed,
                "feedback_kind": record.feedback.kind.value if record.feedback else None,
            },
        )

    def _propose_improvement(self, lesson: Lesson) -> ImprovementProposal | None:
        target = self._infer_target(lesson)
        if target is None:
            return None

        description = (
            f"Improve {target.value} behavior based on lesson: {lesson.text[:100]}"
        )
        proposed_change = (
            f"Review and apply lesson '{lesson.id}' to relevant "
            f"{target.value} configuration or implementation."
        )
        rationale = (
            f"Expected benefit: {lesson.expected_benefit}. Confidence: {lesson.confidence:.2f}."
        )

        return ImprovementProposal(
            id=uuid.uuid4().hex,
            lesson_id=lesson.id,
            target=target,
            description=description,
            proposed_change=proposed_change,
            rationale=rationale,
        )

    def _infer_target(self, lesson: Lesson) -> ImprovementTarget | None:
        text = lesson.text.lower()
        if any(k in text for k in ("permission", "access", "allowed", "denied")):
            return ImprovementTarget.PERMISSION
        if any(k in text for k in ("prompt", "system prompt", "instruction")):
            return ImprovementTarget.PROMPT
        if any(k in text for k in ("tool", "function", "api")):
            return ImprovementTarget.TOOL
        if any(k in text for k in ("code", "implementation", "function", "module")):
            return ImprovementTarget.CODE
        if any(k in text for k in ("memory", "remember", "recall")):
            return ImprovementTarget.MEMORY
        return ImprovementTarget.SAFETY_RULE

    def _find_step(self, goal_id: str, step_id: str, goals: list[Goal]) -> PlanStep | None:
        for goal in goals:
            if goal.id == goal_id:
                for step in goal.steps:
                    if step.id == step_id:
                        return step
        return None
