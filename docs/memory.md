# Nexus Local AI Assistant — Memory & Context

> **Version:** 1.2.0  
> **Purpose:** Persistent project memory — what has been done, what was decided, what problems were encountered, and what every agent must know before starting work.

---

## 1. Project State

| Aspect | Status |
|--------|--------|
| Documentation | ✅ Complete (agents.md, task.md, tehnika.md, memory.md, rules.md) |
| Project Scaffold | ✅ Complete |
| Git Repository | ✅ Initialized on `develop` |
| Audio Capture | ✅ Complete (capture.py, vad.py, 17 tests) |
| Audio Playback | ✅ Complete (playback.py, tests added) |
| Settings / Config | ✅ Complete (NexusConfig, UI panel, 7 tests) |
| VAD | ✅ Built into capture pipeline |
| STT | ✅ Complete (engine.py, 37 tests) |
| TTS | 📋 Planned |
| LLM Integration | 📋 Planned |
| Camera/Vision | ✅ Complete (camera.py, tests added) |
| Memory Store | 📋 Planned |
| Animated Face UI | ✅ Complete (face.py, face_server.py, demo HTMLs) |
| User Interface | 📋 Planned |
| Main Pipeline | 📋 Planned |
| Packaging | 📋 Planned |

**Legend:** ✅ Done | ⏳ In Progress | 📋 Planned | ❌ Not Started | 🚫 Blocked

---

## 2. Decision Log

| ID | Date | Decision | Rationale | Author |
|----|------|----------|-----------|--------|
| D-001–D-012 | 2026-07-12 | Initial technology decisions | — | Architect |
| D-013–D-015 | 2026-07-12 | Face/SVG/server decisions | — | Architect |
| D-016 | 2026-07-12 | webrtcvad for VAD | Lightweight, no ML model needed, fast | Backend |
| D-017 | 2026-07-12 | PyAudio callback mode | Non-blocking, native thread safety | Backend |
| D-018 | 2026-07-12 | VAD state machine (SILENCE→SPEECH→ENDING) | Prevents false starts, handles trailing silence | Backend |
| D-019 | 2026-07-12 | PyAudio write-thread for playback | Non-blocking, simple output streaming | Backend |
| D-020 | 2026-07-12 | soundfile for WAV, pydub for MP3 | Covers required formats with minimal deps | Backend |
| D-021 | 2026-07-12 | Volume as gain factor on float32 audio | Consistent with capture pipeline dtype | Backend |
| D-022 | 2026-07-12 | NexusConfig persisted to JSON | Simple, human-editable, no extra runtime deps | Backend |
| D-023 | 2026-07-12 | CustomTkinter for settings UI | Native Windows look, fast to implement | Backend |
| D-024 | 2026-07-12 | Default TTS voice: en_US-lessac-medium | Good Estonian/English coverage in Piper | Backend |
| D-025 | 2026-07-12 | Default STT language: et | Primary user language is Estonian | Backend |
| D-026 | 2026-07-12 | PyAudio device enumeration in settings UI | Lets user pick mic/speaker without editing config | Backend |
| D-027 | 2026-07-12 | OpenCV for camera capture | Industry standard, simple Python API | Backend |
| D-028 | 2026-07-12 | Camera runs in background thread | Non-blocking, consistent with audio capture | Backend |
| D-029 | 2026-07-12 | faster-whisper for STT engine | Best offline accuracy, faster than original Whisper | Backend |
| D-030 | 2026-07-12 | STT partial/final callback pattern | Supports streaming UX with interim results | Backend |
| D-031 | 2026-07-12 | Audio preprocessing before STT | Normalize, trim silence, resample to 16kHz | Backend |

---

## 3. Architecture Decisions (ADRs)

### ADR-001: In-process Message Passing — **ACCEPTED**

### ADR-002: Model Storage Strategy — **ACCEPTED**

### ADR-003: Threading Model — **ACCEPTED**

### ADR-004: Face Rendering Strategy — **ACCEPTED**

### ADR-005: Audio Capture Threading

**Context:** Audio capture must not block the asyncio event loop.

**Decision:** Use **PyAudio callback mode** (which calls from a native thread) + a thread-safe `queue.Queue` to pass audio chunks to an async processing thread.

```
[PyAudio Native Thread] → queue.Queue → [nexus-audio-capture Thread] → [VAD + callbacks]
```

**Consequences:**
- ✅ Main event loop never blocks
- ✅ PyAudio handles buffer underrun gracefully via callback
- ❌ Two threads involved (native + Python), but queue decouples them cleanly

### ADR-006: VAD State Machine

**Context:** Raw VAD is noisy — it can flicker on/off during speech.

**Decision:** Three-state machine: `SILENCE → SPEECH → ENDING → SILENCE`. The ENDING state has a configurable grace period (default 600ms) that allows short pauses in speech without triggering speech_end.

---

## 4. Blocker Log

| ID | Date | Blocker | Status | Resolution |
|----|------|---------|--------|------------|
| — | — | None | — | — |

---

## 5. Current Sprint Context

**Current Task:** ARCH-005 — Text-to-Speech Engine

**Most recently completed:** ARCH-004 — Speech-to-Text Engine, ARCH-003 — Camera / Vision Service, ARCH-009 — UI Settings Panel

**What was built:**
- `src/stt/engine.py` — `STTEngine` with faster-whisper, configurable model size/language, partial/final callbacks, graceful fallback, audio preprocessing utilities
- `tests/test_stt.py` — 37 tests covering config, state management, transcription, callbacks, error handling, and audio preprocessing
- `src/stt/__init__.py` — exports STTEngine, STTConfig, TranscriptionResult, Segment, STTState
- `src/audio/capture.py` — AudioCapture with PyAudio callback mode, VAD integration, background thread
- `src/audio/playback.py` — AudioPlayback with queue-based non-blocking playback, volume control
- `src/vision/camera.py` — CameraCapture with OpenCV, background thread, callback/queue API
- `src/config/settings.py` — NexusConfig with JSON persistence
- `src/ui/settings.py` — CustomTkinter settings window
- `tests/test_audio.py` — 28 audio tests (VAD + capture + playback)
- `tests/test_vision.py` — 11 camera tests
- `tests/test_settings.py` — 7 config tests

**Key decisions:**
- faster-whisper for STT (faster than OpenAI Whisper, good accuracy)
- Partial/final callback pattern for streaming transcription UX
- Audio preprocessing: normalize RMS, trim silence, resample to 16kHz
- Graceful fallback: ImportError/RuntimeError caught, error callback fired, state set to ERROR
- PyAudio callback mode for non-blocking capture
- soundfile for WAV, pydub for MP3
- CustomTkinter for settings panel
- Config persisted to `~/.nexus/config.json`
- OpenCV for camera capture with graceful fallback

**Next Task:** ARCH-005 — Text-to-Speech Engine

---

## 6. API Contracts Summary

### Audio Capture API

```python
# src/audio/capture.py
class AudioCaptureConfig:
    sample_rate: int = 16000
    chunk_size: int = 1024
    device_index: int | None = None
    channels: int = 1
    dtype: str = "float32"
    silence_timeout: float = 30.0

class AudioCapture:
    async def start(self) -> None
    async def stop(self) -> None
    @property
    def is_active(self) -> bool
    def get_speech_buffer(self) -> np.ndarray | None

    # Callbacks (set before start)
    on_audio_chunk: Callable[[np.ndarray], None] | None
    on_speech_start: Callable[[], None] | None
    on_speech_end: Callable[[], None] | None
```

### VAD API

```python
# src/audio/vad.py
class VadConfig:
    aggressiveness: int = 3
    sample_rate: int = 16000
    frame_ms: int = 30
    silence_duration_ms: int = 600
    min_speech_duration_ms: int = 100

class VoiceActivityDetector:
    @property
    def state(self) -> VadState
    def process_chunk(self, chunk: np.ndarray) -> VadState
    def is_speech(self, frame: bytes) -> bool
    def reset(self) -> None
```

### Inter-Module Data Types

Same as before, with additional `AudioCaptureConfig`, `VadConfig`, and `NexusConfig` dataclasses.

### Settings API

```python
# src/config/settings.py
class NexusConfig:
    mic_device_index: int | None = None
    speaker_device_index: int | None = None
    sample_rate: int = 16000
    playback_volume: float = 0.8
    tts_voice: str = "en_US-lessac-medium"
    tts_speed: float = 1.0
    stt_model_size: str = "base"
    stt_language: str = "et"
    llm_model: str = "llama3.1"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2048
    ollama_url: str = "http://localhost:11434"
    camera_index: int = 0
    camera_resolution: tuple[int, int] = (640, 480)
    camera_fps: int = 15
    memory_path: str = "~/.nexus/memory"
    theme: str = "dark"
    language: str = "et"

    def save(self, path: Path | str | None = None) -> None
    @classmethod
    def load(cls, path: Path | str | None = None) -> NexusConfig
```

### UI Settings Panel API

```python
# src/ui/settings.py
class SettingsWindow(ctk.CTk):
    def __init__(self, config: NexusConfig | None = None, on_save: Callable[[NexusConfig], None] | None = None): ...

def open_settings(on_save: Callable[[NexusConfig], None] | None = None) -> SettingsWindow
```

### Audio Playback API

```python
# src/audio/playback.py
class AudioPlaybackConfig:
    sample_rate: int = 24000
    chunk_size: int = 1024
    device_index: int | None = None
    channels: int = 1
    dtype: str = "float32"
    max_queue_size: int = 100

class AudioPlayback:
    async def start(self) -> None
    async def stop(self) -> None
    async def play(self, audio: np.ndarray, sample_rate: int | None = None) -> None
    async def play_file(self, path: Path) -> None
    async def set_volume(self, volume: float) -> None

    @property
    def is_active(self) -> bool
    ```

### STT Engine API

```python
# src/stt/engine.py
class STTConfig:
    model_size: str = "base"
    device: str = "auto"
    compute_type: str = "int8"
    language: str = "auto"
    beam_size: int = 5
    vad_filter: bool = True

class STTEngine:
    def __init__(
        self,
        config: STTConfig | None = None,
        on_partial_transcript: Callable[[str], None] | None = None,
        on_final_transcript: Callable[["TranscriptionResult"], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ): ...

    async def load_model(self) -> None
    async def unload_model(self) -> None
    async def transcribe(self, audio: np.ndarray, *, fire_partial: bool = True) -> TranscriptionResult
    async def transcribe_stream(self, audio: np.ndarray, ...) -> TranscriptionResult

    @staticmethod
    def normalize_audio(audio: np.ndarray, target_rms: float = 0.1) -> np.ndarray
    @staticmethod
    def trim_silence(audio: np.ndarray, sample_rate: int = 16000, ...) -> np.ndarray
    @staticmethod
    def resample_to_16khz(audio: np.ndarray, original_sample_rate: int) -> np.ndarray
    @staticmethod
    def preprocess(audio: np.ndarray, sample_rate: int = 16000, ...) -> np.ndarray

    @property
    def state(self) -> STTState
    @property
    def is_ready(self) -> bool

@dataclass
class TranscriptionResult:
    text: str
    language: str
    confidence: float
    segments: list[Segment]
    duration: float

@dataclass
class Segment:
    start: float
    end: float
    text: str
    confidence: float
```

---

## 8. Completed Tasks

| Task ID | Name | Completed | By |
|---------|------|-----------|----|
| DOCS-001 | Create Project Documentation Foundation | 2026-07-12 | Documentation Agent |
| DOCS-002 | Initialize Project Structure & Git | 2026-07-12 | Documentation Agent |
| UI-FACE-001 | Looi-Style Animated Face Module | 2026-07-12 | Documentation Agent |
| ARCH-001 | Audio Capture Service | 2026-07-12 | Backend Agent |
| ARCH-002 | Audio Playback Service | 2026-07-12 | Backend Agent |
| ARCH-003 | Camera / Vision Service | 2026-07-12 | Backend Agent |
| ARCH-004 | Speech-to-Text Engine | 2026-07-12 | Backend Agent |
| ARCH-009 | UI Settings Panel | 2026-07-12 | Backend Agent |

---

> **Last updated:** 2026-07-12
> **Maintainer:** Documentation Agent
