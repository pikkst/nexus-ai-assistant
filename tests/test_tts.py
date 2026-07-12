"""Tests for local text-to-speech synthesis."""

from __future__ import annotations

import asyncio
import sys
import wave
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from src.tts.engine import TTSConfig, TTSEngine, TTSModelError, TTSState


class FakeVoice:
    def synthesize(self, text: str, wav_file: wave.Wave_write, length_scale: float) -> None:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        wav_file.writeframes(np.array([0, 16384, -16384], dtype=np.int16).tobytes())


def install_fake_piper(loader: MagicMock) -> dict[str, ModuleType]:
    package = ModuleType("piper")
    voice_module = ModuleType("piper.voice")
    voice_module.PiperVoice = MagicMock(load=loader)  # type: ignore[attr-defined]
    return {"piper": package, "piper.voice": voice_module}


def test_config_rejects_invalid_requests() -> None:
    with pytest.raises(ValueError, match="speed"):
        TTSConfig(speed=0)
    with pytest.raises(ValueError, match="voice"):
        TTSConfig(voice=" ")


@pytest.mark.asyncio
async def test_synthesis_returns_playback_compatible_audio() -> None:
    model = Path("pyproject.toml").resolve()
    loader = MagicMock(return_value=FakeVoice())
    engine = TTSEngine(TTSConfig(voice=str(model), speed=1.25, language="et"))

    with patch.dict(sys.modules, install_fake_piper(loader)):
        await engine.load_model()
        result = await engine.synthesize("Tere, Nexus!")

    assert result.sample_rate == 22050
    assert result.audio.dtype == np.float32
    assert result.audio.shape == (3,)
    assert result.language == "et"
    assert engine.state == TTSState.READY


@pytest.mark.asyncio
async def test_synthesis_runs_in_worker_thread() -> None:
    model = Path("pyproject.toml").resolve()
    engine = TTSEngine(TTSConfig(voice=str(model)))
    engine._voice = FakeVoice()
    engine._state = TTSState.READY

    with patch("src.tts.engine.asyncio.to_thread", wraps=asyncio.to_thread) as to_thread:
        await engine.synthesize("hello")

    to_thread.assert_awaited_once()


@pytest.mark.asyncio
async def test_speak_routes_audio_to_playback() -> None:
    engine = TTSEngine(TTSConfig(voice=str(Path("pyproject.toml").resolve())))
    engine._voice = FakeVoice()
    engine._state = TTSState.READY
    playback = MagicMock()
    playback.play = AsyncMock()

    result = await engine.speak("hello", playback)

    playback.play.assert_awaited_once_with(result.audio, sample_rate=22050)


@pytest.mark.asyncio
async def test_missing_model_reports_clear_error() -> None:
    errors: list[Exception] = []
    loader = MagicMock()
    engine = TTSEngine(
        TTSConfig(voice="missing", model_dir=Path("missing-voice-directory")),
        on_error=errors.append,
    )

    with patch.dict(sys.modules, install_fake_piper(loader)):
        with pytest.raises(TTSModelError, match="model file not found"):
            await engine.load_model()

    loader.assert_not_called()
    assert engine.state == TTSState.ERROR
    assert len(errors) == 1


@pytest.mark.asyncio
async def test_fallback_voice_is_loaded() -> None:
    fallback = Path("pyproject.toml").resolve()
    loader = MagicMock(return_value=FakeVoice())
    engine = TTSEngine(
        TTSConfig(
            voice="unsupported",
            fallback_voice=str(fallback),
            model_dir=Path("missing-voice-directory"),
        )
    )

    with patch.dict(sys.modules, install_fake_piper(loader)):
        await engine.load_model()
        result = await engine.synthesize("fallback works")

    assert result.voice == str(fallback)
    loader.assert_called_once()


@pytest.mark.asyncio
async def test_empty_text_is_rejected() -> None:
    engine = TTSEngine()
    with pytest.raises(ValueError, match="text"):
        await engine.synthesize("   ")
