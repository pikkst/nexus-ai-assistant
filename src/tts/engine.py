"""Offline text-to-speech synthesis and playback integration."""

from __future__ import annotations

import asyncio
import io
import logging
import wave
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Protocol

import numpy as np

logger = logging.getLogger(__name__)


class TTSState(Enum):
    """Operational state of the TTS engine."""

    UNLOADED = "unloaded"
    LOADING = "loading"
    READY = "ready"
    SYNTHESIZING = "synthesizing"
    ERROR = "error"


class TTSModelError(RuntimeError):
    """Raised when no usable local TTS model can be loaded."""


@dataclass(frozen=True)
class TTSConfig:
    """Configuration for local Piper synthesis."""

    voice: str = "en_US-lessac-medium"
    speed: float = 1.0
    language: str = "en"
    model_dir: Path = Path("~/.nexus/voices")
    fallback_voice: str | None = "en_US-lessac-medium"

    def __post_init__(self) -> None:
        if not self.voice.strip():
            raise ValueError("voice must not be empty")
        if self.speed <= 0:
            raise ValueError("speed must be greater than zero")
        if not self.language.strip():
            raise ValueError("language must not be empty")


@dataclass(frozen=True)
class SynthesisResult:
    """Playback-compatible mono audio produced by a synthesis request."""

    audio: np.ndarray
    sample_rate: int
    voice: str
    language: str


class PlaybackService(Protocol):
    """Subset of AudioPlayback used by the TTS engine."""

    async def play(self, audio: np.ndarray, sample_rate: int | None = None) -> None: ...


class TTSEngine:
    """Non-blocking local TTS engine backed by Piper model files."""

    def __init__(
        self,
        config: TTSConfig | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        self.config = config or TTSConfig()
        self._on_error = on_error
        self._voice: object | None = None
        self._active_voice = self.config.voice
        self._state = TTSState.UNLOADED

    @property
    def state(self) -> TTSState:
        return self._state

    @property
    def is_ready(self) -> bool:
        return self._state == TTSState.READY

    async def load_model(self) -> None:
        """Load the configured voice, trying the fallback voice when necessary."""
        if self._state in {TTSState.LOADING, TTSState.READY, TTSState.SYNTHESIZING}:
            logger.debug("TTS load_model skipped; state=%s", self._state.value)
            return
        self._state = TTSState.LOADING
        logger.info(
            "TTS loading voice=%r speed=%.2f language=%r model_dir=%s",
            self.config.voice,
            self.config.speed,
            self.config.language,
            self.config.model_dir.expanduser(),
        )
        try:
            self._voice, self._active_voice = await asyncio.to_thread(self._load_voice)
            self._state = TTSState.READY
            logger.info("TTS voice loaded successfully: %s", self._active_voice)
        except Exception as exc:
            self._voice = None
            self._state = TTSState.ERROR
            error = exc if isinstance(exc, TTSModelError) else TTSModelError(str(exc))
            self._report_error(error)
            raise error from exc

    async def unload_model(self) -> None:
        self._voice = None
        self._state = TTSState.UNLOADED

    async def synthesize(self, text: str) -> SynthesisResult:
        """Synthesize text without blocking the asyncio event loop."""
        cleaned = text.strip()
        if not cleaned:
            raise ValueError("text must not be empty")
        if not self.is_ready or self._voice is None:
            raise RuntimeError("TTS engine is not ready. Call load_model() first.")

        self._state = TTSState.SYNTHESIZING
        try:
            audio, sample_rate = await asyncio.to_thread(self._synthesize_wav, cleaned)
            return SynthesisResult(
                audio=audio,
                sample_rate=sample_rate,
                voice=self._active_voice,
                language=self.config.language,
            )
        except Exception as exc:
            self._state = TTSState.ERROR
            self._report_error(exc)
            raise RuntimeError(f"TTS synthesis failed: {exc}") from exc
        finally:
            if self._voice is not None:
                self._state = TTSState.READY

    async def speak(self, text: str, playback: PlaybackService) -> SynthesisResult:
        """Synthesize text and route the resulting samples to AudioPlayback."""
        result = await self.synthesize(text)
        await playback.play(result.audio, sample_rate=result.sample_rate)
        return result

    def _load_voice(self) -> tuple[object, str]:
        try:
            from piper.voice import PiperVoice
            logger.debug("Piper TTS module imported successfully")
        except ImportError as exc:
            logger.error("Piper TTS import failed: %s", exc)
            raise TTSModelError(
                "Piper TTS is not installed. Install the 'tts' project extra."
            ) from exc

        failures: list[str] = []
        candidates = [self.config.voice]
        if self.config.fallback_voice and self.config.fallback_voice not in candidates:
            candidates.append(self.config.fallback_voice)
        logger.debug("TTS voice candidates: %s", candidates)

        for voice_name in candidates:
            model_path = self._resolve_model_path(voice_name)
            if not model_path.is_file():
                try:
                    self._download_voice(voice_name)
                except Exception as exc:
                    logger.warning("TTS voice %r download failed: %s", voice_name, exc)
                    failures.append(f"{voice_name}: download failed ({exc})")
                    continue
            config_path = model_path.with_suffix(model_path.suffix + ".json")
            try:
                kwargs = {"config_path": config_path} if config_path.is_file() else {}
                logger.debug("TTS loading PiperVoice from %s", model_path)
                voice = PiperVoice.load(model_path, **kwargs)
                logger.info("TTS PiperVoice loaded successfully for %r", voice_name)
                return voice, voice_name
            except Exception as exc:
                failures.append(f"{voice_name}: {exc}")
                logger.error("TTS PiperVoice.load failed for %r: %s", voice_name, exc)

        logger.error("TTS no usable voice loaded. failures=%s", failures)
        raise TTSModelError("No usable TTS voice. " + "; ".join(failures))

    def _resolve_model_path(self, voice: str) -> Path:
        path = Path(voice).expanduser()
        if path.suffix == ".onnx" or path.is_absolute():
            return path
        return self.config.model_dir.expanduser() / f"{voice}.onnx"

    def _download_voice(self, voice: str) -> None:
        try:
            from piper.download_voices import download_voice
        except ImportError as exc:
            raise TTSModelError(
                "Voice download is not available. Ensure 'piper-tts>=1.2.0' is installed."
            ) from exc

        download_dir = self.config.model_dir.expanduser()
        download_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Downloading TTS voice '%s' to %s", voice, download_dir)
        download_voice(voice, download_dir)
        logger.info("TTS voice '%s' downloaded successfully", voice)

    def _synthesize_wav(self, text: str) -> tuple[np.ndarray, int]:
        logger.debug("TTS synthesizing text length=%d chars", len(text))
        output = io.BytesIO()
        with wave.open(output, "wb") as wav_file:
            self._voice.synthesize(  # type: ignore[union-attr]
                text,
                wav_file,
                length_scale=1.0 / self.config.speed,
            )
        output.seek(0)
        with wave.open(output, "rb") as wav_file:
            sample_rate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            frames = wav_file.readframes(wav_file.getnframes())
        if sample_width != 2:
            logger.error("TTS unsupported sample width=%d", sample_width)
            raise ValueError(f"Unsupported Piper sample width: {sample_width}")
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        if channels > 1:
            audio = audio.reshape(-1, channels).mean(axis=1)
        logger.debug(
            "TTS synthesis complete: samples=%d sample_rate=%d channels=%d",
            len(audio), sample_rate, channels,
        )
        return audio, sample_rate

    def _report_error(self, error: Exception) -> None:
        logger.error("TTS error: %s", error, exc_info=True)
        if self._on_error:
            try:
                self._on_error(error)
            except Exception:
                logger.debug("TTS error callback failed", exc_info=True)
