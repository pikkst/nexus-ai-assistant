"""Persona and interaction mode models for Nexus."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import Any


class PersonaMode(str, Enum):
    """High-level interaction modes."""

    COMPANION = "companion"
    BALANCED = "balanced"
    FOCUSED = "focused"


@dataclass(frozen=True, slots=True)
class PersonaSettings:
    """Configurable persona behavior."""

    mode: PersonaMode = PersonaMode.BALANCED
    playfulness: float = 0.5
    proactivity: float = 0.5
    response_detail: float = 0.5
    unsolicited_suggestions: bool = True
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.playfulness <= 1.0:
            raise ValueError("playfulness must be between 0.0 and 1.0")
        if not 0.0 <= self.proactivity <= 1.0:
            raise ValueError("proactivity must be between 0.0 and 1.0")
        if not 0.0 <= self.response_detail <= 1.0:
            raise ValueError("response_detail must be between 0.0 and 1.0")


@dataclass(frozen=True, slots=True)
class PersonaResponseMetadata:
    """Structured response metadata for downstream rendering."""

    emotion: str = "neutral"
    voice_energy: float = 0.5
    confidence: float = 0.8
    detail_level: str = "normal"
    should_suggest: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.voice_energy <= 1.0:
            raise ValueError("voice_energy must be between 0.0 and 1.0")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
