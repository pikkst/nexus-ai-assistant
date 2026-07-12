"""Tests for configuration-driven Nexus runtime construction."""

from __future__ import annotations

from src.app import create_runtime
from src.config import NexusConfig


def test_factory_respects_disabled_features() -> None:
    runtime = create_runtime(
        NexusConfig(enable_audio_input=False, enable_audio_output=False, enable_memory=False)
    )

    assert runtime.services.capture is None
    assert runtime.services.stt is None
    assert runtime.services.playback is None
    assert runtime.services.tts is None
    assert runtime.services.memory is None
