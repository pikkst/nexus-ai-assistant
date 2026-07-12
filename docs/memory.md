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
| STT | 📋 Planned |
| TTS | 📋 Planned |
| LLM Integration | 📋 Planned |
| Camera/Vision | 📋 Planned |
| Memory Store | 📋 Planned |
| Animated Face UI | ✅ Complete (face.py, face_server.py, demo HTMLs) |
| User Interface | 📋 Planned |
| Main Pipeline | 📋 Planned |
| Packaging | 📋 Planned |
| Runtime State Machine | 📋 Planned (CORE-001) |
| Tool Execution & Permissions | 📋 Planned (TOOLS-001) |
| Goals & Resumable Tasks | 📋 Planned (TASKS-001) |
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
| D-027 | 2026-07-12 | Build one authoritative Nexus runtime before adding broad autonomy | Existing services need a coherent, testable lifecycle before they can act reliably | Architect |
| D-028 | 2026-07-12 | Separate working, episodic, semantic, preference, and procedural memory | Different information requires different retrieval, confidence, privacy, and retention rules | Architect |
| D-029 | 2026-07-12 | Tool use is typed, permissioned, auditable, and verified | Useful autonomy must remain transparent, bounded, and evidence-based | Architect |
| D-030 | 2026-07-12 | Persona affects expression, not truth or safety standards | Playfulness must not reduce factual reliability or bypass user control | Architect |
| D-031 | 2026-07-12 | Learning produces reviewable lessons and proposals, not uncontrolled self-modification | User approval remains mandatory for code, prompts, permissions, and safety rules | Architect |

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

**Current Task:** ARCH-003 — Camera / Vision Service (next in queue)

**Most recently completed:** ARCH-002 — Audio Playback Service, ARCH-009 — UI Settings Panel

**What was built:**
- `src/audio/playback.py` — `AudioPlayback` with PyAudio write-thread, queue, volume, file support
- `src/config/settings.py` — `NexusConfig` with JSON persistence
- `src/ui/settings.py` — CustomTkinter settings window (volume, sample rate, input/output device selection, voice, speed, language, theme)
- `tests/test_settings.py` — 7 tests for config load/save/roundtrip
- `tests/test_audio.py` — playback tests added (24 total passing)

**Key decisions:**
- PyAudio write-thread for non-blocking playback
- soundfile for WAV, pydub for MP3, raw PCM via numpy
- CustomTkinter for settings panel (native Windows look, simple API)
- Config persisted to `~/.nexus/config.json`
- Volume applied as gain factor on float32 audio
- Graceful degradation when no speakers are available
- Audio device enumeration via PyAudio with "Default" fallback

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

**New backlog tasks discovered:** `CORE-001`, `TOOLS-001`, `TASKS-001`, `MEM-002`, `MEM-003`, `PERSONA-001`, `EVAL-001`, `LEARN-001`, `UI-008`, and `ARCH-010`.

**Validation note:** 107 tests passed in the managed environment. Fourteen tests using pytest temporary directories could not start because the environment denied creation of both its default temp directory and `C:\tmp\nexus-pytest`; no application assertion failed in those cases.

**Next Task:** INTEGRATION-001 — Main Application & Pipeline, followed by CORE-001

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

---

> **Last updated:** 2026-07-12  
> **Maintainer:** Documentation Agent
