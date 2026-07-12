"""Persistence and restart tests for Nexus task management."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.tasks import GoalStatus, StepStatus, TaskManager, TaskStore, create_task_manager


def test_active_work_recovers_as_paused_after_restart(tmp_path: Path) -> None:
    store = TaskStore(tmp_path / "state")
    first = TaskManager(store)
    goal = first.create_goal("Survive restart")
    step = first.add_step(goal.id, "Long work")
    first.start_goal(goal.id)
    first.start_step(goal.id, step.id)

    restarted = TaskManager(store)
    recovered = restarted.get_goal(goal.id)

    assert recovered.status is GoalStatus.PAUSED
    assert recovered.steps[0].status is StepStatus.PAUSED


def test_all_fields_round_trip(tmp_path: Path) -> None:
    store = TaskStore(tmp_path / "tasks.json")
    tasks = TaskManager(store)
    goal = tasks.create_goal("Persistent goal")
    first = tasks.add_step(goal.id, "First", description="Details")
    tasks.add_step(goal.id, "Second", dependencies=[first.id], verification_required=False)

    loaded = TaskManager(store).get_goal(goal.id)

    assert loaded.objective == "Persistent goal"
    assert loaded.steps[0].description == "Details"
    assert loaded.steps[1].dependencies == (first.id,)
    assert not loaded.steps[1].verification_required


def test_corrupt_store_has_clear_error(tmp_path: Path) -> None:
    path = tmp_path / "tasks.json"
    path.write_text("{broken", encoding="utf-8")

    with pytest.raises(ValueError, match="Cannot load task store"):
        TaskManager(TaskStore(path))


def test_factory_uses_directory_storage(tmp_path: Path) -> None:
    tasks = create_task_manager(tmp_path / "nexus-tasks")
    created = tasks.create_goal("Factory goal")

    assert (tmp_path / "nexus-tasks" / "tasks.json").is_file()
    assert tasks.get_goal(created.id).objective == "Factory goal"


def test_returned_goals_cannot_mutate_manager_state(tmp_path: Path) -> None:
    tasks = create_task_manager(tmp_path)
    goal = tasks.create_goal("Protected state")
    external = tasks.get_goal(goal.id)
    external.objective = "Mutated"

    assert tasks.get_goal(goal.id).objective == "Protected state"
