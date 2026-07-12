"""Construction helper for persistent Nexus task management."""

from __future__ import annotations

from pathlib import Path

from .manager import TaskManager
from .store import TaskStore


def create_task_manager(path: Path | str = Path("~/.nexus/tasks")) -> TaskManager:
    """Create a task manager backed by local atomic JSON storage."""
    return TaskManager(TaskStore(path))
