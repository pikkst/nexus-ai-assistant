"""Goal lifecycle and plan validation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.tasks import (
    Evidence,
    GoalStatus,
    StepStatus,
    TaskManager,
    TaskStateError,
    TaskStore,
)


def manager(tmp_path: Path) -> TaskManager:
    return TaskManager(TaskStore(tmp_path / "tasks.json"))


def verified(summary: str = "Tests passed") -> Evidence:
    return Evidence("test", summary, verified=True, reference="pytest")


def test_multi_step_goal_requires_dependencies_and_evidence(tmp_path: Path) -> None:
    tasks = manager(tmp_path)
    goal = tasks.create_goal("Build a verified feature")
    first = tasks.add_step(goal.id, "Implement")
    second = tasks.add_step(goal.id, "Test", dependencies=[first.id])

    tasks.start_goal(goal.id)
    with pytest.raises(TaskStateError, match="Incomplete dependencies"):
        tasks.start_step(goal.id, second.id)
    tasks.start_step(goal.id, first.id)
    with pytest.raises(TaskStateError, match="Verified evidence"):
        tasks.complete_step(goal.id, first.id, "Implemented")
    tasks.complete_step(goal.id, first.id, "Implemented", [verified()])
    tasks.resume_goal(goal.id)
    tasks.start_step(goal.id, second.id)
    tasks.complete_step(goal.id, second.id, "Tested", [verified()])
    tasks.complete_goal(goal.id)

    completed = tasks.get_goal(goal.id)
    assert completed.status is GoalStatus.COMPLETED
    assert all(step.status is StepStatus.COMPLETED for step in completed.steps)


def test_user_confirmation_is_valid_evidence(tmp_path: Path) -> None:
    tasks = manager(tmp_path)
    goal = tasks.create_goal("Prepare a draft")
    step = tasks.add_step(goal.id, "Review draft")
    tasks.start_goal(goal.id)
    tasks.start_step(goal.id, step.id)

    tasks.complete_step(
        goal.id,
        step.id,
        "User approved",
        [Evidence("user_confirmation", "Approved in UI", verified=True)],
    )

    assert tasks.get_goal(goal.id).steps[0].result is not None


def test_pause_resume_cancel_and_events(tmp_path: Path) -> None:
    tasks = manager(tmp_path)
    events = []
    tasks.subscribe(events.append)
    goal = tasks.create_goal("Interruptible work")
    step = tasks.add_step(goal.id, "Work")
    tasks.start_goal(goal.id)
    tasks.start_step(goal.id, step.id)
    tasks.pause_goal(goal.id)

    paused = tasks.get_goal(goal.id)
    assert paused.status is GoalStatus.PAUSED
    assert paused.steps[0].status is StepStatus.PAUSED

    tasks.resume_goal(goal.id)
    tasks.cancel_goal(goal.id)
    assert tasks.get_goal(goal.id).status is GoalStatus.CANCELLED
    assert events[-1].action == "goal_cancelled"


def test_blocker_resolution_and_recovery(tmp_path: Path) -> None:
    tasks = manager(tmp_path)
    goal = tasks.create_goal("Needs permission")
    step = tasks.add_step(goal.id, "Send email")
    tasks.start_goal(goal.id)
    tasks.start_step(goal.id, step.id)
    tasks.block_step(goal.id, step.id, "Confirm recipient", needs_user=True)

    blocked = tasks.get_goal(goal.id)
    assert blocked.status is GoalStatus.BLOCKED
    assert blocked.steps[0].blocker is not None
    assert blocked.steps[0].blocker.needs_user

    tasks.resolve_blocker(goal.id, step.id)
    recovered = tasks.get_goal(goal.id)
    assert recovered.status is GoalStatus.PAUSED
    assert recovered.steps[0].status is StepStatus.PENDING
    assert recovered.steps[0].blocker.resolved_at is not None


def test_plan_can_be_amended_before_execution(tmp_path: Path) -> None:
    tasks = manager(tmp_path)
    goal = tasks.create_goal("Draft project")
    step = tasks.add_step(goal.id, "Old title")

    changed = tasks.amend_step(
        goal.id, step.id, title="New title", description="Clear details"
    )

    assert changed.title == "New title"
    assert changed.description == "Clear details"
    assert tasks.get_goal(goal.id).revision == 3


def test_failed_step_fails_goal(tmp_path: Path) -> None:
    tasks = manager(tmp_path)
    goal = tasks.create_goal("Fallible work")
    step = tasks.add_step(goal.id, "Run")
    tasks.start_goal(goal.id)
    tasks.start_step(goal.id, step.id)

    tasks.fail_step(goal.id, step.id, "Command failed")

    failed = tasks.get_goal(goal.id)
    assert failed.status is GoalStatus.FAILED
    assert failed.steps[0].result is not None
    assert not failed.steps[0].result.success
