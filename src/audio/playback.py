"""
Nexus Audio Playback Service.

Plays audio through speakers for TTS output.
Non-blocking with internal queue and background thread.
"""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf

try:
    import pyaudio
except ImportError:
    pyaudio = None


@dataclass
class AudioPlaybackConfig:
    """Configuration for AudioPlayback."""

    sample_rate: int = 24000
    """Default output sample rate in Hz."""

    chunk_size: int = 1024
    """Number of frames per playback chunk."""

    device_index: int | None = None
    """PyAudio device index. None = default output device."""

    channels: int = 1
    """Number of channels (1 = mono)."""

    dtype: str = "float32"
    """Numpy dtype for audio data."""

    max_queue_size: int = 100
    """Maximum number of queued audio chunks."""


class AudioPlayback:
    """Non-blocking audio playback service.

    Usage:
        playback = AudioPlayback()
        await playback.start()
        await playback.play(audio_np_array, sample_rate=24000)
        await playback.play_file(Path("output.wav"))
        await playback.stop()
    """

    def __init__(
        self,
        config: AudioPlaybackConfig | None = None,
    ) -> None:
        self.config = config or AudioPlaybackConfig()
        self._volume: float = 1.0
        self._stream: object | None = None
        self._pyaudio: object | None = None
        self._thread: threading.Thread | None = None
        self._running = threading.Event()
        self._queue: queue.Queue[bytes | None] = queue.Queue(maxsize=self.config.max_queue_size)

    async def start(self) -> None:
        """Initialize audio output device.

        Logs a warning and returns silently if no speakers are available.
        """
        if self._running.is_set():
            return

        if pyaudio is None:
            import logging
            logging.getLogger(__name__).warning(
                "PyAudio not installed. Audio playback disabled."
            )
            return

        self._pyaudio = pyaudio.PyAudio()

        try:
            device_info = self._pyaudio.get_default_output_device_info()
            device_index = device_info["index"]
        except (OSError, IOError):
            self._pyaudio.terminate()
            self._pyaudio = None
            import logging
            logging.getLogger(__name__).warning(
                "No speakers detected. Audio playback disabled."
            )
            return

        if self.config.device_index is not None:
            device_index = self.config.device_index

        try:
            self._stream = self._pyaudio.open(
                format=pyaudio.paFloat32 if self.config.dtype == "float32" else pyaudio.paInt16,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                output=True,
                output_device_index=device_index,
                frames_per_buffer=self.config.chunk_size,
            )
        except Exception as e:
            self._pyaudio.terminate()
            self._pyaudio = None
            import logging
            logging.getLogger(__name__).error(
                f"Failed to open audio output stream: {e}"
            )
            return

        self._running.set()
        self._thread = threading.Thread(
            target=self._playback_loop,
            name="nexus-audio-playback",
            daemon=True,
        )
        self._thread.start()

    async def stop(self) -> None:
        """Stop playback and clean up resources."""
        self._running.clear()
        self._queue.put(None)

        if self._thread and self._thread.is_alive():
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

        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    async def play(self, audio: np.ndarray, sample_rate: int | None = None) -> None:
        """Queue audio data for playback.

        Args:
            audio: Audio samples as numpy array (float32 or int16).
            sample_rate: Sample rate of the input audio.
        """
        if not self._running.is_set() or self._stream is None:
            import logging
            logging.getLogger(__name__).warning(
                "AudioPlayback not started. Call start() first."
            )
            return

        rate = sample_rate or self.config.sample_rate
        audio = self._apply_volume(audio)

        if rate != self.config.sample_rate:
            audio = self._resample(audio, rate, self.config.sample_rate)

        if self.config.dtype == "float32":
            data = audio.astype(np.float32).tobytes()
        else:
            data = audio.astype(np.int16).tobytes()

        try:
            self._queue.put(data, timeout=1.0)
        except queue.Full:
            import logging
            logging.getLogger(__name__).warning(
                "Playback queue full, dropping audio chunk."
            )

    async def play_file(self, path: Path) -> None:
        """Play an audio file (WAV, MP3, or raw PCM).

        Args:
            path: Path to the audio file.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")

        suffix = path.suffix.lower()

        if suffix == ".wav":
            audio, sample_rate = sf.read(str(path), dtype=np.float32)
            if audio.ndim > 1:
                audio = audio.mean(axis=1)
        elif suffix == ".mp3":
            try:
                audio, sample_rate = sf.read(str(path), dtype=np.float32)
                if audio.ndim > 1:
                    audio = audio.mean(axis=1)
            except Exception:
                try:
                    from pydub import AudioSegment
                    segment = AudioSegment.from_mp3(str(path))
                    audio = np.array(segment.get_array_of_samples(), dtype=np.float32)
                    sample_rate = segment.frame_rate
                    if segment.channels > 1:
                        audio = audio.reshape(-1, segment.channels).mean(axis=1)
                except ImportError:
                    raise RuntimeError(
                        "MP3 playback requires pydub. Install with: pip install pydub"
                    )
        elif suffix in (".pcm", ".raw"):
            audio = np.fromfile(path, dtype=np.float32)
            sample_rate = self.config.sample_rate
        else:
            raise ValueError(f"Unsupported audio format: {suffix}")

        await self.play(audio, sample_rate=sample_rate)

    async def set_volume(self, volume: float) -> None:
        """Set playback volume.

        Args:
            volume: Volume level from 0.0 (silent) to 1.0 (full).
        """
        if not 0.0 <= volume <= 1.0:
            raise ValueError(f"Volume must be between 0.0 and 1.0, got {volume}")
        self._volume = volume

    @property
    def is_active(self) -> bool:
        """Whether audio playback is currently running."""
        return self._running.is_set() and self._stream is not None

    async def __aenter__(self) -> "AudioPlayback":
        await self.start()
        return self

    async def __aexit__(self, *args) -> None:
        await self.stop()

    def _apply_volume(self, audio: np.ndarray) -> np.ndarray:
        """Apply volume gain to audio data."""
        if self._volume == 1.0:
            return audio
        return np.clip(audio * self._volume, -1.0, 1.0).astype(audio.dtype)

    def _resample(self, audio: np.ndarray, from_rate: int, to_rate: int) -> np.ndarray:
        """Simple linear interpolation resampling."""
        if from_rate == to_rate:
            return audio
        ratio = to_rate / from_rate
        new_length = int(len(audio) * ratio)
        indices = np.linspace(0, len(audio) - 1, new_length)
        return np.interp(indices, np.arange(len(audio)), audio).astype(audio.dtype)

    def _playback_loop(self) -> None:
        """Background thread: plays queued audio chunks."""
        import logging
        logger = logging.getLogger(__name__)

        while self._running.is_set():
            try:
                data = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if data is None:
                break

            if self._stream is not None:
                try:
                    self._stream.write(data)
                except Exception as e:
                    logger.error(f"Error writing to audio stream: {e}")
