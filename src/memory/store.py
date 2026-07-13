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

from .models import (
    DEFAULT_RETENTION,
    MemoryEntry,
    MemoryResult,
    MemoryScope,
    MemorySource,
    MemoryType,
    SensitivityLevel,
)

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


def _entry_from_legacy(item: dict[str, Any]) -> MemoryEntry:
    """Convert a legacy v1 memory dict into a v2 MemoryEntry with safe defaults."""
    now = _utc_now().isoformat()
    return MemoryEntry(
        id=item.get("id", uuid.uuid4().hex),
        memory_type=MemoryType.EPISODIC,
        text=item.get("text", ""),
        source=MemorySource.USER_STATED,
        confidence=float(item.get("metadata", {}).get("confidence", 0.5)),
        importance=float(item.get("metadata", {}).get("importance", 0.5)),
        sensitivity=SensitivityLevel(item.get("metadata", {}).get("sensitivity", "low")),
        scope=MemoryScope.GLOBAL,
        created_at=item.get("created_at", now),
        updated_at=item.get("updated_at", now),
        metadata=item.get("metadata", {}),
        supersedes=item.get("metadata", {}).get("supersedes"),
        summary_of=tuple(item.get("metadata", {}).get("summary_of", [])),
    )


def _entry_to_dict(entry: MemoryEntry) -> dict[str, Any]:
    """Serialize a MemoryEntry, flattening enums and tuples for JSON."""
    data = asdict(entry)
    data["memory_type"] = entry.memory_type.value
    data["source"] = entry.source.value
    data["sensitivity"] = entry.sensitivity.value
    data["scope"] = entry.scope.value
    data["summary_of"] = list(entry.summary_of)
    return data


class MemoryStore:
    """Thread-safe JSON store for structured, multi-layer memory."""

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
        memory_type: MemoryType = MemoryType.EPISODIC,
        source: MemorySource = MemorySource.USER_STATED,
        confidence: float = 0.5,
        importance: float = 0.5,
        sensitivity: SensitivityLevel = SensitivityLevel.LOW,
        scope: MemoryScope = MemoryScope.GLOBAL,
        metadata: dict[str, Any] | None = None,
        created_at: datetime | None = None,
        supersedes: str | None = None,
        summary_of: tuple[str, ...] = (),
        persist: bool = True,
    ) -> MemoryEntry:
        """Add a non-empty memory and optionally persist it immediately."""
        text = text.strip()
        if not text:
            raise ValueError("Memory text cannot be empty")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if not 0.0 <= importance <= 1.0:
            raise ValueError("importance must be between 0.0 and 1.0")
        timestamp = created_at or _utc_now()
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        now_iso = timestamp.astimezone(timezone.utc).isoformat()
        entry = MemoryEntry(
            id=uuid.uuid4().hex,
            memory_type=memory_type,
            text=text,
            source=source,
            confidence=confidence,
            importance=importance,
            sensitivity=sensitivity,
            scope=scope,
            created_at=now_iso,
            updated_at=now_iso,
            metadata=dict(metadata or {}),
            supersedes=supersedes,
            summary_of=summary_of,
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
            payload = {
                "version": 2,
                "entries": [_entry_to_dict(entry) for entry in self._entries],
            }
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
                version = payload.get("version", 1)
                if version == 1:
                    self._entries = [_entry_from_legacy(item) for item in raw_entries]
                else:
                    for item in raw_entries:
                        item.setdefault("supersedes", None)
                        if "summary_of" in item and isinstance(item["summary_of"], list):
                            item["summary_of"] = tuple(item["summary_of"])
                        elif "summary_of" not in item:
                            item["summary_of"] = ()
                    self._entries = [MemoryEntry(**item) for item in raw_entries]
            except (OSError, json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
                raise ValueError(f"Cannot load memory store from {self.path}") from exc
            self.prune(persist=False)

    def migrate(self) -> int:
        """Migrate legacy entries in place if needed; returns number migrated."""
        with self._lock:
            if not self._entries:
                return 0
            legacy_count = sum(
                1 for entry in self._entries if entry.memory_type == MemoryType.EPISODIC
                and entry.source == MemorySource.USER_STATED
                and not entry.metadata
                and entry.scope == MemoryScope.GLOBAL
            )
            if legacy_count:
                self.save()
            return legacy_count
