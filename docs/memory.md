# Nexus Local AI Assistant — Memory & Context

> **Version:** 1.3.0
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
| STT | ✅ Complete (engine.py, 54 tests) |
| TTS | 📋 Planned |
| LLM Integration | ✅ Complete (async Ollama client, prompt/history support, streaming) |
| Camera/Vision | ✅ Complete (camera.py, tests added) |
| Memory Store | ✅ Complete (JSON persistence, similarity search, pruning) |
| Animated Face UI | ✅ Complete (face.py, face_server.py, demo HTMLs) |
| Selectable Face Themes | ✅ Complete (UI-FACE-002) |
| User Interface | 📋 Planned |
| Main Pipeline | ✅ Complete (INTEGRATION-001) |
| Packaging | 📋 Planned |
| Runtime State Machine | ✅ Complete (CORE-001) |
| Tool Execution & Permissions | ✅ Complete (TOOLS-001) |
| Goals & Resumable Tasks | ✅ Complete (TASKS-001) |
| LLM Tool Selection & Calling | ⏳ In Progress (TOOLS-002) |
| Structured Memory & Consent | 📋 Planned (MEM-002, MEM-003) |
| Persona & Interaction Modes | 📋 Planned (PERSONA-001) |
| Verification & Safe Learning | 📋 Planned (EVAL-001, LEARN-001) |

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
| D-032 | 2026-07-12 | Direct async HTTP client for Ollama | Small offline API surface, injectable transport, no orchestration dependency | Backend |
| D-033 | 2026-07-12 | Ollama newline-delimited JSON streaming | Native backend protocol and incremental UI-ready output | Backend |
| D-034 | 2026-07-12 | JSON memory store with token cosine similarity | Dependency-free, transparent local persistence suitable for small conversation histories | Backend |
| D-035 | 2026-07-12 | Atomic writes plus age/capacity pruning | Avoid partial files and bound local storage growth | Backend |
| D-036 | 2026-07-13 | Central NexusRuntime owns the request-response lifecycle | Keeps audio, STT, memory, LLM, TTS, playback, and future UI consumers behind one testable orchestration boundary | Integration |
| D-037 | 2026-07-13 | Runtime dependencies use small protocols and constructor injection | End-to-end behavior can be tested without hardware, model files, or a live Ollama backend | Integration |
| D-038 | 2026-07-13 | STT, TTS, capture, and playback are optional runtime services | Missing local hardware or models must not prevent text interaction from working | Integration |
| D-039 | 2026-07-12 | Build one authoritative Nexus runtime before adding broad autonomy | Existing services need a coherent, testable lifecycle before they can act reliably | Architect |
| D-040 | 2026-07-12 | Separate working, episodic, semantic, preference, and procedural memory | Different information requires different retrieval, confidence, privacy, and retention rules | Architect |
| D-041 | 2026-07-12 | Tool use is typed, permissioned, auditable, and verified | Useful autonomy must remain transparent, bounded, and evidence-based | Architect |
| D-042 | 2026-07-12 | Persona affects expression, not truth or safety standards | Playfulness must not reduce factual reliability or bypass user control | Architect |
| D-043 | 2026-07-12 | Learning produces reviewable lessons and proposals, not uncontrolled self-modification | User approval remains mandatory for code, prompts, permissions, and safety rules | Architect |
| D-044 | 2026-07-13 | RuntimeStateMachine is the sole authority for runtime state | Validated transitions prevent UI, face, and services from presenting contradictory activity | Integration |
| D-045 | 2026-07-13 | State events include previous state, current state, metadata, and UTC timestamp | Consumers can render and audit transitions without reading mutable runtime internals | Integration |
| D-046 | 2026-07-13 | Face emotion is derived through a state adapter | The existing face stays decoupled from orchestration while reflecting truthful runtime state | Integration |
| D-047 | 2026-07-13 | Face themes are palette/render-style presets over the existing SVG engine | Themes preserve emotions and animation without introducing bitmap assets or duplicate renderers | UI |
| D-048 | 2026-07-13 | Classic remains the default and unknown themes fail validation | Existing consumers remain compatible and invalid persisted values cannot silently alter rendering | UI |
| D-049 | 2026-07-13 | Every tool declares one of four explicit risk levels | Read-only, local-write, external, and destructive actions can follow different confirmation policy | Integration |
| D-050 | 2026-07-13 | ToolRegistry returns structured failures while propagating cancellation | Callers can recover from validation, permission, timeout, and execution errors without hiding user cancellation | Integration |
| D-051 | 2026-07-13 | Tool audit stores redacted inputs and status but never tool output | Local accountability is preserved without copying file contents or secrets into logs | Integration |
| D-052 | 2026-07-13 | Goals and plan steps persist as versioned atomic JSON | Task state remains local, transparent, restartable, and consistent with existing storage patterns | Integration |
| D-053 | 2026-07-13 | Active goals and steps recover as paused after process restart | Nexus never assumes interrupted work continued or completed while the process was offline | Integration |
| D-054 | 2026-07-13 | Successful verified steps require machine evidence or explicit user confirmation | LLM assertions alone cannot mark real work complete | Integration |
| D-055 | 2026-07-13 | Tool calls use Ollama's native function schema and role=tool result messages | The local backend receives its documented protocol without an invented intermediary format | Integration |
| D-056 | 2026-07-13 | All model-requested calls execute exclusively through ToolRegistry | Model output cannot bypass schema validation, risk policy, timeout, cancellation, or audit | Integration |
| D-057 | 2026-07-13 | Agent loops pause on confirmation and enforce call, repetition, timeout, and parallel-call guards | Human control and bounded execution take priority over autonomous continuation | Integration |

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

**Current Task:** TOOLS-002 — LLM Tool Selection & Calling

**Most recently completed:** ARCH-007 — Memory / Vector Store, ARCH-006 — LLM Integration, ARCH-005 — Text-to-Speech Engine

**What was built:**
- `src/llm/tool_types.py` and `LLMClient.chat` — native Ollama tool schemas, calls, and role=tool conversations
- `src/tools/calling.py` — typed completed, waiting-confirmation, and failed agent-run snapshots
- `src/tools/agent.py` — bounded selection, registry invocation, result injection, pause/resume, and recovery loop
- Tool descriptors and built-ins now expose defensive JSON-compatible parameter schemas
- `tests/test_llm_tools.py`, `tests/test_tool_agent.py`, and `tests/test_tool_agent_limits.py` — protocol, selection, confirmation, rejection, timeout, loop, limit, and cancellation tests
- `src/tasks/models.py` — typed goals, plan steps, dependencies, results, evidence, blockers, events, and statuses
- `src/tasks/store.py` and `src/tasks/codec.py` — atomic versioned JSON persistence and full model round-trip
- `src/tasks/operations.py` — validated start, pause, resume, cancel, block, resolve, fail, and complete transitions
- `src/tasks/manager.py` and `src/tasks/base.py` — inspectable, amendable, event-emitting persistent task manager
- `src/tasks/factory.py` — standard local task-manager construction
- `tests/test_tasks_manager.py` and `tests/test_tasks_persistence.py` — lifecycle, evidence, dependency, interruption, blocker, immutability, and restart tests
- `src/config/settings.py` — persisted task storage path
- `src/tools/models.py` — typed tool, request, result, descriptor, risk, and error contracts
- `src/tools/permissions.py` — configurable allow, confirm, and deny decisions by risk level
- `src/tools/registry.py` — discovery, validation, timeout, cancellation, invocation, and audit flow
- `src/tools/audit.py` — append-only JSONL audit with recursive sensitive-key redaction
- `src/tools/filesystem.py` — sandboxed directory listing, text reading, and project inspection
- `src/tools/factory.py` — ready-to-use built-in project registry construction
- `tests/test_tools_registry.py` and `tests/test_tools_filesystem.py` — permission, lifecycle, privacy, sandbox, and end-to-end tool tests
- `src/ui/face_themes.py` — classic, neon blue, pixel, red alert, and cosmic theme presets
- `src/ui/face.py` — runtime theme switching, glow effects, and pixel eye/mouth rendering
- `src/ui/face_server.py` — theme query support, discovery endpoint, and persisted default loading
- `src/ui/settings.py` and `src/config/settings.py` — persisted face-theme selection
- `tests/test_face_themes.py` — theme, emotion, switching, pixel, palette, and validation tests
- `src/app/state_machine.py` — authoritative transition table, validation, interruption, and subscriber delivery
- `src/app/events.py` — expanded typed states and transition events with previous state and UTC timestamp
- `src/app/face_state.py` — runtime-state to face-emotion adapter compatible with `NexusFace`
- `tests/test_state_machine.py` — normal, invalid, interrupted, blocked, recovery, subscriber, and face integration tests
- `src/app/runtime.py` — event-driven `NexusRuntime` for text and captured-audio requests
- `src/app/factory.py` — configuration-driven construction of audio, STT, LLM, memory, TTS, and playback services
- `src/app/events.py` — observable runtime state and event contracts for the future UI
- `src/app/contracts.py` — injectable service protocols for hardware-free integration testing
- `src/app/lifecycle.py` — graceful optional-service startup and shutdown helpers
- `src/main.py` — minimal interactive local text shell with clean lifecycle handling
- `tests/test_app.py` and `tests/test_app_factory.py` — end-to-end, audio, lifecycle, recovery, and configuration smoke tests
- `src/config/settings.py` — persisted audio-input, audio-output, and memory feature toggles
- `src/memory/store.py` — thread-safe JSON memory service with atomic persistence, token-frequency cosine search, metadata, and timestamps
- `tests/test_memory.py` — tests for storage, retrieval ranking, custom paths, corrupt data, and age/capacity pruning
- `src/config/settings.py` — configurable memory storage format, capacity, and maximum age
- `src/llm/client.py` — async Ollama chat client, structured responses, streaming, and typed backend errors
- `src/llm/prompts.py` — validated system prompt and conversation history construction
- `tests/test_llm.py` — tests for prompt flow, configuration, responses, streaming, timeouts, and backend failures
- `src/config/settings.py` — persisted LLM URL, model, temperature, token limit, timeout, and system prompt settings
- `src/tts/engine.py` — async Piper TTS engine with voice fallback and playback routing
- `tests/test_tts.py` — 7 tests covering synthesis, playback, errors, and fallback behavior
- `src/stt/engine.py` — `STTEngine` with faster-whisper, configurable model size/language, partial/final callbacks, graceful fallback, audio preprocessing utilities
- `tests/test_stt.py` — 54 tests covering config, state management, transcription, callbacks, error handling, audio validation, compute type resolution, and audio preprocessing
- `src/stt/__init__.py` — exports STTEngine, STTConfig, TranscriptionResult, Segment, STTState
- `src/audio/capture.py` — AudioCapture with PyAudio callback mode, VAD integration, background thread
- `src/audio/playback.py` — `AudioPlayback` with PyAudio write-thread, queue-based non-blocking playback, volume control, and file support
- `src/vision/camera.py` — `CameraCapture` with OpenCV, background thread, callback/queue API, and graceful camera-unavailability handling
- `src/config/settings.py` — NexusConfig with JSON persistence
- `src/ui/settings.py` — CustomTkinter settings window with audio device selection
- `tests/test_audio.py` — 28 audio tests (VAD + capture + playback)
- `tests/test_vision.py` — 11 camera tests
- `tests/test_settings.py` — 7 config tests

**Key decisions:**
- Store lightweight conversation memory as human-readable JSON without requiring an embedding model
- Rank results with Unicode-aware token-frequency cosine similarity
- Prune stale entries by age and enforce a maximum entry count after writes and loads
- Persist through an atomic temporary-file replacement to reduce corruption risk
- Use direct `httpx` integration with Ollama's local `/api/chat` endpoint
- Keep request construction public and deterministic for testing and future backend adapters
- Map backend connectivity/status errors and timeouts to separate LLM exceptions
- Stream Ollama's newline-delimited JSON response as incremental text chunks
- faster-whisper for STT (faster than OpenAI Whisper, good accuracy)
- Partial/final callback pattern for streaming transcription UX
- Audio preprocessing: normalize RMS, trim silence, resample to 16kHz
- Graceful fallback: ImportError/RuntimeError caught, error callback fired, state set to ERROR
- PyAudio callback mode for non-blocking capture
- soundfile for WAV, pydub for MP3
- CustomTkinter for settings panel
- Config persisted to `~/.nexus/config.json`
- Volume applied as a gain factor on float32 audio
- Graceful degradation when no speakers are available
- Audio device enumeration via PyAudio with "Default" fallback
- OpenCV for camera capture with optional import and graceful fallback
- Camera runs in a daemon thread named `nexus-camera-capture`
- Audio input validation: 1-D float32 mono required, non-empty, finite values only
- compute_type validated per device: int8_float16/int16 honored where supported, invalid values fall back with warning
- Segment confidence renamed to speech_probability (1.0 - no_speech_prob proxy)
- transcribe_stream no longer mutates instance callbacks (thread-safe per-call overrides)

**Architecture analysis — companion and workhorse direction:**

- The repository has working service-level foundations, but no authoritative orchestration layer yet.
- Implement `INTEGRATION-001` and `CORE-001` before broad UI polish, semantic memory, or autonomous tools.
- The preferred lifecycle is `IDLE → LISTENING → UNDERSTANDING → PLANNING → ACTING → VERIFYING → SPEAKING → IDLE`, with explicit waiting, blocked, error, and sleeping states.
- The animated face must reflect actual runtime state; it must not independently imply that work succeeded.
- Serious work requires typed goals, resumable plans, permissioned tools, structured results, and evidence-backed completion.
- Companion behavior should use configurable companion, balanced, and focused modes plus bounded playfulness and proactivity.
- Long-term memory must be selective and user-controlled. Sensitive information needs explicit policy and all memories need provenance.
- Safe self-development means learning from verified outcomes and feedback. Nexus may propose changes, but must not silently rewrite source code, core prompts, permissions, or safety policy.
- Documentation currently describes ChromaDB while the implementation uses JSON token-cosine search; `MEM-002` must either reconcile the documentation or introduce a backend-neutral hybrid retrieval layer.
- `pyproject.toml` currently discovers `nexus*` packages, while modules live directly below `src/`; `ARCH-010` tracks the required package-layout repair.
- The first useful vertical slice is text input → relevant memory → LLM → response, followed by microphone → STT → the same cycle → TTS, all driven by runtime state and covered by an end-to-end smoke test.

**Recommended implementation order:**

1. `INTEGRATION-001` — minimal end-to-end runtime
2. `CORE-001` — authoritative states and events
3. `TOOLS-001` — typed tools and permissions
4. `TASKS-001` — goals, plans, interruption, and resume
5. `MEM-002` and `MEM-003` — structured memory and user control
6. `PERSONA-001` — bounded companion behavior
7. `EVAL-001` — verification and feedback
8. `LEARN-001` — safe reflection and learning
9. `UI-008` — unified companion workspace
10. `ARCH-010` and `OPS-001` — reliable installation and distribution

**New backlog tasks discovered:** `CORE-001`, `TOOLS-001`, `TOOLS-002`, `TOOLS-003`,
`WEB-001`, `CONNECTOR-001`, `CONNECTOR-002`, `CONNECTOR-003`, `CONNECTOR-004`,
`CONNECTOR-005`, `PLUGIN-001`, `TASKS-001`, `MEM-002`, `MEM-003`, `PERSONA-001`,
`EVAL-001`, `LEARN-001`, `UI-008`, and `ARCH-010`.

**External capability implementation order:**

1. `TASKS-001` — persistent goals and resumable plans
2. `TOOLS-002` — LLM tool selection through the existing registry
3. `TOOLS-003` — sandboxed local development work
4. `WEB-001` — cited web research
5. `CONNECTOR-001` — credential vault and OAuth foundation
6. `CONNECTOR-002` and `CONNECTOR-003` — Gmail and Google Calendar
7. `CONNECTOR-004` and `CONNECTOR-005` — Telegram and LinkedIn-assisted workflows
8. `PLUGIN-001` — third-party MCP and plugin discovery

**TOOLS-002 validation:** 189 tests pass. Ruff and mypy are configured in
`pyproject.toml` but are not installed in the current environment. All new Python files compile,
stay within the project's 150-line limit, and `git diff --check` passes.

**Next Task after merge:** TOOLS-003 — Local Development Toolset

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
    memory_storage_format: str = "json"
    memory_max_entries: int = 1000
    memory_max_age_days: int = 90
    theme: str = "dark"
    language: str = "et"

    def save(self, path: Path | str | None = None) -> None
    @classmethod
    def load(cls, path: Path | str | None = None) -> NexusConfig
```

### Memory Store API

```python
# src/memory/store.py
class MemoryStore:
    def __init__(
        self,
        path: Path | str,
        *,
        storage_format: str = "json",
        max_entries: int = 1000,
        max_age_days: int | None = 90,
    ): ...
    def add(self, text: str, *, metadata: dict | None = None, ...) -> MemoryEntry
    def search(self, query: str, *, limit: int = 5) -> list[MemoryResult]
    def prune(self, *, now: datetime | None = None, persist: bool = True) -> int
    def save(self) -> None
    def load(self) -> None
```

Storage is a versioned JSON document. Search uses token-frequency cosine similarity;
cleanup combines configurable age retention with a maximum entry count.

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
    async def transcribe(
        self,
        audio: np.ndarray,
        *,
        fire_partial: bool = True,
        on_partial: Callable[[str], None] | None = None,
        on_final: Callable[[TranscriptionResult], None] | None = None,
    ) -> TranscriptionResult
    async def transcribe_stream(
        self,
        audio: np.ndarray,
        on_partial: Callable[[str], None] | None = None,
        on_final: Callable[[TranscriptionResult], None] | None = None,
    ) -> TranscriptionResult

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
    speech_probability: float
```

---

### TTS Engine API

```python
# src/tts/engine.py
class TTSConfig:
    voice: str = "en_US-lessac-medium"
    speed: float = 1.0
    language: str = "en"
    model_dir: Path = Path("~/.nexus/voices")
    fallback_voice: str | None = None

class TTSEngine:
    async def load_model(self) -> None
    async def unload_model(self) -> None
    async def synthesize(self, text: str) -> SynthesisResult
    async def speak(self, text: str, playback: PlaybackService) -> SynthesisResult
```

Piper is the offline backend. Model loading and synthesis run through `asyncio.to_thread`.
Generated 16-bit WAV is converted to mono `float32` samples for `AudioPlayback.play`.
The configured fallback voice is tried when the primary voice is missing or unsupported.

---

### Main Application Runtime API

```python
# src/app/runtime.py
class RuntimeServices:
    llm: LLMService
    memory: MemoryService | None
    capture: CaptureService | None
    playback: PlaybackService | None
    stt: STTService | None
    tts: TTSService | None

class NexusRuntime:
    def subscribe(self, callback: Callable[[RuntimeEvent], None]) -> None
    def interrupt(self, message: str = "Interrupted") -> RuntimeEvent
    async def start(self) -> None
    async def stop(self) -> None
    async def handle_text(self, text: str) -> str
    async def handle_audio(self, audio: np.ndarray) -> str

def create_runtime(config: NexusConfig | None = None) -> NexusRuntime

class RuntimeStateMachine:
    @property
    def state(self) -> RuntimeState
    def subscribe(self, callback: Callable[[RuntimeEvent], None]) -> None
    def can_transition(self, target: RuntimeState) -> bool
    def transition(self, target: RuntimeState, ...) -> RuntimeEvent
    def interrupt(self, message: str = "Interrupted") -> RuntimeEvent

def face_emotion_for(state: RuntimeState) -> str
```

The state machine supports STOPPED, IDLE, LISTENING, UNDERSTANDING, PLANNING, ACTING,
VERIFYING, SPEAKING, WAITING_CONFIRMATION, BLOCKED, ERROR, and SLEEPING. Every transition is
validated before mutation and emits previous/current state metadata. Optional speech services
degrade independently so text interaction remains usable.

---

### Tool Registry API

```python
class RiskLevel(Enum):
    READ_ONLY = "read_only"
    LOCAL_WRITE = "local_write"
    EXTERNAL = "external"
    DESTRUCTIVE = "destructive"

class ToolRegistry:
    def register(self, tool: Tool) -> None
    def discover(self) -> tuple[ToolDescriptor, ...]
    async def invoke(
        self, request: ToolRequest, *, confirmed: bool = False,
        timeout: float | None = None,
    ) -> ToolResult

def create_project_tool_registry(project_root: Path | str, ...) -> ToolRegistry
```

Built-in tools are `filesystem.list_directory`, `filesystem.read_text`, and `project.inspect`.
Resolved paths must remain within the configured project root. Local-write, external, and
destructive tools require confirmation by default. Every attempted invocation creates a redacted
JSONL audit entry, including rejected, failed, timed-out, and cancelled requests.

---

### LLM Tool-Calling API

```python
class ToolCallingAgent:
    async def run(self, prompt: str) -> ToolAgentRun
    async def resume(self, run: ToolAgentRun, *, confirmed: bool) -> ToolAgentRun

class ToolRunStatus(Enum):
    COMPLETED = "completed"
    WAITING_CONFIRMATION = "waiting_confirmation"
    FAILED = "failed"
```

The agent sends registered JSON function schemas through Ollama's native `tools` field, parses
`message.tool_calls`, executes exclusively through `ToolRegistry`, and returns results as
`role: tool` messages. It rejects parallel calls for now and bounds total calls, repeated-call loops,
timeouts, and cancellation. Confirmation-required calls return a resumable snapshot.

Protocol reference: https://docs.ollama.com/capabilities/tool-calling

---

### Goal & Task Manager API

```python
class TaskManager:
    def create_goal(self, objective: str) -> Goal
    def get_goal(self, goal_id: str) -> Goal
    def list_goals(self) -> tuple[Goal, ...]
    def add_step(self, goal_id: str, title: str, ...) -> PlanStep
    def amend_step(self, goal_id: str, step_id: str, ...) -> PlanStep
    def start_goal(self, goal_id: str) -> None
    def start_step(self, goal_id: str, step_id: str) -> None
    def pause_goal(self, goal_id: str) -> None
    def resume_goal(self, goal_id: str) -> None
    def cancel_goal(self, goal_id: str) -> None
    def block_step(self, goal_id: str, step_id: str, reason: str, ...) -> None
    def resolve_blocker(self, goal_id: str, step_id: str) -> None
    def complete_step(self, goal_id: str, step_id: str, summary: str, evidence=()) -> None
    def fail_step(self, goal_id: str, step_id: str, summary: str) -> None
    def complete_goal(self, goal_id: str) -> None
```

Returned goals are deep copies so callers cannot mutate persisted manager state. After restart,
previously active work becomes paused. Dependency checks gate step start, and verified evidence or a
verified user-confirmation artifact gates successful step completion.

---

### Face Theme API

```python
class FaceTheme(Enum):
    CLASSIC = "classic"
    NEON_BLUE = "neon_blue"
    PIXEL = "pixel"
    RED_ALERT = "red_alert"
    COSMIC = "cosmic"

face = NexusFace(theme=FaceTheme.COSMIC)
face.set_theme("pixel")
svg = face.render("happy")
```

The face server accepts `theme` on render and animate requests and exposes available values through
`GET /api/face/themes`. The animated browser demo includes a theme selector.

---

## 7. Completed Tasks

| Task ID | Name | Completed | By |
|---------|------|-----------|----|
| DOCS-001 | Create Project Documentation Foundation | 2026-07-12 | Documentation Agent |
| DOCS-002 | Initialize Project Structure & Git | 2026-07-12 | Documentation Agent |
| UI-FACE-001 | Looi-Style Animated Face Module | 2026-07-12 | Documentation Agent |
| ARCH-001 | Audio Capture Service | 2026-07-12 | Backend Agent |
| ARCH-002 | Audio Playback Service | 2026-07-12 | Backend Agent |
| ARCH-003 | Camera / Vision Service | 2026-07-12 | Backend Agent |
| ARCH-004 | Speech-to-Text Engine | 2026-07-12 | Backend Agent |
| ARCH-005 | Text-to-Speech Engine | 2026-07-12 | Backend Agent |
| ARCH-006 | LLM Integration | 2026-07-12 | Backend Agent |
| ARCH-007 | Memory / Vector Store | 2026-07-12 | Backend Agent |
| ARCH-009 | UI Settings Panel | 2026-07-12 | Backend Agent |
| INTEGRATION-001 | Main Application & Pipeline | 2026-07-13 | Integration Agent |
| CORE-001 | Assistant Runtime State Machine | 2026-07-13 | Integration Agent |
| UI-FACE-002 | Selectable Face Themes | 2026-07-13 | UI Agent |
| TOOLS-001 | Tool Protocol, Registry & Permissions | 2026-07-13 | Integration Agent |
| TASKS-001 | Goals, Plans & Resumable Tasks | 2026-07-13 | Integration Agent |

---

> **Last updated:** 2026-07-13
> **Maintainer:** Documentation Agent
