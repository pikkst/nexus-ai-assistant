"""Local development report summarizing outcomes and proposed improvements."""

from __future__ import annotations

from src.eval.models import EvalMetrics

from .models import (
    DevReport,
    ImprovementProposal,
    Lesson,
    LessonStatus,
    QuarantineRecord,
    utc_now,
)
from .store import LessonStore


class DevReportGenerator:
    def __init__(
        self,
        lesson_store: LessonStore,
        eval_metrics: EvalMetrics | None = None,
    ) -> None:
        self.lesson_store = lesson_store
        self.eval_metrics = eval_metrics

    def generate(self) -> DevReport:
        lessons = self.lesson_store.load_lessons()
        proposals = self.lesson_store.load_proposals()
        quarantine = self.lesson_store.load_quarantine()

        total = self.eval_metrics.total_evaluations if self.eval_metrics else 0
        successful = (
            self.eval_metrics.successful_verifications if self.eval_metrics else 0
        )
        failed = self.eval_metrics.failed_verifications if self.eval_metrics else 0
        approved = sum(1 for lesson in lessons if lesson.status is LessonStatus.APPROVED)
        quarantined = len(quarantine)
        pending = sum(1 for proposal in proposals if proposal.status == "pending")

        summary_lines = [
            f"Development report generated at {utc_now().isoformat()}",
            f"Evaluations: {total} total, {successful} passed, {failed} failed",
            f"Lessons: {len(lessons)} generated, {approved} approved, {quarantined} quarantined",
            f"Proposals: {pending} pending approval",
        ]
        if proposals:
            summary_lines.append("Pending proposals:")
            for proposal in proposals:
                summary_lines.append(
                    f"  - [{proposal.target.value}] {proposal.description}"
                )

        return DevReport(
            generated_at=utc_now().isoformat(),
            total_evaluations=total,
            successful_verifications=successful,
            failed_verifications=failed,
            lessons_generated=len(lessons),
            lessons_approved=approved,
            lessons_quarantined=quarantined,
            proposals_pending=pending,
            summary="\n".join(summary_lines),
        )
