"""Persistent goal and plan manager for Nexus."""

from __future__ import annotations

import copy
from collections.abc import Callable, Sequence

from . import operations
from .base import TaskManagerBase
from .models import Evidence, Goal, PlanStep, StepStatus, TaskStateError, utc_now
from .store import TaskStore

class TaskManager(TaskManagerBase):
    """Create, inspect, amend, persist, pause, and resume plans."""

    def __init__(self, store: TaskStore) -> None:
        super().__init__(store)

    def create_goal(self, objective: str) -> Goal:
        if not objective.strip():
            raise ValueError("objective must not be empty")
        goal = Goal(objective.strip())
        self._goals[goal.id] = goal
        self._save()
        self._emit(goal, "goal_created")
        return copy.deepcopy(goal)

    def get_goal(self, goal_id: str) -> Goal:
        return copy.deepcopy(self._goal(goal_id))

    def list_goals(self) -> tuple[Goal, ...]:
        ordered = sorted(self._goals.values(), key=lambda goal: goal.created_at)
        return tuple(copy.deepcopy(goal) for goal in ordered)

    def add_step(
        self,
        goal_id: str,
        title: str,
        *,
        description: str = "",
        dependencies: Sequence[str] = (),
        verification_required: bool = True,
    ) -> PlanStep:
        goal = self._editable_goal(goal_id)
        if not title.strip():
            raise ValueError("step title must not be empty")
        known = {step.id for step in goal.steps}
        unknown = set(dependencies) - known
        if unknown:
            raise TaskStateError(f"Unknown dependencies: {', '.join(sorted(unknown))}")
        step = PlanStep(
            title=title.strip(), description=description.strip(),
            dependencies=tuple(dict.fromkeys(dependencies)),
            verification_required=verification_required,
        )
        goal.steps.append(step)
        self._touch(goal)
        self._save()
        self._emit(goal, "step_added", step.id)
        return copy.deepcopy(step)

    def amend_step(
        self, goal_id: str, step_id: str, *, title: str | None = None,
        description: str | None = None,
    ) -> PlanStep:
        goal = self._editable_goal(goal_id)
        step = operations.find_step(goal, step_id)
        if step.status not in {StepStatus.PENDING, StepStatus.PAUSED, StepStatus.WAITING}:
            raise TaskStateError(f"Cannot amend step from {step.status.value}")
        if title is not None:
            if not title.strip():
                raise ValueError("step title must not be empty")
            step.title = title.strip()
        if description is not None:
            step.description = description.strip()
        step.updated_at = utc_now()
        self._changed(goal, "step_amended", step.id)
        return copy.deepcopy(step)

    def start_goal(self, goal_id: str) -> None:
        self._apply(goal_id, "goal_started", operations.start_goal)

    def start_step(self, goal_id: str, step_id: str) -> None:
        self._apply(goal_id, "step_started", operations.start_step, step_id, step_id=step_id)

    def pause_goal(self, goal_id: str) -> None:
        self._apply(goal_id, "goal_paused", operations.pause_goal)

    def resume_goal(self, goal_id: str) -> None:
        self._apply(goal_id, "goal_resumed", operations.resume_goal)

    def cancel_goal(self, goal_id: str) -> None:
        self._apply(goal_id, "goal_cancelled", operations.cancel_goal)

    def block_step(self, goal_id: str, step_id: str, reason: str, *, needs_user: bool = False) -> None:
        self._apply(
            goal_id, "step_blocked", operations.block_step, step_id, reason, needs_user,
            step_id=step_id,
        )

    def resolve_blocker(self, goal_id: str, step_id: str) -> None:
        self._apply(goal_id, "blocker_resolved", operations.resolve_blocker, step_id, step_id=step_id)

    def complete_step(
        self, goal_id: str, step_id: str, summary: str,
        evidence: Sequence[Evidence] = (),
    ) -> None:
        self._apply(
            goal_id, "step_completed", operations.complete_step,
            step_id, summary, tuple(evidence), step_id=step_id,
        )

    def fail_step(self, goal_id: str, step_id: str, summary: str) -> None:
        self._apply(goal_id, "step_failed", operations.fail_step, step_id, summary, step_id=step_id)

    def complete_goal(self, goal_id: str) -> None:
        self._apply(goal_id, "goal_completed", operations.complete_goal)

    def _apply(self, goal_id: str, action: str, operation: Callable[..., None], *args: object,
               step_id: str | None = None) -> None:
        goal = self._goal(goal_id)
        operation(goal, *args)
        self._changed(goal, action, step_id)
