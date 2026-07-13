"""Validated state operations for goals and plan steps."""

from __future__ import annotations

from .models import (
    Blocker,
    Evidence,
    Goal,
    GoalStatus,
    PlanStep,
    StepResult,
    StepStatus,
    TaskStateError,
    utc_now,
)

_FINAL_GOALS = {GoalStatus.COMPLETED, GoalStatus.CANCELLED}
_FINAL_STEPS = {StepStatus.COMPLETED, StepStatus.CANCELLED}


def find_step(goal: Goal, step_id: str) -> PlanStep:
    try:
        return next(step for step in goal.steps if step.id == step_id)
    except StopIteration as exc:
        raise KeyError(f"Unknown step: {step_id}") from exc


def start_goal(goal: Goal) -> None:
    if goal.status not in {GoalStatus.PENDING, GoalStatus.PAUSED, GoalStatus.WAITING}:
        raise TaskStateError(f"Cannot start goal from {goal.status.value}")
    goal.status = GoalStatus.ACTIVE


def start_step(goal: Goal, step_id: str) -> None:
    if goal.status not in {GoalStatus.ACTIVE, GoalStatus.PAUSED}:
        raise TaskStateError("Goal must be active or paused before starting a step")
    step = find_step(goal, step_id)
    if step.status not in {StepStatus.PENDING, StepStatus.PAUSED, StepStatus.WAITING}:
        raise TaskStateError(f"Cannot start step from {step.status.value}")
    completed = {item.id for item in goal.steps if item.status is StepStatus.COMPLETED}
    missing = set(step.dependencies) - completed
    if missing:
        raise TaskStateError(f"Incomplete dependencies: {', '.join(sorted(missing))}")
    for item in goal.steps:
        if item.status is StepStatus.ACTIVE and item.id != step.id:
            raise TaskStateError("Another plan step is already active")
    goal.status = GoalStatus.ACTIVE
    step.status = StepStatus.ACTIVE
    step.updated_at = utc_now()


def pause_goal(goal: Goal) -> None:
    if goal.status not in {GoalStatus.ACTIVE, GoalStatus.WAITING, GoalStatus.BLOCKED}:
        raise TaskStateError(f"Cannot pause goal from {goal.status.value}")
    goal.status = GoalStatus.PAUSED
    for step in goal.steps:
        if step.status is StepStatus.ACTIVE:
            step.status = StepStatus.PAUSED
            step.updated_at = utc_now()


def resume_goal(goal: Goal) -> None:
    if goal.status not in {GoalStatus.PAUSED, GoalStatus.WAITING}:
        raise TaskStateError(f"Cannot resume goal from {goal.status.value}")
    goal.status = GoalStatus.ACTIVE


def cancel_goal(goal: Goal) -> None:
    if goal.status in _FINAL_GOALS:
        raise TaskStateError(f"Cannot cancel goal from {goal.status.value}")
    goal.status = GoalStatus.CANCELLED
    for step in goal.steps:
        if step.status not in _FINAL_STEPS:
            step.status = StepStatus.CANCELLED
            step.updated_at = utc_now()


def block_step(goal: Goal, step_id: str, reason: str, needs_user: bool) -> None:
    step = find_step(goal, step_id)
    if step.status in _FINAL_STEPS:
        raise TaskStateError(f"Cannot block step from {step.status.value}")
    if not reason.strip():
        raise ValueError("blocker reason must not be empty")
    step.blocker = Blocker(reason.strip(), needs_user=needs_user)
    step.status = StepStatus.BLOCKED
    step.updated_at = utc_now()
    goal.status = GoalStatus.BLOCKED


def resolve_blocker(goal: Goal, step_id: str) -> None:
    step = find_step(goal, step_id)
    if step.status is not StepStatus.BLOCKED or step.blocker is None:
        raise TaskStateError("Step is not blocked")
    step.blocker.resolved_at = utc_now()
    step.status = StepStatus.PENDING
    step.updated_at = utc_now()
    goal.status = GoalStatus.PAUSED


def complete_step(
    goal: Goal, step_id: str, summary: str, evidence: tuple[Evidence, ...]
) -> None:
    step = find_step(goal, step_id)
    if step.status is not StepStatus.ACTIVE:
        raise TaskStateError("Only an active step can complete")
    if not summary.strip():
        raise ValueError("result summary must not be empty")
    if step.verification_required and not any(item.verified for item in evidence):
        raise TaskStateError("Verified evidence or user confirmation is required")
    step.result = StepResult(True, summary.strip(), evidence)
    step.status = StepStatus.COMPLETED
    step.updated_at = utc_now()
    goal.status = GoalStatus.WAITING


def fail_step(goal: Goal, step_id: str, summary: str) -> None:
    step = find_step(goal, step_id)
    if step.status is not StepStatus.ACTIVE:
        raise TaskStateError("Only an active step can fail")
    step.result = StepResult(False, summary.strip())
    step.status = StepStatus.FAILED
    step.updated_at = utc_now()
    goal.status = GoalStatus.FAILED


def complete_goal(goal: Goal) -> None:
    if not goal.steps or any(step.status is not StepStatus.COMPLETED for step in goal.steps):
        raise TaskStateError("Every plan step must be completed")
    goal.status = GoalStatus.COMPLETED


def revert_step_for_rework(goal: Goal, step_id: str) -> None:
    step = find_step(goal, step_id)
    if step.status is not StepStatus.FAILED:
        raise TaskStateError("Only a failed step can be reverted for rework")
    step.status = StepStatus.PENDING
    step.result = None
    step.updated_at = utc_now()
    goal.status = GoalStatus.PAUSED
