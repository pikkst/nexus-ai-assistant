"""Quarantine logic for conflicting or low-confidence lessons."""

from __future__ import annotations

from .models import Lesson, LessonStatus, QuarantineRecord, utc_now


class QuarantineManager:
    def __init__(self, store) -> None:
        self.store = store
        self._quarantined_ids: set[str] = set()

    def evaluate(self, lesson: Lesson, existing_lessons: list[Lesson]) -> QuarantineRecord | None:
        if lesson.confidence < 0.5:
            record = QuarantineRecord(
                id=utc_now().isoformat(),
                lesson_id=lesson.id,
                reason="low_confidence",
            )
            self._quarantined_ids.add(lesson.id)
            self.store.add_quarantine(record)
            return record

        conflicts = self._find_conflicts(lesson, existing_lessons)
        if conflicts:
            record = QuarantineRecord(
                id=utc_now().isoformat(),
                lesson_id=lesson.id,
                reason="conflict",
                conflicting_lesson_ids=tuple(conflicts),
            )
            self._quarantined_ids.add(lesson.id)
            self.store.add_quarantine(record)
            return record

        return None

    def release(self, lesson_id: str) -> None:
        self._quarantined_ids.discard(lesson_id)

    def is_quarantined(self, lesson_id: str) -> bool:
        return lesson_id in self._quarantined_ids

    def _find_conflicts(self, lesson: Lesson, existing: list[Lesson]) -> list[str]:
        lesson_text = lesson.text.casefold().strip()
        conflicts = []
        for other in existing:
            if other.status is LessonStatus.QUARANTINED:
                continue
            other_text = other.text.casefold().strip()
            if lesson_text == other_text or self._semantic_overlap(lesson_text, other_text):
                conflicts.append(other.id)
        return conflicts

    def _semantic_overlap(self, a: str, b: str) -> bool:
        tokens_a = set(a.split())
        tokens_b = set(b.split())
        if not tokens_a or not tokens_b:
            return False
        overlap = tokens_a & tokens_b
        return len(overlap) / max(len(tokens_a), len(tokens_b)) > 0.7
