"""Tests for the audio capture and VAD modules."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.audio.vad import VadConfig, VadState, VoiceActivityDetector


# ------------------------------------------------------------------
# VAD Tests
# ------------------------------------------------------------------

class TestVadConfig:
    def test_default_config(self) -> None:
        config = VadConfig()
        assert config.sample_rate == 16000
        assert config.aggressiveness == 3
        assert config.frame_ms == 30
        assert config.silence_duration_ms == 600

    def test_invalid_sample_rate(self) -> None:
        with pytest.raises(ValueError, match="sample_rate"):
            VoiceActivityDetector(VadConfig(sample_rate=12345))

    def test_invalid_frame_ms(self) -> None:
        with pytest.raises(ValueError, match="frame_ms"):
            VoiceActivityDetector(VadConfig(frame_ms=7))


class TestVoiceActivityDetector:
    def test_initial_state(self) -> None:
        vad = VoiceActivityDetector(VadConfig(aggressiveness=0, silence_duration_ms=200))
        assert vad.state == VadState.SILENCE

    def test_silence_chunk_returns_silence(self) -> None:
        vad = VoiceActivityDetector(VadConfig(aggressiveness=0, silence_duration_ms=200))
        silence = np.zeros(16000 // 1000 * 30, dtype=np.float32)  # 30ms of silence
        state = vad.process_chunk(silence)
        assert state == VadState.SILENCE

    def test_state_machine_flow(self) -> None:
        """Simulate: silence → speech → silence transition."""
        vad = VoiceActivityDetector(
            VadConfig(aggressiveness=0, silence_duration_ms=200, min_speech_duration_ms=30)
        )

        # Initial: silence
        silence = np.zeros(480, dtype=np.float32)
        assert vad.process_chunk(silence) == VadState.SILENCE

        # We can't easily fake webrtcvad output, but we can test the framework
        # Mock the underlying VAD to return True, then False
        with patch.object(vad._vad, "is_speech", return_value=True):
            speech_chunk = np.ones(480, dtype=np.float32) * 0.5
            # Need multiple chunks to cross min_speech_frames
            for _ in range(4):
                state = vad.process_chunk(speech_chunk)
            assert state == VadState.SPEECH

        # Now stop speech — should go to ENDING then SILENCE
        with patch.object(vad._vad, "is_speech", return_value=False):
            # Should be ENDING after first silence chunk
            state = vad.process_chunk(silence)
            assert state == VadState.ENDING

            # After enough silence frames, should be SILENCE
            for _ in range(10):
                state = vad.process_chunk(silence)
            assert state == VadState.SILENCE

    def test_speech_start_callback(self) -> None:
        calls = []
        vad = VoiceActivityDetector(
            VadConfig(aggressiveness=0, min_speech_duration_ms=30),
            on_speech_start=lambda: calls.append("start"),
        )

        with patch.object(vad._vad, "is_speech", return_value=True):
            for _ in range(4):
                vad.process_chunk(np.ones(480, dtype=np.float32))
        assert calls == ["start"]

    def test_speech_end_callback(self) -> None:
        calls = []
        vad = VoiceActivityDetector(
            VadConfig(aggressiveness=0, silence_duration_ms=200, min_speech_duration_ms=30),
            on_speech_end=lambda: calls.append("end"),
        )

        # Start speech
        with patch.object(vad._vad, "is_speech", return_value=True):
            for _ in range(4):
                vad.process_chunk(np.ones(480, dtype=np.float32))

        # End speech
        with patch.object(vad._vad, "is_speech", return_value=False):
            silence = np.zeros(480, dtype=np.float32)
            for _ in range(10):
                vad.process_chunk(silence)
        assert calls == ["end"]

    def test_reset(self) -> None:
        vad = VoiceActivityDetector()
        vad.reset()
        assert vad.state == VadState.SILENCE

    def test_process_chunk_float32_input(self) -> None:
        vad = VoiceActivityDetector(VadConfig(aggressiveness=0, silence_duration_ms=100))
        chunk = np.zeros(480, dtype=np.float32)
        # Should not raise
        state = vad.process_chunk(chunk)
        assert state in (VadState.SILENCE,)

    def test_process_chunk_int16_input(self) -> None:
        vad = VoiceActivityDetector(VadConfig(aggressiveness=0, silence_duration_ms=100))
        chunk = np.zeros(480, dtype=np.int16)
        state = vad.process_chunk(chunk)
        assert state in (VadState.SILENCE,)


# ------------------------------------------------------------------
# AudioCapture Tests
# ------------------------------------------------------------------

class TestAudioCapture:
    """Tests for AudioCapture with mocked PyAudio."""

    @pytest.mark.asyncio
    async def test_importable(self) -> None:
        from src.audio.capture import AudioCapture, AudioCaptureConfig
        config = AudioCaptureConfig()
        capture = AudioCapture(config)
        assert not capture.is_active
        # No need to start — just verifying import and instantiation

    @pytest.mark.asyncio
    async def test_start_without_mic(self) -> None:
        """Should log warning and return silently if no mic."""
        from src.audio.capture import AudioCapture

        capture = AudioCapture()
        with patch("pyaudio.PyAudio") as mock_pa:
            instance = mock_pa.return_value
            instance.get_default_input_device_info.side_effect = OSError("No mic")
            await capture.start()
            assert not capture.is_active

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Async context manager should enter and exit cleanly."""
        from src.audio.capture import AudioCapture

        async with AudioCapture() as capture:
            assert capture is not None

    @pytest.mark.asyncio
    async def test_get_speech_buffer_empty(self) -> None:
        from src.audio.capture import AudioCapture

        capture = AudioCapture()
        assert capture.get_speech_buffer() is None

    def test_config_defaults(self) -> None:
        from src.audio.capture import AudioCaptureConfig

        config = AudioCaptureConfig()
        assert config.sample_rate == 16000
        assert config.chunk_size == 1024
        assert config.channels == 1
        assert config.dtype == "float32"

    def test_config_custom(self) -> None:
        from src.audio.capture import AudioCaptureConfig

        config = AudioCaptureConfig(
            sample_rate=48000,
            chunk_size=2048,
            device_index=1,
        )
        assert config.sample_rate == 48000
        assert config.chunk_size == 2048
        assert config.device_index == 1
