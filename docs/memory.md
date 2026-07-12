# Nexus Local AI Assistant — Memory & Context

> **Version:** 1.1.0  
> **Purpose:** Persistent project memory — what has been done, what was decided, what problems were encountered, and what every agent must know before starting work.

---

## 1. Project State

| Aspect | Status |
|--------|--------|
| Documentation | ✅ Complete (agents.md, task.md, tehnika.md, memory.md, rules.md) |
| Project Scaffold | ❌ Not started |
| Git Repository | ❌ Not initialized |
| Audio Capture | 📋 Planned |
| Audio Playback | 📋 Planned |
| VAD | 📋 Planned |
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
| D-001 | 2026-07-12 | Python 3.11+ as primary language | Best ecosystem for AI/ML, audio, video processing | Architect |
| D-002 | 2026-07-12 | Ollama + Llama 3.1 as LLM backend | Simplest local setup, good performance, active community | Architect |
| D-003 | 2026-07-12 | faster-whisper for STT | Best accuracy-to-speed ratio for offline use, CTranslate2 backend | Architect |
| D-004 | 2026-07-12 | Piper TTS as primary TTS | Truly offline, fast inference, supports Estonian | Architect |
| D-005 | 2026-07-12 | PyAudio for audio I/O | Industry standard, low latency, cross-platform | Architect |
| D-006 | 2026-07-12 | OpenCV for camera | Most mature computer vision library, extensive format support | Architect |
| D-007 | 2026-07-12 | ChromaDB for memory | Zero-config, no server process, pure Python, local-only | Architect |
| D-008 | 2026-07-12 | Gradio as primary UI | Fast to prototype, built-in audio/video components, dark theme | Architect |
| D-009 | 2026-07-12 | CustomTkinter as fallback UI | Native desktop feel, better system tray integration | Architect |
| D-010 | 2026-07-12 | loguru for logging | Structured logging, easy file rotation, less boilerplate | Architect |
| D-011 | 2026-07-12 | Async architecture (asyncio) | Non-blocking I/O for audio/video streams, better responsiveness | Architect |
| D-012 | 2026-07-12 | Modular pipeline pattern | Each component independently testable, swappable, maintainable | Architect |
| D-013 | 2026-07-12 | Looi-style animated face as primary UX | Makes assistant feel alive and approachable, communicates state naturally | Architect |
| D-014 | 2026-07-12 | SVG-based face rendering | Zero dependencies, works in any browser/Gradio/Tkinter, small payload | Architect |
| D-015 | 2026-07-12 | Face server on port 8765 | Separate from main UI, allows independent testing and animation | Architect |

---

## 3. Architecture Decisions (ADRs)

### ADR-001: In-process Message Passing vs IPC

**Context:** Nexus has multiple modules that need to communicate (audio → STT → LLM → TTS → playback).

**Decision:** Use **in-process async function calls** (direct Python method calls with asyncio) rather than a message broker, pipes, or HTTP.

**Consequences:**
- ✅ Zero serialization overhead
- ✅ Simple debugging (single process)
- ✅ Lower latency
- ❌ No inter-process isolation (one crash takes everything down)
- ❌ Cannot scale modules to separate machines

**Mitigation:** Each module has try/except boundaries and starts independently. A crashed module can be restarted without restarting the whole application.

---

### ADR-002: Model Storage Strategy

**Context:** Whisper and Piper models are large (2-8 GB total). They need to be downloaded somewhere persistent.

**Decision:** Use `~/.nexus/` as the central data directory. Models are downloaded on first use and cached indefinitely.

**Layout:**
```
~/.nexus/
├── config.json        # User configuration
├── memory/            # ChromaDB storage
├── voices/            # Piper TTS voice models
├── logs/              # Application logs
└── cache/             # Temporary files and caches
```

**Rationale:** Follows XDG convention and is easy to find and backup.

---

### ADR-003: Threading Model

**Context:** Audio capture and camera capture are blocking I/O operations. They must not block the main asyncio event loop.

**Decision:** Each blocking I/O source runs in its own **dedicated thread** with a thread-safe queue to pass data to the async world.

```
[Audio Thread]  → asyncio.Queue → [Async Pipeline]
[Camera Thread] → asyncio.Queue → [Async Pipeline]
[Main Thread]    → asyncio event loop
```

---

### ADR-004: Face Rendering Strategy

**Context:** The assistant needs a visual representation that shows its state (idle, listening, thinking, speaking, etc.).

**Decision:** Use **pure SVG generation from Python** with zero external dependencies. The `NexusFace` class renders SVG strings directly. A lightweight HTTP server serves the SVGs for web-based UIs.

**Consequences:**
- ✅ Zero dependencies (no PIL, no Cairo, no OpenGL)
- ✅ Works in any browser, Gradio, or Tkinter (via `render()` → HTML embed)
- ✅ Animation via `animate(dt)` method for smooth blink/gaze cycles
- ✅ 9 emotion states cover all pipeline stages
- ❌ Not photorealistic (intentionally cartoon/stylized like Looi)

---

## 4. Blocker Log

| ID | Date | Blocker | Status | Resolution |
|----|------|---------|--------|------------|
| — | — | None yet | — | — |

---

## 5. Current Sprint Context

**Current Task:** UI-FACE-001 — Looi-Style Animated Face Module ✅ COMPLETED

**What was built:**
- `src/ui/face.py` — `NexusFace` class with 9 emotions, blink/gaze/mouth animation, SVG generation
- `src/ui/face_server.py` — HTTP API server (port 8765) serving SVGs and demo HTML
- `src/ui/face_demo_grid.html` — Static HTML showing all 9 emotions in a grid
- `src/ui/face_demo_animated.html` — Interactive HTML demo with emotion buttons
- `docs/nexus_face_preview.svg` — Preview of the face design

**Key decisions:**
- Looi-style design with large anime eyes, soft head shape, blush, and expressive eyebrows
- Pure SVG generation — can be embedded in Gradio, CustomTkinter, or web pages
- Face server runs on port 8765, independent from main UI

**Known Issues:** None

**Next Task:** DOCS-002 — Initialize Project Structure & Git

---

## 6. API Contracts Summary

All modules follow these conventions:

- **Constructor:** Takes configuration; never starts I/O
- **`async def start()`:** Starts internal threads/connections
- **`async def stop()`:** Gracefully stops and cleans up
- **Context manager:** `async with Module(config) as m:` pattern
- **Errors:** Raised as exceptions, never silently swallowed
- **Callbacks:** Set as attributes before `start()`

### Inter-Module Data Types

```
AudioChunk = np.ndarray          # float32, [-1.0, 1.0], mono
AudioBuffer = np.ndarray         # float32, [-1.0, 1.0], mono, variable length
TranscriptionResult = str        # Plain text
LLMResponseStream = AsyncIterator[str]  # Token stream
TextToSynthesize = str           # Plain text
AudioResponse = np.ndarray       # float32, mono, ready for playback
CameraFrame = np.ndarray         # uint8, BGR, H×W×3
VisionContext = dict             # {"person_present": bool, "description": str}
ConfigDict = dict                # JSON-serializable key-value pairs
FaceSvg = str                    # Complete SVG markup
Emotion = str                    # "idle" | "listening" | "thinking" | "speaking" | "happy" | "sad" | "surprised" | "confused" | "sleeping"
```

---

## 7. What Agents Need to Know Before Starting

1. **Task workflow:** Every task → new branch → implement → update memory → update task → PR
2. **Read memory.md first** — it contains all context you need
3. **Read tehnika.md** — it has exact API signatures, class names, and data types
4. **Follow the coding standards** in agents.md §5
5. **Update this file** after completing your task — add decisions, blockers, and status changes
6. **Don't break existing modules** — run tests before and after your changes
7. **NexusFace is at src/ui/face.py** — use `face.render(emotion)` to get SVG strings. The face server is at `src/ui/face_server.py` on port 8765.

---

> **Last updated:** 2026-07-12  
> **Maintainer:** Documentation Agent
