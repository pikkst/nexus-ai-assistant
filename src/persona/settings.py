"""Persona manager with settings persistence and bounded behavior."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, time
from pathlib import Path
from typing import Any, Callable

from .models import PersonaMode, PersonaResponseMetadata, PersonaSettings

logger = logging.getLogger(__name__)


class PersonaManager:
    """Manage persona settings, persistence, and bounded style guidance."""

    def __init__(
        self,
        settings: PersonaSettings | None = None,
        path: str | Path | None = None,
    ) -> None:
        self.path = Path(path) if path is not None else Path("~/.nexus/persona.json").expanduser()
        self.settings = settings or PersonaSettings()
        self._proactive_last_sent: datetime | None = None
        self._on_change: Callable[[PersonaSettings], None] | None = None

    def set_on_change(self, callback: Callable[[PersonaSettings], None]) -> None:
        self._on_change = callback

    def _notify(self) -> None:
        if self._on_change:
            try:
                self._on_change(self.settings)
            except Exception:
                logger.exception("Persona change callback failed")

    def update(self, **kwargs: Any) -> PersonaSettings:
        current = asdict(self.settings)
        current.update(kwargs)
        new_settings = PersonaSettings(**current)
        if new_settings.quiet_hours_start is not None and not isinstance(
            new_settings.quiet_hours_start, time
        ):
            raise TypeError("quiet_hours_start must be a time instance")
        if new_settings.quiet_hours_end is not None and not isinstance(
            new_settings.quiet_hours_end, time
        ):
            raise TypeError("quiet_hours_end must be a time instance")
        self.settings = new_settings
        self._notify()
        return self.settings

    def set_mode(self, mode: PersonaMode | str) -> PersonaSettings:
        return self.update(mode=PersonaMode(mode))

    def is_quiet_hours(self, *, now: datetime | None = None) -> bool:
        if self.settings.quiet_hours_start is None or self.settings.quiet_hours_end is None:
            return False
        current = (now or datetime.now()).time()
        start = self.settings.quiet_hours_start
        end = self.settings.quiet_hours_end
        if start <= end:
            return start <= current <= end
        return current >= start or current <= end

    def can_send_proactive(self, *, now: datetime | None = None) -> bool:
        if not self.settings.unsolicited_suggestions:
            return False
        if self.is_quiet_hours():
            return False
        if self._proactive_last_sent is None:
            return True
        current = now or datetime.now()
        delta = (current - self._proactive_last_sent).total_seconds()
        rate_limit = max(60.0, 3600.0 * (1.1 - self.settings.proactivity))
        return delta >= rate_limit

    def mark_proactive_sent(self, *, now: datetime | None = None) -> None:
        self._proactive_last_sent = now or datetime.now()

    def response_metadata(self, confidence: float = 0.8) -> PersonaResponseMetadata:
        mode = self.settings.mode
        if mode == PersonaMode.COMPANION:
            emotion = "happy"
            voice_energy = 0.7 + self.settings.playfulness * 0.3
            detail_level = "normal"
        elif mode == PersonaMode.FOCUSED:
            emotion = "neutral"
            voice_energy = 0.3 + self.settings.playfulness * 0.2
            detail_level = "concise" if self.settings.response_detail < 0.4 else "normal"
        else:
            emotion = "neutral"
            voice_energy = 0.5 + self.settings.playfulness * 0.2
            detail_level = "normal" if self.settings.response_detail < 0.7 else "detailed"
        detail_level = self._clamp_detail(detail_level)
        return PersonaResponseMetadata(
            emotion=emotion,
            voice_energy=min(1.0, max(0.0, voice_energy)),
            confidence=min(1.0, max(0.0, confidence)),
            detail_level=detail_level,
            should_suggest=self.settings.unsolicited_suggestions and self.can_send_proactive(),
        )

    def _clamp_detail(self, level: str) -> str:
        mapping = {"concise": 0.0, "normal": 0.5, "detailed": 1.0}
        current = mapping.get(level, 0.5)
        if self.settings.response_detail < 0.33:
            return "concise"
        if self.settings.response_detail > 0.66:
            return "detailed"
        return "normal"

    def apply_persona(self, base_prompt: str) -> str:
        mode = self.settings.mode.value
        playfulness = self.settings.playfulness
        detail = self.settings.response_detail
        tone_guidance = (
            "Use warm, brief responses with light emoji sparingly."
            if playfulness > 0.7
            else "Keep responses factual and concise."
            if playfulness < 0.3
            else "Balance warmth and clarity."
        )
        detail_guidance = (
            "Provide short, focused answers."
            if detail < 0.33
            else "Offer thorough explanations with context."
            if detail > 0.66
            else "Provide clear, complete answers."
        )
        return (
            f"{base_prompt}\n\n"
            f"Persona mode: {mode}. {tone_guidance} {detail_guidance}\n"
            "Always preserve factual accuracy, cite uncertainty, and respect user control."
        )

    def save(self, path: Path | str | None = None) -> None:
        target = Path(path) if path is not None else self.path
        target.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(self.settings)
        data["mode"] = self.settings.mode.value
        data["quiet_hours_start"] = (
            self.settings.quiet_hours_start.isoformat()
            if self.settings.quiet_hours_start
            else None
        )
        data["quiet_hours_end"] = (
            self.settings.quiet_hours_end.isoformat()
            if self.settings.quiet_hours_end
            else None
        )
        target.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path | str | None = None) -> PersonaManager:
        target = Path(path) if path is not None else Path("~/.nexus/persona.json").expanduser()
        if not target.exists():
            return cls()
        try:
            data: dict[str, Any] = json.loads(target.read_text(encoding="utf-8"))
            if not data:
                return cls()
            start = data.pop("quiet_hours_start", None)
            end = data.pop("quiet_hours_end", None)
            if start:
                data["quiet_hours_start"] = time.fromisoformat(start)
            if end:
                data["quiet_hours_end"] = time.fromisoformat(end)
            if "mode" in data:
                data["mode"] = PersonaMode(data["mode"])
            return cls(settings=PersonaSettings(**data), path=target)
        except Exception:
            return cls()
        try:
            data: dict[str, Any] = json.loads(target.read_text(encoding="utf-8"))
            if not data:
                return cls()
            start = data.pop("quiet_hours_start", None)
            end = data.pop("quiet_hours_end", None)
            if start:
                data["quiet_hours_start"] = datetime.fromisoformat(start).time()
            if end:
                data["quiet_hours_end"] = datetime.fromisoformat(end).time()
            if "mode" in data:
                data["mode"] = PersonaMode(data["mode"])
            return cls(settings=PersonaSettings(**data), path=target)
        except Exception:
            return cls()
