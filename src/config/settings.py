"""
Nexus Configuration Management.

Central configuration for all Nexus components.
Persisted to ~/.nexus/config.json as JSON.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class NexusConfig:
    """Master configuration for Nexus."""

    # Audio
    mic_device_index: int | None = None
    speaker_device_index: int | None = None
    sample_rate: int = 16000
    playback_volume: float = 0.8
    tts_voice: str = "en_US-lessac-medium"
    tts_speed: float = 1.0

    # STT
    stt_model_size: str = "base"
    stt_language: str = "et"

    # LLM
    llm_model: str = "llama3.1"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2048
    ollama_url: str = "http://localhost:11434"

    # Vision
    camera_index: int = 0
    camera_resolution: tuple[int, int] = (640, 480)
    camera_fps: int = 15

    # Memory
    memory_path: str = str(Path("~/.nexus/memory").expanduser())

    # UI
    theme: str = "dark"
    language: str = "et"

    def save(self, path: Path | str | None = None) -> None:
        """Save config to JSON file."""
        if path is None:
            path = Path("~/.nexus/config.json").expanduser()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(self)
        # tuple -> list for JSON
        data["camera_resolution"] = list(data["camera_resolution"])
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path | str | None = None) -> NexusConfig:
        """Load config from JSON file, returning defaults if missing."""
        if path is None:
            path = Path("~/.nexus/config.json").expanduser()
        path = Path(path)
        if not path.exists():
            return cls()
        try:
            data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            if "camera_resolution" in data and isinstance(data["camera_resolution"], list):
                data["camera_resolution"] = tuple(data["camera_resolution"])
            return cls(**data)
        except Exception:
            return cls()
