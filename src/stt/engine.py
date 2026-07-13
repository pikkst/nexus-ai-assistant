"""
Nexus Speech-to-Text Engine.

Converts microphone audio into text transcripts using faster-whisper.
Provides synchronous and streaming transcription with partial/final callbacks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Sequence

import numpy as np


logger = logging.getLogger(__name__)


class STTState(Enum):
    """Operational state of the STT engine."""

    UNLOADED = "unloaded"
    LOADING = "loading"
    READY = "ready"
    TRANSCRIBING = "transcribing"
    ERROR = "error"


@dataclass
class STTConfig:
    """Configuration for STTEngine."""

    model_size: str = "base"
    """Whisper model size: tiny, base, small, medium, large."""

    device: str = "auto"
    """Device to run on: cpu, cuda, auto."""

    compute_type: str = "int8"
    """Compute precision: int8, float16, float32."""

    language: str = "auto"
    """Language code: et, en, or auto for detection."""

    beam_size: int = 5
    """Beam search width. Higher = more accurate, slower."""

    vad_filter: bool = True
    """Enable internal VAD to skip non-speech segments."""


@dataclass
class Segment:
    """A single transcribed text segment."""

    start: float
    """Start time in seconds."""

    end: float
    """End time in seconds."""

    text: str
    """Transcribed text for this segment."""

    speech_probability: float = 0.0
    """Speech-presence proxy (1.0 - no_speech_prob) for this segment."""


@dataclass
class TranscriptionResult:
    """Full transcription output."""

    text: str
    """Complete transcribed text."""

    language: str
    """Detected or configured language code."""

    confidence: float
    """Overall speech-presence proxy (average of per-segment 1.0 - no_speech_prob)."""

    segments: list[Segment] = field(default_factory=list)
    """Per-segment breakdown with timing."""

    duration: float = 0.0
    """Audio duration in seconds."""


class STTEngine:
    """Local speech-to-text engine backed by faster-whisper.

    Usage:
        engine = STTEngine()
        await engine.load_model()
        result = await engine.transcribe(audio_np_array)
        print(result.text)
        await engine.unload_model()

    Streaming:
        engine = STTEngine()
        await engine.load_model()
        await engine.transcribe_stream(audio_np_array)
        await engine.unload_model()
    """

    def __init__(
        self,
        config: STTConfig | None = None,
        on_partial_transcript: Callable[[str], None] | None = None,
        on_final_transcript: Callable[[TranscriptionResult], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        self.config = config or STTConfig()
        self._on_partial = on_partial_transcript
        self._on_final = on_final_transcript
        self._on_error = on_error

        self._state = STTState.UNLOADED
        self._model: object | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def state(self) -> STTState:
        """Current operational state of the engine."""
        return self._state

    @property
    def is_ready(self) -> bool:
        """Whether a model is loaded and ready for transcription."""
        return self._state == STTState.READY

    async def load_model(self) -> None:
        """Load the Whisper model into memory.

        Downloads the model on first use (cached by faster-whisper).
        Sets state to READY on success, ERROR on failure.
        """
        if self._state in (STTState.LOADING, STTState.READY, STTState.TRANSCRIBING):
            logger.debug("STT load_model skipped; state=%s", self._state.value)
            return

        self._state = STTState.LOADING
        logger.info(
            "STT loading model_size=%s device=%s compute_type=%s language=%s",
            self.config.model_size,
            self.config.device,
            self.config.compute_type,
            self.config.language,
        )

        try:
            from faster_whisper import WhisperModel  # noqa: F401
            logger.debug("faster-whisper imported successfully")
        except ImportError as exc:
            self._state = STTState.ERROR
            err = RuntimeError(
                "faster-whisper is not installed. "
                "Install it with: pip install faster-whisper"
            )
            err.__cause__ = exc
            logger.error("STT faster-whisper import failed: %s", exc)
            if self._on_error:
                try:
                    self._on_error(err)
                except Exception:
                    pass
            raise err

        try:
            device = self._resolve_device()
            compute_type = self._resolve_compute_type(device)

            logger.info(
                "STT loading model: %s on %s (%s)",
                self.config.model_size,
                device,
                compute_type,
            )

            model = WhisperModel(
                self.config.model_size,
                device=device,
                compute_type=compute_type,
            )

            self._model = model
            self._state = STTState.READY
            logger.info("STT model loaded successfully: model_size=%s device=%s", self.config.model_size, device)

        except Exception as exc:
            self._state = STTState.ERROR
            self._model = None
            logger.error("STT failed to load model: %s", exc, exc_info=True)
            if self._on_error:
                try:
                    self._on_error(exc)
                except Exception:
                    pass
            raise RuntimeError(f"Failed to load STT model: {exc}") from exc

    async def unload_model(self) -> None:
        """Free the loaded model from memory."""
        self._model = None
        self._state = STTState.UNLOADED
        logger.info("STT model unloaded.")

    async def transcribe(
        self,
        audio: np.ndarray,
        *,
        fire_partial: bool = True,
        on_partial: Callable[[str], None] | None = None,
        on_final: Callable[[TranscriptionResult], None] | None = None,
    ) -> TranscriptionResult:
        """Transcribe a complete audio array into text.

        Args:
            audio: Float32 numpy array, mono, sample rate 16000 Hz.
            fire_partial: If True, fire the per-segment partial callback.
            on_partial: Override instance-level partial callback for this call.
            on_final: Override instance-level final callback for this call.

        Returns:
            TranscriptionResult with full text, language, confidence, segments.
        """
        self._validate_audio(audio)

        if self._state != STTState.READY:
            raise RuntimeError(
                f"STT engine is not ready (state={self._state.value}). "
                "Call load_model() first."
            )

        self._state = STTState.TRANSCRIBING
        logger.debug("STT transcribing audio: samples=%d dtype=%s", len(audio), audio.dtype)

        partial_callback = on_partial if on_partial is not None else self._on_partial
        final_callback = on_final if on_final is not None else self._on_final

        try:
            segments, info = self._model.transcribe(  # type: ignore[union-attr]
                audio,
                beam_size=self.config.beam_size,
                language=self._resolve_language(),
                vad_filter=self.config.vad_filter,
            )
            logger.debug("STT transcription started: beam_size=%s vad_filter=%s", self.config.beam_size, self.config.vad_filter)

            segment_list: list[Segment] = []
            partial_text_parts: list[str] = []

            for seg in segments:
                segment = Segment(
                    start=seg.start or 0.0,
                    end=seg.end or 0.0,
                    text=seg.text.strip(),
                    speech_probability=1.0 - (seg.no_speech_prob if seg.no_speech_prob is not None else 0.0),
                )
                segment_list.append(segment)
                partial_text_parts.append(segment.text)

                if fire_partial and partial_callback:
                    try:
                        partial_callback(segment.text)
                    except Exception:
                        pass

            full_text = " ".join(partial_text_parts).strip()
            avg_speech_probability = (
                sum(s.speech_probability for s in segment_list) / len(segment_list)
                if segment_list
                else 0.0
            )

            detected_language = info.language or self.config.language or "auto"

            result = TranscriptionResult(
                text=full_text,
                language=detected_language,
                confidence=avg_speech_probability,
                segments=segment_list,
                duration=info.duration or 0.0,
            )

            logger.info(
                "STT transcription complete: language=%s confidence=%.2f duration=%.2fs segments=%d text=%r",
                detected_language,
                avg_speech_probability,
                info.duration or 0.0,
                len(segment_list),
                full_text[:200],
            )

            if final_callback:
                try:
                    final_callback(result)
                except Exception:
                    pass

            self._state = STTState.READY
            return result

        except Exception as exc:
            self._state = STTState.ERROR
            logger.error("STT transcription failed: %s", exc, exc_info=True)
            if self._on_error:
                try:
                    self._on_error(exc)
                except Exception:
                    pass
            raise RuntimeError(f"Transcription failed: {exc}") from exc

    async def transcribe_stream(
        self,
        audio: np.ndarray,
        on_partial: Callable[[str], None] | None = None,
        on_final: Callable[[TranscriptionResult], None] | None = None,
    ) -> TranscriptionResult:
        """Transcribe audio with per-call callback overrides.

        Unlike the older state-mutating wrapper, this delegates to
        `transcribe()` without touching instance callbacks, so it is
        safe to call concurrently.

        Args:
            audio: Float32 numpy array, mono, sample rate 16000 Hz.
            on_partial: Partial callback for this call only.
            on_final: Final callback for this call only.

        Returns:
            TranscriptionResult with full transcript.
        """
        return await self.transcribe(
            audio,
            fire_partial=True,
            on_partial=on_partial,
            on_final=on_final,
        )

    # ------------------------------------------------------------------
    # Audio Preprocessing Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def normalize_audio(audio: np.ndarray, target_rms: float = 0.1) -> np.ndarray:
        """Normalize audio to a target RMS level.

        Args:
            audio: Float32 numpy array.
            target_rms: Desired root-mean-square amplitude.

        Returns:
            Normalized float32 audio array.
        """
        if audio.size == 0:
            return audio.astype(np.float32)

        rms = np.sqrt(np.mean(audio ** 2))
        if rms < 1e-8:
            return audio.astype(np.float32)

        gain = target_rms / rms
        normalized = audio * gain

        # Clip to valid range
        normalized = np.clip(normalized, -1.0, 1.0)

        return normalized.astype(np.float32)

    @staticmethod
    def trim_silence(
        audio: np.ndarray,
        sample_rate: int = 16000,
        threshold: float = 0.01,
        frame_ms: int = 30,
    ) -> np.ndarray:
        """Trim leading and trailing silence from audio.

        Args:
            audio: Float32 numpy array.
            sample_rate: Audio sample rate in Hz.
            threshold: Amplitude threshold below which is considered silence.
            frame_ms: Frame size for silence detection in milliseconds.

        Returns:
            Trimmed float32 audio array.
        """
        if audio.size == 0:
            return audio.astype(np.float32)

        frame_samples = int(sample_rate * frame_ms / 1000)
        if frame_samples <= 0:
            return audio.astype(np.float32)

        abs_audio = np.abs(audio)

        def find_start() -> int:
            for i in range(0, len(audio) - frame_samples + 1, frame_samples):
                if np.mean(abs_audio[i : i + frame_samples]) > threshold:
                    return i
            return len(audio)

        def find_end(start: int) -> int:
            for i in range(len(audio) - frame_samples, start - 1, -frame_samples):
                if np.mean(abs_audio[i : i + frame_samples]) > threshold:
                    return min(i + frame_samples, len(audio))
            return start

        start = find_start()
        end = find_end(start)

        return audio[start:end].astype(np.float32)

    @staticmethod
    def resample_to_16khz(audio: np.ndarray, original_sample_rate: int) -> np.ndarray:
        """Resample audio to 16000 Hz if needed.

        Uses simple linear interpolation. For production, consider
        librosa or scipy for higher quality resampling.

        Args:
            audio: Float32 numpy array.
            original_sample_rate: Current sample rate of the audio.

        Returns:
            Float32 numpy array at 16000 Hz.
        """
        if original_sample_rate == 16000 or audio.size == 0:
            return audio.astype(np.float32)

        duration = len(audio) / original_sample_rate
        target_samples = int(duration * 16000)

        if target_samples == 0:
            return np.array([], dtype=np.float32)

        x_old = np.linspace(0, len(audio) - 1, len(audio))
        x_new = np.linspace(0, len(audio) - 1, target_samples)
        resampled = np.interp(x_new, x_old, audio.astype(np.float32))

        return resampled.astype(np.float32)

    @staticmethod
    def preprocess(
        audio: np.ndarray,
        sample_rate: int = 16000,
        normalize: bool = True,
        trim_silence_flag: bool = True,
    ) -> np.ndarray:
        """Preprocess audio for optimal STT quality.

        Steps:
        1. Resample to 16000 Hz if needed.
        2. Convert to float32 mono.
        3. Optionally normalize.
        4. Optionally trim silence.

        Args:
            audio: Raw audio array (any dtype, any sample rate).
            sample_rate: Current sample rate.
            normalize: Whether to normalize RMS.
            trim_silence_flag: Whether to trim leading/trailing silence.

        Returns:
            Preprocessed float32 mono audio at 16000 Hz.
        """
        # Ensure float32
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # Mix to mono if multi-channel
        if audio.ndim > 1:
            audio = np.mean(audio, axis=-1)

        # Resample to 16000 Hz
        audio = STTEngine.resample_to_16khz(audio, sample_rate)

        # Trim silence
        if trim_silence_flag:
            audio = STTEngine.trim_silence(audio, sample_rate=16000)

        # Normalize
        if normalize:
            audio = STTEngine.normalize_audio(audio)

        return audio

    # ------------------------------------------------------------------
    # Context Manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "STTEngine":
        await self.load_model()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.unload_model()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _validate_audio(self, audio: np.ndarray) -> None:
        """Validate audio array shape, dtype, and contents before transcription."""
        if not isinstance(audio, np.ndarray):
            raise TypeError(f"audio must be a numpy array, got {type(audio).__name__}")
        if audio.ndim != 1:
            raise ValueError(
                f"audio must be a 1-D mono array, got {audio.ndim}-D. "
                "Use STTEngine.preprocess() to convert multi-channel audio."
            )
        if audio.dtype != np.float32:
            raise TypeError(
                f"audio dtype must be float32, got {audio.dtype}. "
                "Use STTEngine.preprocess() to convert."
            )
        if audio.size == 0:
            raise ValueError("audio array is empty. Provide non-empty audio for transcription.")
        if not np.all(np.isfinite(audio)):
            raise ValueError(
                "audio array contains NaN or Inf values. "
                "Check the audio source or use STTEngine.preprocess() to clean it."
            )

    def _resolve_device(self) -> str:
        """Resolve the effective device string."""
        if self.config.device == "auto":
            try:
                import torch  # noqa: F401
                if torch.cuda.is_available():
                    return "cuda"
            except ImportError:
                pass
            return "cpu"
        return self.config.device

    def _resolve_compute_type(self, device: str) -> str:
        """Resolve compute type based on device and config.

        Validates the configured compute_type against what the target
        device supports. Falls back to a safe default on mismatch.
        """
        allowed_cpu = {"int8", "float32", "int16"}
        allowed_cuda = {"float16", "int8", "float32", "int8_float16", "int16"}

        if device == "cuda":
            if self.config.compute_type in allowed_cuda:
                return self.config.compute_type
            logger.warning(
                "compute_type=%r is not supported on CUDA, falling back to float16",
                self.config.compute_type,
            )
            return "float16"

        if self.config.compute_type in allowed_cpu:
            return self.config.compute_type
        logger.warning(
            "compute_type=%r is not supported on CPU, falling back to int8",
            self.config.compute_type,
        )
        return "int8"

    def _resolve_language(self) -> str | None:
        """Resolve language: 'auto' -> None for Whisper auto-detect."""
        lang = self.config.language.lower()
        if lang == "auto":
            return None
        return lang
