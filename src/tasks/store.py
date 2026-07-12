"""Atomic JSON persistence for Nexus goals and plans."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from .codec import goal_from_dict, goal_to_dict
from .models import Goal


class TaskStore:
    """Thread-safe versioned storage for task state."""

    def __init__(self, path: Path | str) -> None:
        configured = Path(path).expanduser()
        self.path = configured / "tasks.json" if configured.suffix.lower() != ".json" else configured
        self._lock = threading.RLock()

    def save(self, goals: list[Goal]) -> None:
        payload = {"version": 1, "goals": [goal_to_dict(goal) for goal in goals]}
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(self.path.suffix + ".tmp")
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            temporary.replace(self.path)

    def load(self) -> list[Goal]:
        with self._lock:
            if not self.path.exists():
                return []
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
                if payload.get("version") != 1:
                    raise ValueError("Unsupported task store version")
                return [goal_from_dict(item) for item in payload.get("goals", [])]
            except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Cannot load task store from {self.path}") from exc
