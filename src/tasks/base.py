"""Persistence and event support shared by task management operations."""

from __future__ import annotations

import logging
from collections.abc import Callable

from .models import Goal, GoalStatus, StepStatus, TaskEvent, TaskStateError, utc_now
from .store import TaskStore

logger = logging.getLogger(__name__)


class TaskManagerBase:
    """Internal storage, lookup, recovery, and event behavior."""

    def __init__(self, store: TaskStore) -> None:
        self.store = store
        self._goals = {goal.id: goal for goal in store.load()}
        self._subscribers: list[Callable[[TaskEvent], None]] = []
        if self._recover_interrupted():
            self._save()

    def subscribe(self, callback: Callable[[TaskEvent], None]) -> None:
        self._subscribers.append(callback)

    def _goal(self, goal_id: str) -> Goal:
        try:
            return self._goals[goal_id]
        except KeyError as exc:
            raise KeyError(f"Unknown goal: {goal_id}") from exc

    def _editable_goal(self, goal_id: str) -> Goal:
        goal = self._goal(goal_id)
        if goal.status in {GoalStatus.COMPLETED, GoalStatus.CANCELLED}:
            raise TaskStateError(f"Cannot amend goal from {goal.status.value}")
        return goal

    def _changed(self, goal: Goal, action: str, step_id: str | None = None) -> None:
        self._touch(goal)
        self._save()
        self._emit(goal, action, step_id)

    def _touch(self, goal: Goal) -> None:
        goal.updated_at = utc_now()
        goal.revision += 1

    def _recover_interrupted(self) -> bool:
        changed = False
        for goal in self._goals.values():
            if goal.status is GoalStatus.ACTIVE:
                goal.status = GoalStatus.PAUSED
                changed = True
            for step in goal.steps:
                if step.status is StepStatus.ACTIVE:
                    step.status = StepStatus.PAUSED
                    changed = True
        return changed

    def _save(self) -> None:
        self.store.save(list(self._goals.values()))

    def _emit(self, goal: Goal, action: str, step_id: str | None = None) -> None:
        event = TaskEvent(goal.id, action, goal.status, step_id)
        for subscriber in tuple(self._subscribers):
            try:
                subscriber(event)
            except Exception:
                logger.exception("Task event subscriber failed")
