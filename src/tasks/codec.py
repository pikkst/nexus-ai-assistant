"""JSON-compatible serialization for task models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import Blocker, Evidence, Goal, GoalStatus, PlanStep, StepResult, StepStatus, SuccessCriterion


def _date(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)


def goal_to_dict(goal: Goal) -> dict[str, Any]:
    return {
        "id": goal.id,
        "objective": goal.objective,
        "status": goal.status.value,
        "steps": [_step_to_dict(step) for step in goal.steps],
        "created_at": goal.created_at.isoformat(),
        "updated_at": goal.updated_at.isoformat(),
        "revision": goal.revision,
    }


def _step_to_dict(step: PlanStep) -> dict[str, Any]:
    return {
        "id": step.id,
        "title": step.title,
        "description": step.description,
        "dependencies": list(step.dependencies),
        "verification_required": step.verification_required,
        "success_criteria": [
            {
                "id": criterion.id,
                "description": criterion.description,
                "check_type": criterion.check_type,
                "expression": criterion.expression,
            }
            for criterion in step.success_criteria
        ],
        "status": step.status.value,
        "result": None if step.result is None else _result_to_dict(step.result),
        "blocker": None if step.blocker is None else _blocker_to_dict(step.blocker),
        "created_at": step.created_at.isoformat(),
        "updated_at": step.updated_at.isoformat(),
    }


def _result_to_dict(result: StepResult) -> dict[str, Any]:
    return {
        "success": result.success,
        "summary": result.summary,
        "evidence": [
            {
                "kind": item.kind,
                "summary": item.summary,
                "verified": item.verified,
                "confidence": item.confidence,
                "reference": item.reference,
                "created_at": item.created_at.isoformat(),
            }
            for item in result.evidence
        ],
        "completed_at": result.completed_at.isoformat(),
    }


def _blocker_to_dict(blocker: Blocker) -> dict[str, Any]:
    return {
        "reason": blocker.reason,
        "needs_user": blocker.needs_user,
        "created_at": blocker.created_at.isoformat(),
        "resolved_at": None if blocker.resolved_at is None else blocker.resolved_at.isoformat(),
    }


def goal_from_dict(data: dict[str, Any]) -> Goal:
    return Goal(
        id=data["id"],
        objective=data["objective"],
        status=GoalStatus(data["status"]),
        steps=[_step_from_dict(item) for item in data.get("steps", [])],
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
        revision=int(data.get("revision", 1)),
    )


def _step_from_dict(data: dict[str, Any]) -> PlanStep:
    blocker_data = data.get("blocker")
    result_data = data.get("result")
    success_criteria_data = data.get("success_criteria", [])
    return PlanStep(
        id=data["id"],
        title=data["title"],
        description=data.get("description", ""),
        dependencies=tuple(data.get("dependencies", [])),
        verification_required=bool(data.get("verification_required", True)),
        success_criteria=tuple(
            SuccessCriterion(
                id=item["id"],
                description=item.get("description", ""),
                check_type=item.get("check_type", "machine"),
                expression=item.get("expression"),
            )
            for item in success_criteria_data
        ),
        status=StepStatus(data["status"]),
        result=None if result_data is None else _result_from_dict(result_data),
        blocker=None if blocker_data is None else Blocker(
            reason=blocker_data["reason"],
            needs_user=bool(blocker_data.get("needs_user", False)),
            created_at=datetime.fromisoformat(blocker_data["created_at"]),
            resolved_at=_date(blocker_data.get("resolved_at")),
        ),
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
    )


def _result_from_dict(data: dict[str, Any]) -> StepResult:
    evidence = tuple(
        Evidence(
            kind=item["kind"],
            summary=item["summary"],
            verified=bool(item["verified"]),
            confidence=float(item.get("confidence", 1.0)),
            reference=item.get("reference"),
            created_at=datetime.fromisoformat(item["created_at"]),
        )
        for item in data.get("evidence", [])
    )
    return StepResult(
        success=bool(data["success"]),
        summary=data["summary"],
        evidence=evidence,
        completed_at=datetime.fromisoformat(data["completed_at"]),
    )
