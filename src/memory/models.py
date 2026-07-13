"""Memory types, provenance fields, and core contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MemoryType(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PREFERENCE = "preference"
    PROCEDURAL = "procedural"


class MemoryScope(str, Enum):
    GLOBAL = "global"
    PROJECT = "project"
    SESSION = "session"


class SensitivityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MemorySource(str, Enum):
    USER_STATED = "user_stated"
    ASSISTANT_INFERRED = "assistant_inferred"
    TOOL_OUTPUT = "tool_output"
    EXTERNAL = "external"


@dataclass(frozen=True, slots=True)
class MemoryEntry:
    """One structured memory record with full provenance."""

    id: str
    memory_type: MemoryType
    text: str
    source: MemorySource
    confidence: float
    importance: float
    sensitivity: SensitivityLevel
    scope: MemoryScope
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = field(default_factory=dict)
    supersedes: str | None = None
    summary_of: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MemoryResult:
    """A memory entry and its relevance score."""

    entry: MemoryEntry
    score: float
    retrieval_path: str = "keyword"


@dataclass(frozen=True, slots=True)
class ContradictionRecord:
    """Record of a detected contradiction between memories."""

    existing_id: str
    incoming_id: str
    existing_text: str
    incoming_text: str
    resolution: str
    resolved_at: str


@dataclass(frozen=True, slots=True)
class MemorySummary:
    """Condensed representation of a group of memories."""

    id: str
    summary_text: str
    source_ids: tuple[str, ...]
    memory_type: MemoryType
    created_at: str
    importance: float
    confidence: float


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    """Retention rules for a memory type or scope."""

    max_age_days: int | None = 90
    max_entries: int | None = 1000
    min_confidence: float = 0.0
    require_source: bool = False


DEFAULT_RETENTION: dict[MemoryType, RetentionPolicy] = {
    MemoryType.WORKING: RetentionPolicy(max_age_days=1, max_entries=50, min_confidence=0.0),
    MemoryType.EPISODIC: RetentionPolicy(max_age_days=90, max_entries=500, min_confidence=0.1),
    MemoryType.SEMANTIC: RetentionPolicy(max_age_days=None, max_entries=200, min_confidence=0.5),
    MemoryType.PREFERENCE: RetentionPolicy(max_age_days=None, max_entries=100, min_confidence=0.3),
    MemoryType.PROCEDURAL: RetentionPolicy(max_age_days=None, max_entries=150, min_confidence=0.4),
}
