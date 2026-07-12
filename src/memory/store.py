"""Persistent, local conversation memory with lightweight similarity search."""

from __future__ import annotations

import json
import math
import re
import threading
import uuid
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_TOKEN_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _tokens(text: str) -> Counter[str]:
    return Counter(_TOKEN_PATTERN.findall(text.casefold()))


def _similarity(query: Counter[str], document: Counter[str]) -> float:
    """Return cosine similarity between token-frequency vectors."""
    if not query or not document:
        return 0.0
    dot_product = sum(count * document.get(token, 0) for token, count in query.items())
    query_norm = math.sqrt(sum(count * count for count in query.values()))
    document_norm = math.sqrt(sum(count * count for count in document.values()))
    return dot_product / (query_norm * document_norm)


@dataclass(frozen=True, slots=True)
class MemoryEntry:
    """One persisted conversation snippet."""

    id: str
    text: str
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MemoryResult:
    """A memory entry and its relevance score."""

    entry: MemoryEntry
    score: float


class MemoryStore:
    """Thread-safe JSON store for small, local conversation histories."""

    def __init__(
        self,
        path: Path | str,
        *,
        storage_format: str = "json",
        max_entries: int = 1000,
        max_age_days: int | None = 90,
    ) -> None:
        if storage_format.casefold() != "json":
            raise ValueError("Only the 'json' memory storage format is supported")
        if max_entries < 1:
            raise ValueError("max_entries must be at least 1")
        if max_age_days is not None and max_age_days < 1:
            raise ValueError("max_age_days must be at least 1 or None")

        configured_path = Path(path).expanduser()
        self.path = (
            configured_path / "memories.json"
            if configured_path.suffix.casefold() != ".json"
            else configured_path
        )
        self.storage_format = "json"
        self.max_entries = max_entries
        self.max_age_days = max_age_days
        self._entries: list[MemoryEntry] = []
        self._lock = threading.RLock()
        self.load()

    @property
    def entries(self) -> tuple[MemoryEntry, ...]:
        """Return an immutable snapshot of stored entries."""
        with self._lock:
            return tuple(self._entries)

    def add(
        self,
        text: str,
        *,
        metadata: dict[str, Any] | None = None,
        created_at: datetime | None = None,
        persist: bool = True,
    ) -> MemoryEntry:
        """Add a non-empty snippet and optionally persist it immediately."""
        text = text.strip()
        if not text:
            raise ValueError("Memory text cannot be empty")
        timestamp = created_at or _utc_now()
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        entry = MemoryEntry(
            id=uuid.uuid4().hex,
            text=text,
            created_at=timestamp.astimezone(timezone.utc).isoformat(),
            metadata=dict(metadata or {}),
        )
        with self._lock:
            self._entries.append(entry)
            self.prune(persist=False)
            if persist:
                self.save()
        return entry

    def search(self, query: str, *, limit: int = 5) -> list[MemoryResult]:
        """Rank entries by token-frequency cosine similarity."""
        if limit < 1:
            return []
        query_tokens = _tokens(query)
        if not query_tokens:
            return []
        with self._lock:
            results = [
                MemoryResult(entry=entry, score=_similarity(query_tokens, _tokens(entry.text)))
                for entry in self._entries
            ]
        matching = (result for result in results if result.score > 0)
        return sorted(matching, key=lambda result: (result.score, result.entry.created_at), reverse=True)[
            :limit
        ]

    def prune(self, *, now: datetime | None = None, persist: bool = True) -> int:
        """Remove expired entries and then enforce the configured capacity."""
        current_time = now or _utc_now()
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
        with self._lock:
            before = len(self._entries)
            if self.max_age_days is not None:
                cutoff = current_time.astimezone(timezone.utc) - timedelta(days=self.max_age_days)
                self._entries = [
                    entry
                    for entry in self._entries
                    if datetime.fromisoformat(entry.created_at) >= cutoff
                ]
            self._entries.sort(key=lambda entry: entry.created_at)
            if len(self._entries) > self.max_entries:
                self._entries = self._entries[-self.max_entries :]
            removed = before - len(self._entries)
            if persist and removed:
                self.save()
            return removed

    def save(self) -> None:
        """Atomically persist the current entries as UTF-8 JSON."""
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path = self.path.with_suffix(self.path.suffix + ".tmp")
            payload = {"version": 1, "entries": [asdict(entry) for entry in self._entries]}
            temporary_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            temporary_path.replace(self.path)

    def load(self) -> None:
        """Load entries from disk; missing storage starts empty."""
        with self._lock:
            if not self.path.exists():
                self._entries = []
                return
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
                raw_entries = payload.get("entries", [])
                self._entries = [MemoryEntry(**item) for item in raw_entries]
            except (OSError, json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
                raise ValueError(f"Cannot load memory store from {self.path}") from exc
            self.prune(persist=False)
