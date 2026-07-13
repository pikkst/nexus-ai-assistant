"""Construction helper for the learning layer."""

from __future__ import annotations

from pathlib import Path

from src.memory import MemoryManager, MemoryStore
from .quarantine import QuarantineManager
from .reflection import ReflectionEngine
from .store import LessonStore


def create_learning_layer(
    path: Path | str = Path("~/.nexus/learning").expanduser(),
    memory_manager: MemoryManager | None = None,
) -> tuple[LessonStore, ReflectionEngine, QuarantineManager]:
    store = LessonStore(path)
    quarantine = QuarantineManager(store)
    reflection = ReflectionEngine(
        memory_manager=memory_manager,
        lesson_store=store,
        quarantine=quarantine,
    )
    return store, reflection, quarantine
