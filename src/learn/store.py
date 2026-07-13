"""Atomic JSONL persistence for lessons and proposals."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from .models import (
    ImprovementProposal,
    ImprovementTarget,
    Lesson,
    LessonStatus,
    QuarantineRecord,
)


class LessonStore:
    def __init__(self, path: Path | str) -> None:
        configured = Path(path).expanduser()
        self.lessons_path = (
            configured / "lessons.jsonl"
            if configured.suffix.lower() != ".jsonl"
            else configured
        )
        self.proposals_path = self.lessons_path.parent / "proposals.jsonl"
        self.quarantine_path = self.lessons_path.parent / "quarantine.jsonl"
        self._lock = threading.RLock()

    def add_lesson(self, lesson: Lesson) -> None:
        with self._lock:
            self.lessons_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "id": lesson.id,
                "text": lesson.text,
                "scope": lesson.scope,
                "confidence": lesson.confidence,
                "provenance": list(lesson.provenance),
                "expected_benefit": lesson.expected_benefit,
                "status": lesson.status.value,
                "created_at": lesson.created_at.isoformat(),
                "metadata": lesson.metadata,
            }
            with self.lessons_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def add_proposal(self, proposal: ImprovementProposal) -> None:
        with self._lock:
            self.proposals_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "id": proposal.id,
                "lesson_id": proposal.lesson_id,
                "target": proposal.target.value,
                "description": proposal.description,
                "proposed_change": proposal.proposed_change,
                "rationale": proposal.rationale,
                "requires_approval": proposal.requires_approval,
                "status": proposal.status,
                "created_at": proposal.created_at.isoformat(),
            }
            with self.proposals_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def add_quarantine(self, record: QuarantineRecord) -> None:
        with self._lock:
            self.quarantine_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "id": record.id,
                "lesson_id": record.lesson_id,
                "reason": record.reason,
                "conflicting_lesson_ids": list(record.conflicting_lesson_ids),
                "created_at": record.created_at.isoformat(),
            }
            with self.quarantine_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def load_lessons(self) -> list[Lesson]:
        lessons: list[Lesson] = []
        with self._lock:
            if not self.lessons_path.exists():
                return lessons
            for line in self.lessons_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                lessons.append(
                    Lesson(
                        id=payload["id"],
                        text=payload["text"],
                        scope=payload["scope"],
                        confidence=float(payload["confidence"]),
                        provenance=tuple(payload["provenance"]),
                        expected_benefit=payload["expected_benefit"],
                        status=LessonStatus(payload["status"]),
                        created_at=datetime.fromisoformat(payload["created_at"]).replace(
                            tzinfo=timezone.utc
                        ),
                        metadata=payload.get("metadata", {}),
                    )
                )
        return lessons

    def load_proposals(self) -> list[ImprovementProposal]:
        proposals: list[ImprovementProposal] = []
        with self._lock:
            if not self.proposals_path.exists():
                return proposals
            for line in self.proposals_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                proposals.append(
                    ImprovementProposal(
                        id=payload["id"],
                        lesson_id=payload["lesson_id"],
                        target=ImprovementTarget(payload["target"]),
                        description=payload["description"],
                        proposed_change=payload["proposed_change"],
                        rationale=payload["rationale"],
                        requires_approval=payload["requires_approval"],
                        status=payload["status"],
                        created_at=datetime.fromisoformat(payload["created_at"]).replace(
                            tzinfo=timezone.utc
                        ),
                    )
                )
        return proposals

    def load_quarantine(self) -> list[QuarantineRecord]:
        records: list[QuarantineRecord] = []
        with self._lock:
            if not self.quarantine_path.exists():
                return records
            for line in self.quarantine_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                records.append(
                    QuarantineRecord(
                        id=payload["id"],
                        lesson_id=payload["lesson_id"],
                        reason=payload["reason"],
                        conflicting_lesson_ids=tuple(
                            payload.get("conflicting_lesson_ids", [])
                        ),
                        created_at=datetime.fromisoformat(payload["created_at"]).replace(
                            tzinfo=timezone.utc
                        ),
                    )
                )
        return records
