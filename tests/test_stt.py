"""Tests for the STT engine module."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.stt.engine import (
    STTConfig,
    STTEngine,
    STTState,
    Segment,
    TranscriptionResult,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture()
def default_config() -> STTConfig:
    return STTConfig()

@pytest.fixture()
def sample_audio_16khz() -> np.ndarray:
    rng = np.random.default_rng(42)
    return (rng.standard_normal(16000 * 2) * 0.1).astype(np.float32)

@pytest.fixture()
def sample_audio_44khz() -> np.ndarray:
    rng = np.random.default_rng(42)
    return (rng.standard_normal(44100 * 2) * 0.1).astype(np.float32)

@pytest.fixture()
def silent_audio_16khz() -> np.ndarray:
    return np.zeros(16000 * 2, dtype=np.float32)


# ------------------------------------------------------------------
# STTConfig Tests
# ------------------------------------------------------------------

class TestSTTConfig:
    def test_defaults(self) -> None:
        config = STTConfig()
        assert config.model_size == "base"
        assert config.device == "auto"
        assert config.compute_type == "int8"
        assert config.language == "auto"
        assert config.beam_size == 5
        assert config.vad_filter is True

    def test_custom_values(self) -> None:
        config = STTConfig(
            model_size="small",
            device="cpu",
            compute_type="float32",
            language="et",
            beam_size=10,
            vad_filter=False,
        )
        assert config.model_size == "small"
        assert config.device == "cpu"
        assert config.compute_type == "float32"
        assert config.language == "et"
        assert config.beam_size == 10
        assert config.vad_filter is False


# ------------------------------------------------------------------
# STTState Tests
# ------------------------------------------------------------------

class TestSTTState:
    def test_state_values(self) -> None:
        assert STTState.UNLOADED.value == "unloaded"
        assert STTState.LOADING.value == "loading"
        assert STTState.READY.value == "ready"
        assert STTState.TRANSCRIBING.value == "transcribing"
        assert STTState.ERROR.value == "error"


# ------------------------------------------------------------------
# TranscriptionResult & Segment Tests
# ------------------------------------------------------------------

class TestTranscriptionResult:
    def test_defaults(self) -> None:
        result = TranscriptionResult(text="hello", language="en", confidence=0.95)
        assert result.text == "hello"
        assert result.language == "en"
        assert result.confidence == 0.95
        assert result.segments == []
        assert result.duration == 0.0

    def test_with_segments(self) -> None:
        segments = [
            Segment(start=0.0, end=1.5, text="Hello", speech_probability=0.95),
            Segment(start=1.5, end=3.0, text="world", speech_probability=0.90),
        ]
        result = TranscriptionResult(
            text="Hello world",
            language="en",
            confidence=0.925,
            segments=segments,
            duration=3.0,
        )
        assert len(result.segments) == 2
        assert result.segments[0].start == 0.0
        assert result.segments[1].speech_probability == 0.90
        assert result.duration == 3.0


class TestSegment:
    def test_segment_creation(self) -> None:
        seg = Segment(start=0.0, end=2.0, text="test", speech_probability=0.88)
        assert seg.start == 0.0
        assert seg.end == 2.0
        assert seg.text == "test"
        assert seg.speech_probability == 0.88


# ------------------------------------------------------------------
# STTEngine Tests
# ------------------------------------------------------------------

class TestSTTEngineInit:
    def test_default_state(self) -> None:
        engine = STTEngine()
        assert engine.state == STTState.UNLOADED
        assert not engine.is_ready

    def test_custom_callbacks(self) -> None:
        partial_calls: list[str] = []
        final_results: list[TranscriptionResult] = []
        error_calls: list[Exception] = []

        engine = STTEngine(
            on_partial_transcript=lambda t: partial_calls.append(t),
            on_final_transcript=lambda r: final_results.append(r),
            on_error=lambda e: error_calls.append(e),
        )
        assert engine._on_partial is not None
        assert engine._on_final is not None
        assert engine._on_error is not None

    def test_config_passed(self) -> None:
        config = STTConfig(model_size="small", language="en")
        engine = STTEngine(config=config)
        assert engine.config.model_size == "small"
        assert engine.config.language == "en"


class TestSTTEngineLoadUnload:
    @pytest.mark.asyncio
    async def test_load_model_success(self) -> None:
        engine = STTEngine()
        mock_model = MagicMock()

        with patch.dict(sys.modules, {"faster_whisper": MagicMock()}):
            with patch(
                "src.stt.engine.STTEngine._resolve_device", return_value="cpu"
            ), patch(
                "src.stt.engine.STTEngine._resolve_compute_type", return_value="int8"
            ), patch(
                "faster_whisper.WhisperModel", return_value=mock_model
            ) as mock_wm:
                mock_wm.return_value = mock_model
                await engine.load_model()
                assert engine.state == STTState.READY
                assert engine.is_ready

    @pytest.mark.asyncio
    async def test_load_model_missing_faster_whisper(self) -> None:
        engine = STTEngine()

        mock_fw = MagicMock()
        mock_fw.WhisperModel = MagicMock(side_effect=ImportError)
        with patch.dict(sys.modules, {"faster_whisper": mock_fw}):
            with pytest.raises(RuntimeError, match="Failed to load STT model"):
                await engine.load_model()
        assert engine.state == STTState.ERROR

    @pytest.mark.asyncio
    async def test_unload_model(self) -> None:
        engine = STTEngine()
        mock_model = MagicMock()

        with patch.dict(sys.modules, {"faster_whisper": MagicMock()}):
            with patch(
                "src.stt.engine.STTEngine._resolve_device", return_value="cpu"
            ), patch(
                "src.stt.engine.STTEngine._resolve_compute_type", return_value="int8"
            ), patch(
                "faster_whisper.WhisperModel", return_value=mock_model
            ) as mock_wm:
                mock_wm.return_value = mock_model
                await engine.load_model()
                assert engine.is_ready

        await engine.unload_model()
        assert engine.state == STTState.UNLOADED
        assert not engine.is_ready

    @pytest.mark.asyncio
    async def test_load_model_failure_calls_error_callback(self) -> None:
        errors: list[Exception] = []
        engine = STTEngine(on_error=lambda e: errors.append(e))

        with patch.dict(sys.modules, {"faster_whisper": MagicMock()}):
            with patch(
                "src.stt.engine.STTEngine._resolve_device", return_value="cpu"
            ), patch(
                "src.stt.engine.STTEngine._resolve_compute_type", return_value="int8"
            ), patch(
                "faster_whisper.WhisperModel", side_effect=RuntimeError("OOM")
            ):
                with pytest.raises(RuntimeError, match="OOM"):
                    await engine.load_model()
        assert len(errors) == 1
        assert engine.state == STTState.ERROR


class TestSTTEngineTranscribe:
    @pytest.mark.asyncio
    async def test_transcribe_not_ready_raises(self) -> None:
        engine = STTEngine()
        audio = np.ones(16000, dtype=np.float32) * 0.1
        with pytest.raises(RuntimeError, match="not ready"):
            await engine.transcribe(audio)

    @pytest.mark.asyncio
    async def test_transcribe_success(self, sample_audio_16khz: np.ndarray) -> None:
        engine = STTEngine()
        mock_model = MagicMock()

        mock_seg = MagicMock()
        mock_seg.start = 0.0
        mock_seg.end = 2.0
        mock_seg.text = "Hello world"
        mock_seg.no_speech_prob = 0.05

        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.duration = 2.0

        with patch.dict(sys.modules, {"faster_whisper": MagicMock()}):
            with patch(
                "src.stt.engine.STTEngine._resolve_device", return_value="cpu"
            ), patch(
                "src.stt.engine.STTEngine._resolve_compute_type", return_value="int8"
            ), patch(
                "faster_whisper.WhisperModel", return_value=mock_model
            ) as mock_wm:
                mock_wm.return_value = mock_model
                mock_model.transcribe.return_value = ([mock_seg], mock_info)

                await engine.load_model()
                result = await engine.transcribe(sample_audio_16khz)

        assert engine.state == STTState.READY
        assert result.text == "Hello world"
        assert result.language == "en"
        assert result.duration == 2.0
        assert len(result.segments) == 1
        assert result.segments[0].start == 0.0
        assert result.segments[0].speech_probability == pytest.approx(0.95)

    @pytest.mark.asyncio
    async def test_transcribe_fires_callbacks(
        self, sample_audio_16khz: np.ndarray
    ) -> None:
        partial_calls: list[str] = []
        final_results: list[TranscriptionResult] = []

        engine = STTEngine(
            on_partial_transcript=lambda t: partial_calls.append(t),
            on_final_transcript=lambda r: final_results.append(r),
        )
        mock_model = MagicMock()

        mock_seg = MagicMock()
        mock_seg.start = 0.0
        mock_seg.end = 1.0
        mock_seg.text = "partial"
        mock_seg.no_speech_prob = 0.1

        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.duration = 1.0

        with patch.dict(sys.modules, {"faster_whisper": MagicMock()}):
            with patch(
                "src.stt.engine.STTEngine._resolve_device", return_value="cpu"
            ), patch(
                "src.stt.engine.STTEngine._resolve_compute_type", return_value="int8"
            ), patch(
                "faster_whisper.WhisperModel", return_value=mock_model
            ) as mock_wm:
                mock_wm.return_value = mock_model
                mock_model.transcribe.return_value = ([mock_seg], mock_info)

                await engine.load_model()
                await engine.transcribe(sample_audio_16khz)

        assert "partial" in partial_calls
        assert len(final_results) == 1
        assert final_results[0].text == "partial"

    @pytest.mark.asyncio
    async def test_transcribe_stream_overrides_callbacks(
        self, sample_audio_16khz: np.ndarray
    ) -> None:
        stream_partial: list[str] = []

        engine = STTEngine(on_partial_transcript=lambda t: None)
        mock_model = MagicMock()

        mock_seg = MagicMock()
        mock_seg.start = 0.0
        mock_seg.end = 1.0
        mock_seg.text = "streamed"
        mock_seg.no_speech_prob = 0.1

        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.duration = 1.0

        with patch.dict(sys.modules, {"faster_whisper": MagicMock()}):
            with patch(
                "src.stt.engine.STTEngine._resolve_device", return_value="cpu"
            ), patch(
                "src.stt.engine.STTEngine._resolve_compute_type", return_value="int8"
            ), patch(
                "faster_whisper.WhisperModel", return_value=mock_model
            ) as mock_wm:
                mock_wm.return_value = mock_model
                mock_model.transcribe.return_value = ([mock_seg], mock_info)

                await engine.load_model()
                await engine.transcribe_stream(
                    sample_audio_16khz,
                    on_partial=lambda t: stream_partial.append(t),
                )

        assert "streamed" in stream_partial

    @pytest.mark.asyncio
    async def test_transcribe_failure_sets_error_state(
        self, sample_audio_16khz: np.ndarray
    ) -> None:
        errors: list[Exception] = []
        engine = STTEngine(on_error=lambda e: errors.append(e))
        mock_model = MagicMock()
        mock_model.transcribe.side_effect = RuntimeError("Whisper crashed")

        with patch.dict(sys.modules, {"faster_whisper": MagicMock()}):
            with patch(
                "src.stt.engine.STTEngine._resolve_device", return_value="cpu"
            ), patch(
                "src.stt.engine.STTEngine._resolve_compute_type", return_value="int8"
            ), patch(
                "faster_whisper.WhisperModel", return_value=mock_model
            ) as mock_wm:
                mock_wm.return_value = mock_model
                await engine.load_model()
                with pytest.raises(RuntimeError, match="crashed"):
                    await engine.transcribe(sample_audio_16khz)

        assert engine.state == STTState.ERROR
        assert len(errors) == 1

    def test_transcribe_invalid_audio_type(self) -> None:
        engine = STTEngine()
        with pytest.raises(TypeError, match="numpy array"):
            engine._validate_audio([1.0, 2.0])  # type: ignore[arg-type]

    def test_transcribe_invalid_audio_ndim(self) -> None:
        engine = STTEngine()
        audio = np.ones((10, 2), dtype=np.float32)
        with pytest.raises(ValueError, match="1-D mono"):
            engine._validate_audio(audio)

    def test_transcribe_invalid_audio_dtype(self) -> None:
        engine = STTEngine()
        audio = np.ones(100, dtype=np.int16)
        with pytest.raises(TypeError, match="float32"):
            engine._validate_audio(audio)

    def test_transcribe_empty_audio(self) -> None:
        engine = STTEngine()
        audio = np.array([], dtype=np.float32)
        with pytest.raises(ValueError, match="empty"):
            engine._validate_audio(audio)

    def test_transcribe_nan_audio(self) -> None:
        engine = STTEngine()
        audio = np.array([0.1, np.nan, 0.2], dtype=np.float32)
        with pytest.raises(ValueError, match="NaN or Inf"):
            engine._validate_audio(audio)

    def test_transcribe_inf_audio(self) -> None:
        engine = STTEngine()
        audio = np.array([0.1, np.inf, 0.2], dtype=np.float32)
        with pytest.raises(ValueError, match="NaN or Inf"):
            engine._validate_audio(audio)

    @pytest.mark.asyncio
    async def test_transcribe_language_fallback(self, sample_audio_16khz: np.ndarray) -> None:
        engine = STTEngine()
        mock_model = MagicMock()

        mock_seg = MagicMock()
        mock_seg.start = 0.0
        mock_seg.end = 1.0
        mock_seg.text = "tere"
        mock_seg.no_speech_prob = 0.1

        mock_info = MagicMock()
        mock_info.language = ""
        mock_info.duration = 1.0

        with patch.dict(sys.modules, {"faster_whisper": MagicMock()}):
            with patch(
                "src.stt.engine.STTEngine._resolve_device", return_value="cpu"
            ), patch(
                "src.stt.engine.STTEngine._resolve_compute_type", return_value="int8"
            ), patch(
                "faster_whisper.WhisperModel", return_value=mock_model
            ) as mock_wm:
                mock_wm.return_value = mock_model
                mock_model.transcribe.return_value = ([mock_seg], mock_info)

                await engine.load_model()
                result = await engine.transcribe(sample_audio_16khz)

        assert result.language == "auto"


class TestSTTEngineContextManager:
    @pytest.mark.asyncio
    async def test_async_context_manager(self) -> None:
        mock_model = MagicMock()
        with patch.dict(sys.modules, {"faster_whisper": MagicMock()}):
            with patch(
                "src.stt.engine.STTEngine._resolve_device", return_value="cpu"
            ), patch(
                "src.stt.engine.STTEngine._resolve_compute_type", return_value="int8"
            ), patch(
                "faster_whisper.WhisperModel", return_value=mock_model
            ) as mock_wm:
                mock_wm.return_value = mock_model
                async with STTEngine() as engine:
                    assert engine.is_ready
        assert not engine.is_ready
        assert engine.state == STTState.UNLOADED


class TestResolveComputeType:
    def test_cpu_honors_int8(self) -> None:
        engine = STTEngine(STTConfig(compute_type="int8"))
        assert engine._resolve_compute_type("cpu") == "int8"

    def test_cpu_honors_float32(self) -> None:
        engine = STTEngine(STTConfig(compute_type="float32"))
        assert engine._resolve_compute_type("cpu") == "float32"

    def test_cpu_honors_int16(self) -> None:
        engine = STTEngine(STTConfig(compute_type="int16"))
        assert engine._resolve_compute_type("cpu") == "int16"

    def test_cpu_falls_back_from_float16(self) -> None:
        engine = STTEngine(STTConfig(compute_type="float16"))
        assert engine._resolve_compute_type("cpu") == "int8"

    def test_cuda_honors_float16(self) -> None:
        engine = STTEngine(STTConfig(compute_type="float16"))
        assert engine._resolve_compute_type("cuda") == "float16"

    def test_cuda_honors_int8(self) -> None:
        engine = STTEngine(STTConfig(compute_type="int8"))
        assert engine._resolve_compute_type("cuda") == "int8"

    def test_cuda_honors_float32(self) -> None:
        engine = STTEngine(STTConfig(compute_type="float32"))
        assert engine._resolve_compute_type("cuda") == "float32"

    def test_cuda_honors_int8_float16(self) -> None:
        engine = STTEngine(STTConfig(compute_type="int8_float16"))
        assert engine._resolve_compute_type("cuda") == "int8_float16"

    def test_cuda_honors_int16(self) -> None:
        engine = STTEngine(STTConfig(compute_type="int16"))
        assert engine._resolve_compute_type("cuda") == "int16"

    def test_cuda_falls_back_from_invalid(self) -> None:
        engine = STTEngine(STTConfig(compute_type="invalid"))
        assert engine._resolve_compute_type("cuda") == "float16"


# ------------------------------------------------------------------
# Audio Preprocessing Tests
# ------------------------------------------------------------------

class TestNormalizeAudio:
    def test_empty_audio(self) -> None:
        result = STTEngine.normalize_audio(np.array([], dtype=np.float32))
        assert result.dtype == np.float32
        assert len(result) == 0

    def test_silence_unchanged(self) -> None:
        audio = np.zeros(1000, dtype=np.float32)
        result = STTEngine.normalize_audio(audio)
        np.testing.assert_array_almost_equal(result, np.zeros(1000, dtype=np.float32))

    def test_loud_audio_normalized(self) -> None:
        audio = np.ones(1000, dtype=np.float32) * 0.5
        result = STTEngine.normalize_audio(audio, target_rms=0.1)
        rms = float(np.sqrt(np.mean(result ** 2)))
        assert abs(rms - 0.1) < 0.01

    def test_output_dtype_float32(self) -> None:
        audio = np.ones(100, dtype=np.float64)
        result = STTEngine.normalize_audio(audio)
        assert result.dtype == np.float32


class TestTrimSilence:
    def test_empty_audio(self) -> None:
        result = STTEngine.trim_silence(np.array([], dtype=np.float32))
        assert len(result) == 0

    def test_silence_only(self) -> None:
        audio = np.zeros(16000, dtype=np.float32)
        result = STTEngine.trim_silence(audio)
        assert len(result) == 0

    def test_trim_silent_edges(self) -> None:
        audio = np.concatenate([
            np.zeros(8000, dtype=np.float32),
            np.ones(8000, dtype=np.float32) * 0.05,
            np.zeros(8000, dtype=np.float32),
        ])
        result = STTEngine.trim_silence(audio, threshold=0.01)
        assert len(result) < 9000
        assert len(result) > 7000

    def test_output_dtype_float32(self) -> None:
        audio = np.ones(1000, dtype=np.float64) * 0.05
        result = STTEngine.trim_silence(audio)
        assert result.dtype == np.float32


class TestResampleTo16khz:
    def test_already_16khz(self) -> None:
        audio = np.ones(16000, dtype=np.float32) * 0.1
        result = STTEngine.resample_to_16khz(audio, 16000)
        np.testing.assert_array_equal(result, audio)

    def test_empty_audio(self) -> None:
        result = STTEngine.resample_to_16khz(np.array([], dtype=np.float32), 44100)
        assert len(result) == 0

    def test_downsample_44_to_16(self) -> None:
        audio = np.ones(44100, dtype=np.float32) * 0.1
        result = STTEngine.resample_to_16khz(audio, 44100)
        assert result.dtype == np.float32
        assert abs(len(result) - 16000) <= 1

    def test_output_dtype_float32(self) -> None:
        audio = np.ones(44100, dtype=np.int16)
        result = STTEngine.resample_to_16khz(audio, 44100)
        assert result.dtype == np.float32


class TestPreprocess:
    def test_empty_audio(self) -> None:
        result = STTEngine.preprocess(np.array([], dtype=np.float32))
        assert len(result) == 0

    def test_multichannel_to_mono(self) -> None:
        audio = np.ones((1000, 2), dtype=np.float32) * 0.1
        result = STTEngine.preprocess(audio, sample_rate=16000)
        assert result.ndim == 1

    def test_resample_44_to_16(self) -> None:
        audio = np.ones(44100, dtype=np.float32) * 0.1
        result = STTEngine.preprocess(audio, sample_rate=44100)
        assert abs(len(result) - 16000) <= 1

    def test_output_float32(self) -> None:
        audio = np.ones(16000, dtype=np.int16) * 100
        result = STTEngine.preprocess(audio, sample_rate=16000)
        assert result.dtype == np.float32

    def test_normalize_disabled(self) -> None:
        audio = np.ones(1000, dtype=np.float32) * 0.5
        result = STTEngine.preprocess(audio, sample_rate=16000, normalize=False)
        rms = float(np.sqrt(np.mean(result ** 2)))
        assert abs(rms - 0.5) < 0.01

    def test_trim_silence_disabled(self) -> None:
        audio = np.concatenate([
            np.zeros(4000, dtype=np.float32),
            np.ones(8000, dtype=np.float32) * 0.05,
        ])
        result = STTEngine.preprocess(audio, sample_rate=16000, trim_silence_flag=False)
        assert len(result) == 12000
