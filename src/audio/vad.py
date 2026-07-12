"""
Nexus Voice Activity Detection (VAD).

Detects when a person is speaking using WebRTCVAD.
Wraps webrtcvad with a state machine (SILENCE → SPEECH → ENDING → SILENCE)
for clean utterance boundary detection.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

import numpy as np


class VadState(Enum):
    """Current state of the VAD state machine."""

    SILENCE = "silence"
    SPEECH = "speech"
    ENDING = "ending"


@dataclass
class VadConfig:
    """Configuration for VoiceActivityDetector."""

    aggressiveness: int = 3
    """VAD aggressiveness (0–3). 3 = most aggressive, fewer false positives."""

    sample_rate: int = 16000
    """Audio sample rate in Hz. Must be 8000, 16000, 32000, or 48000."""

    frame_ms: int = 30
    """Frame duration in milliseconds. Must be 10, 20, or 30."""

    silence_duration_ms: int = 600
    """Milliseconds of silence before SPEECH → SILENCE transition."""

    min_speech_duration_ms: int = 100
    """Minimum speech duration to avoid noise triggering false starts."""


class VoiceActivityDetector:
    """State-machine based voice activity detector.

    Usage:
        vad = VoiceActivityDetector()
        for chunk in audio_stream:
            state = vad.process_chunk(chunk)
            if state == VadState.SPEECH:
                print("Speaking...")
            elif state == VadState.SILENCE:
                print("Silence")
    """

    def __init__(
        self,
        config: VadConfig | None = None,
        on_speech_start: Callable[[], None] | None = None,
        on_speech_end: Callable[[], None] | None = None,
    ) -> None:
        self.config = config or VadConfig()
        self._on_speech_start = on_speech_start
        self._on_speech_end = on_speech_end

        # Validate config
        if self.config.sample_rate not in (8000, 16000, 32000, 48000):
            raise ValueError(f"sample_rate must be 8000/16000/32000/48000, got {self.config.sample_rate}")
        if self.config.frame_ms not in (10, 20, 30):
            raise ValueError(f"frame_ms must be 10/20/30, got {self.config.frame_ms}")

        import webrtcvad  # noqa: F401
        self._vad = webrtcvad.Vad(self.config.aggressiveness)

        # State machine
        self._state: VadState = VadState.SILENCE
        self._silence_frames = 0
        self._speech_frames = 0
        self._silence_limit = self.config.silence_duration_ms // self.config.frame_ms
        self._min_speech_frames = self.config.min_speech_duration_ms // self.config.frame_ms

        self._frame_size = self.config.sample_rate * self.config.frame_ms // 1000  # samples per frame
        self._pending_buffer: list[np.ndarray] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def state(self) -> VadState:
        """Current VAD state."""
        return self._state

    def process_chunk(self, chunk: np.ndarray) -> VadState:
        """Process an audio chunk and return the current VAD state.

        Args:
            chunk: Float32 numpy array of audio samples, mono.

        Returns:
            Current VadState after processing this chunk.
        """
        # Convert float32 [-1,1] to int16 required by webrtcvad
        if chunk.dtype == np.float32:
            int_chunk = (chunk * 32767).astype(np.int16)
        elif chunk.dtype == np.int16:
            int_chunk = chunk
        else:
            int_chunk = (chunk.astype(np.float32) * 32767).astype(np.int16)

        # Process in fixed-size frames
        is_speech = False
        for frame_bytes in self._frame_generator(int_chunk.tobytes()):
            try:
                if self._vad.is_speech(frame_bytes, self.config.sample_rate):
                    is_speech = True
            except Exception:
                continue

        return self._update_state(is_speech)

    def is_speech(self, frame: bytes) -> bool:
        """Check if a single 16-bit PCM frame contains speech.

        Lower-level check for manual frame loops.
        """
        return self._vad.is_speech(frame, self.config.sample_rate)

    def reset(self) -> None:
        """Reset the VAD state machine to SILENCE."""
        self._state = VadState.SILENCE
        self._silence_frames = 0
        self._speech_frames = 0
        self._pending_buffer.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _frame_generator(self, raw_bytes: bytes) -> list[bytes]:
        """Split raw PCM bytes into fixed-size frames."""
        frame_bytes = self._frame_size * 2  # 2 bytes per int16 sample
        frames = []
        for i in range(0, len(raw_bytes) - frame_bytes + 1, frame_bytes):
            frames.append(raw_bytes[i:i + frame_bytes])
        return frames

    def _update_state(self, is_speech: bool) -> VadState:
        """Update the state machine based on VAD result from the full chunk."""
        if is_speech:
            self._speech_frames += 1
            self._silence_frames = 0
        else:
            self._silence_frames += 1

        prev = self._state

        if self._state == VadState.SILENCE:
            if is_speech and self._speech_frames >= self._min_speech_frames:
                self._state = VadState.SPEECH
                if self._on_speech_start:
                    self._on_speech_start()

        elif self._state == VadState.SPEECH:
            if not is_speech:
                self._state = VadState.ENDING
                self._silence_frames = 0

        elif self._state == VadState.ENDING:
            if is_speech:
                # Revert to speech — user kept talking
                self._state = VadState.SPEECH
            elif self._silence_frames >= self._silence_limit:
                self._state = VadState.SILENCE
                self._speech_frames = 0
                if self._on_speech_end:
                    self._on_speech_end()

        if self._state != prev and self._state == VadState.SILENCE:
            self._speech_frames = 0

        return self._state
