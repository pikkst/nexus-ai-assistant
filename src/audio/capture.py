"""
Nexus Audio Capture Service.

Captures microphone audio in real-time using PyAudio.
Integrates with VoiceActivityDetector for speech/silence detection.
Runs in a background thread to avoid blocking the async event loop.
"""

from __future__ import annotations

import queue
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from .vad import VoiceActivityDetector, VadConfig, VadState


@dataclass
class AudioCaptureConfig:
    """Configuration for AudioCapture."""

    sample_rate: int = 16000
    """Audio sample rate in Hz."""

    chunk_size: int = 1024
    """Number of frames per audio chunk."""

    device_index: int | None = None
    """PyAudio device index. None = default input device."""

    channels: int = 1
    """Number of channels (1 = mono)."""

    dtype: str = "float32"
    """Numpy dtype for audio data."""

    silence_timeout: float = 30.0
    """Seconds of silence before auto-stop. 0 = no timeout."""


class AudioCapture:
    """Real-time microphone audio capture with VAD integration.

    Usage:
        capture = AudioCapture()
        capture.on_audio_chunk = lambda chunk: print(f"Got {len(chunk)} samples")
        capture.on_speech_start = lambda: print("Speech started")
        capture.on_speech_end = lambda: print("Speech ended")

        async with capture:
            await capture.start()
            # ... capture runs in background ...
            await asyncio.sleep(5)
            await capture.stop()
    """

    def __init__(
        self,
        config: AudioCaptureConfig | None = None,
        vad_config: VadConfig | None = None,
    ) -> None:
        self.config = config or AudioCaptureConfig()
        self._vad_config = vad_config or VadConfig()

        # Callbacks (set before start())
        self.on_audio_chunk: Callable[[np.ndarray], None] | None = None
        self.on_speech_start: Callable[[], None] | None = None
        self.on_speech_end: Callable[[], None] | None = None

        # Internal state
        self._stream: object | None = None  # PyAudio stream
        self._pyaudio: object | None = None  # PyAudio instance
        self._thread: threading.Thread | None = None
        self._running = threading.Event()
        self._chunk_queue: queue.Queue[np.ndarray | None] = queue.Queue(maxsize=100)
        self._speech_buffer: list[np.ndarray] = []
        self._vad: VoiceActivityDetector | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start audio capture in a background thread.

        Raises RuntimeError if no microphone is available.
        Logs a warning and returns silently — callers should check is_active.
        """
        if self._running.is_set():
            return

        import pyaudio

        self._pyaudio = pyaudio.PyAudio()

        # Find default input device
        try:
            device_info = self._pyaudio.get_default_input_device_info()
            device_index = device_info["index"]
        except (OSError, IOError):
            device_index = None

        if device_index is None:
            self._pyaudio.terminate()
            self._pyaudio = None
            import logging
            logging.getLogger(__name__).warning(
                "No microphone detected. Audio capture disabled."
            )
            return

        # Override with explicit device index if set
        if self.config.device_index is not None:
            device_index = self.config.device_index

        # Open audio stream
        try:
            self._stream = self._pyaudio.open(
                format=pyaudio.paFloat32 if self.config.dtype == "float32" else pyaudio.paInt16,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.config.chunk_size,
                stream_callback=self._stream_callback,
            )
            self._stream.start_stream()
        except Exception as e:
            self._pyaudio.terminate()
            self._pyaudio = None
            import logging
            logging.getLogger(__name__).error(
                f"Failed to open audio stream: {e}"
            )
            return

        # Initialize VAD with callbacks
        self._vad = VoiceActivityDetector(
            config=self._vad_config,
            on_speech_start=self._on_vad_speech_start,
            on_speech_end=self._on_vad_speech_end,
        )

        # Start processing thread
        self._running.set()
        self._thread = threading.Thread(
            target=self._process_loop,
            name="nexus-audio-capture",
            daemon=True,
        )
        self._thread.start()

    async def stop(self) -> None:
        """Stop audio capture and clean up resources."""
        self._running.clear()

        if self._thread and self._thread.is_alive():
            self._chunk_queue.put(None)  # Signal thread to stop
            self._thread.join(timeout=2.0)

        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        if self._pyaudio is not None:
            self._pyaudio.terminate()
            self._pyaudio = None

        self._vad = None

    @property
    def is_active(self) -> bool:
        """Whether audio capture is currently running."""
        return self._running.is_set() and self._stream is not None

    def get_speech_buffer(self) -> np.ndarray | None:
        """Return the accumulated speech buffer and clear it.

        Returns None if no speech was captured.
        """
        if not self._speech_buffer:
            return None
        result = np.concatenate(self._speech_buffer, axis=0)
        self._speech_buffer.clear()
        return result

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "AudioCapture":
        return self

    async def __aexit__(self, *args) -> None:
        await self.stop()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _stream_callback(
        self, in_data: bytes, frame_count: int, time_info: dict, status: int
    ) -> tuple[None, int]:
        """PyAudio callback — called from audio thread."""
        if self._running.is_set():
            # Convert bytes to numpy array
            chunk = np.frombuffer(in_data, dtype=np.float32).copy()
            if self.config.channels == 1:
                # Already mono
                pass
            elif self.config.channels > 1:
                # Mix down to mono
                chunk = chunk.reshape(-1, self.config.channels).mean(axis=1)

            try:
                self._chunk_queue.put(chunk, timeout=0.1)
            except queue.Full:
                pass  # Drop chunk if queue is full
        return (None, 0)

    def _process_loop(self) -> None:
        """Background thread: processes audio chunks."""
        import logging

        logger = logging.getLogger(__name__)
        silence_start = time.monotonic()
        vad = self._vad

        while self._running.is_set():
            try:
                chunk = self._chunk_queue.get(timeout=0.5)
            except queue.Empty:
                # Check silence timeout
                if (
                    self.config.silence_timeout > 0
                    and (time.monotonic() - silence_start) > self.config.silence_timeout
                ):
                    logger.info("Silence timeout reached, stopping capture.")
                    self._running.clear()
                    break
                continue

            if chunk is None:
                break

            silence_start = time.monotonic()

            # Fire audio chunk callback
            if self.on_audio_chunk:
                try:
                    self.on_audio_chunk(chunk)
                except Exception:
                    pass

            # VAD processing
            if vad is not None:
                state = vad.process_chunk(chunk)
                if state == VadState.SPEECH or state == VadState.ENDING:
                    self._speech_buffer.append(chunk)

    def _on_vad_speech_start(self) -> None:
        """Called when VAD transitions from silence to speech."""
        if self.on_speech_start:
            try:
                self.on_speech_start()
            except Exception:
                pass

    def _on_vad_speech_end(self) -> None:
        """Called when VAD transitions from speech to silence."""
        if self.on_speech_end:
            try:
                self.on_speech_end()
            except Exception:
                pass
