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

**Most recently completed:** ARCH-002 — Audio Playback Service

**What was built:**
- `src/audio/playback.py` — `AudioPlayback` with PyAudio write-thread, queue, volume, file support
- `tests/test_audio.py` — 9 new playback tests added (28 total passing)
- `requirements.txt` — added `pydub` for MP3 support

**Key decisions:**
- PyAudio write-thread for non-blocking playback
- soundfile for WAV, pydub for MP3, raw PCM via numpy
- Volume applied as gain factor on float32 audio
- Graceful degradation when no speakers are available
- Simple linear interpolation resampling for mismatched sample rates

**Next Task:** ARCH-003 — Camera / Vision Service

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

Same as before, with additional `AudioCaptureConfig` and `VadConfig` dataclasses.

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
