"""Atomic JSONL persistence for evaluation records."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from src.eval.models import (
    CriterionResult,
    EvaluationRecord,
    FeedbackKind,
    FeedbackSignal,
    VerificationResult,
)


class EvalStore:
    """Append-only thread-safe storage for evaluation records."""

    def __init__(self, path: Path | str) -> None:
        configured = Path(path).expanduser()
        self.path = configured / "evaluations.jsonl" if configured.suffix.lower() != ".jsonl" else configured
        self._lock = threading.RLock()

    def append(self, record: EvaluationRecord) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "goal_id": record.goal_id,
                "step_id": record.step_id,
                "verification": {
                    "passed": record.verification.passed,
                    "criteria_results": [
                        {
                            "criterion_id": item.criterion_id,
                            "passed": item.passed,
                            "explanation": item.explanation,
                        }
                        for item in record.verification.criteria_results
                    ],
                    "confidence": record.verification.confidence,
                    "failure_explanation": record.verification.failure_explanation,
                    "verified_at": record.verification.verified_at.isoformat(),
                },
                "feedback": None
                if record.feedback is None
                else {
                    "kind": record.feedback.kind.value,
                    "message": record.feedback.message,
                    "rating": record.feedback.rating,
                    "created_at": record.feedback.created_at.isoformat(),
                },
                "created_at": record.created_at.isoformat(),
            }
            line = json.dumps(payload, ensure_ascii=False)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")

    def load(self) -> list[EvaluationRecord]:
        records: list[EvaluationRecord] = []
        with self._lock:
            if not self.path.exists():
                return records
            for line in self.path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                record = EvaluationRecord(
                    goal_id=payload["goal_id"],
                    step_id=payload["step_id"],
                    verification=self._verification_from_dict(payload["verification"]),
                    feedback=self._feedback_from_dict(payload.get("feedback")),
                    created_at=datetime.fromisoformat(payload["created_at"]).replace(tzinfo=timezone.utc),
                )
                records.append(record)
        return records

    def _verification_from_dict(self, data: dict) -> VerificationResult:
        return VerificationResult(
            passed=bool(data["passed"]),
            criteria_results=tuple(
                CriterionResult(
                    criterion_id=item["criterion_id"],
                    passed=bool(item["passed"]),
                    explanation=item["explanation"],
                )
                for item in data.get("criteria_results", [])
            ),
            confidence=float(data.get("confidence", 0.0)),
            failure_explanation=data.get("failure_explanation", ""),
            verified_at=datetime.fromisoformat(data["verified_at"]).replace(tzinfo=timezone.utc),
        )

    def _feedback_from_dict(self, data: dict | None) -> FeedbackSignal | None:
        if data is None:
            return None
        return FeedbackSignal(
            kind=FeedbackKind(data["kind"]),
            message=data["message"],
            rating=data.get("rating"),
            created_at=datetime.fromisoformat(data["created_at"]).replace(tzinfo=timezone.utc),
        )
