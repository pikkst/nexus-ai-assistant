# Nexus Local AI Assistant — Task Board

> **Version:** 1.1.0  
> **Purpose:** Central task management for all agents. Every task follows the defined format. Each task = new branch, new PR.

---

## Task Lifecycle Rule

**Every agent MUST follow this sequence for every task:**

1. **New branch** — `git checkout -b feature/task-description` from `develop`
2. **Read** `memory.md` and `task.md` to understand current state
3. **Implement** the task
4. **Update** `memory.md` with decisions, blockers, and progress
5. **Update** `task.md` — mark completed tasks, add new discoveries
6. **Create PR** — with description linking back to this task
7. **Merge** only after all AC met and tests pass

---

## Task List

---

### Task: DOCS-001 — Create Project Documentation Foundation

**Status:** ✅ DONE

---

## Task Description

Create the foundational documentation structure for the Nexus Local AI Assistant project.

## User Story

As an AI agent working on the Nexus project,
I need complete, well-structured documentation
so that I can understand the project goals, architecture, workflows, and current state without asking for human clarification.

## Acceptance Criteria

- [x] **AC-1:** `agents.md` exists and defines agent roles, responsibilities, workflows, branch strategy, and coding standards
- [x] **AC-2:** `task.md` exists with at least the initial setup task documented in the required format
- [x] **AC-3:** `tehnika.md` exists with full technical architecture, component descriptions, data flow diagrams (ascii), and technology justification
- [x] **AC-4:** `memory.md` exists with project state, decisions log, blocker history, and "what we know so far"
- [x] **AC-5:** `rules.md` exists with branch rules, PR rules, memory update rules, and file change protocol
- [x] **AC-6:** All documents are written in English
- [x] **AC-7:** Each document has version number and last-updated date

## Definition of Done

- All Acceptance Criteria are met
- All documents are saved to `docs/` directory
- An agent reading all four documents can start implementing code without human guidance

---

**EST:** 5 SP

**RT:** 2026-07-12
**QA:** 2026-07-12

---

### Task: DOCS-002 — Initialize Project Structure & Git

**Status:** ❌ NOT STARTED

---

## Task Description

Initialize the Git repository, create the project directory structure with placeholder files, set up Python virtual environment, and create the initial `requirements.txt` and `pyproject.toml`.

## User Story

As a backend agent,
I need the project scaffold, version control, and dependency management set up
so that I can start implementing features immediately.

## Acceptance Criteria

- [ ] **AC-1:** Git repository initialized with `main` and `develop` branches
- [ ] **AC-2:** Directory structure matches `agents.md` §5.2 (all folders created with `__init__.py` placeholders)
- [ ] **AC-3:** Python virtual environment (`.venv`) created
- [ ] **AC-4:** `requirements.txt` with pinned dependencies
- [ ] **AC-5:** `pyproject.toml` with project metadata, build config, and tool settings
- [ ] **AC-6:** `.gitignore` exists
- [ ] **AC-7:** Initial commit on `develop` with all scaffold files

## Definition of Done

- `git log` shows initial commit on `develop`
- `python -m venv .venv` works
- All placeholder modules are importable

---

**EST:** 3 SP

**RT:**
**QA:**

---

### Task: UI-FACE-001 — Looi-Style Animated Face Module

**Status:** ✅ DONE

---

## Task Description

Create a Looi-style animated face for the Nexus assistant. The face must have large anime-style eyes that are expressive and show emotions: idle, listening, thinking, speaking, happy, sad, surprised, confused, sleeping. Must be pure SVG generation with zero external dependencies.

## User Story

As a user,
I want Nexus to have a cute animated face like the Looi toy
so that the assistant feels alive, approachable, and communicates its state visually.

## Acceptance Criteria

- [x] **AC-1:** `src/ui/face.py` exists with `NexusFace` class
- [x] **AC-2:** Supports 9 emotions: idle, listening, thinking, speaking, happy, sad, surprised, confused, sleeping
- [x] **AC-3:** SVG generation — zero external dependencies
- [x] **AC-4:** Animation system with blink cycle, gaze jitter, mouth movement
- [x] **AC-5:** `render(emotion)` returns full SVG string
- [x] **AC-6:** `animate(dt)` advances state and returns next frame
- [x] **AC-7:** FaceConfig dataclass for customization
- [x] **AC-8:** `generate_emotion_grid()` and `generate_animated_demo()` HTML helpers
- [x] **AC-9:** `src/ui/face_server.py` HTTP API server (port 8765) for serving SVGs and demo HTML
- [x] **AC-10:** Running `python src/ui/face.py` generates the demo HTML files
- [x] **AC-11:** `docs/nexus_face_preview.svg` exists showing the design

## Definition of Done

- `python src/ui/face.py` runs without errors and produces HTML files
- `python -c "from nexus.ui.face import NexusFace; f=NexusFace(); print(f.render('happy'))"` works
- Emotion grid HTML shows all 9 emotions correctly
- Face server starts on port 8765

---

**EST:** 8 SP

**RT:** 2026-07-12
**QA:** 2026-07-12

---

### Task: ARCH-001 — Audio Capture Service

**Status:** 📋 BACKLOG

---

## Task Description

Implement the audio capture module (`src/audio/capture.py`) that reads microphone input. Includes voice activity detection (VAD) to detect when the user is speaking.

## User Story

As the Nexus assistant,
I need to capture audio from the microphone in real-time
so that I can process user speech for STT.

## Acceptance Criteria

- [ ] **AC-1:** `AudioCapture` class that streams audio from default microphone
- [ ] **AC-2:** Configurable sample rate (default 16000 Hz), chunk size, and device index
- [ ] **AC-3:** Voice Activity Detection (VAD) using webrtcvad or silero-vad
- [ ] **AC-4:** Callback-based API: `on_speech_start`, `on_speech_end`, `on_audio_chunk`
- [ ] **AC-5:** Non-blocking — runs in a separate thread
- [ ] **AC-6:** Proper resource cleanup (context manager)
- [ ] **AC-7:** Graceful handling of missing microphone (logs warning, returns silence)
- [ ] **AC-8:** Unit tests with mocked PyAudio
- [ ] **AC-9:** Updated `memory.md` with implementation notes

## Definition of Done

- `pytest tests/test_audio.py` passes
- Module can be imported and instantiated without errors
- PR merged into `develop`

---

**EST:** 5 SP

**RT:**
**QA:**

---

### Task: ARCH-002 — Audio Playback Service

**Status:** 📋 BACKLOG

---

## Task Description

Implement the audio playback module (`src/audio/playback.py`) that sends audio to speakers for TTS output.

## User Story

As the Nexus assistant,
I need to play audio through the speakers
so that I can respond to the user with speech.

## Acceptance Criteria

- [ ] **AC-1:** `AudioPlayback` class that plays audio to default output device
- [ ] **AC-2:** Supports WAV, MP3, and raw PCM formats
- [ ] **AC-3:** Non-blocking playback with queue
- [ ] **AC-4:** Volume control (0.0 to 1.0)
- [ ] **AC-5:** Stop/ interrupt current playback
- [ ] **AC-6:** Proper resource cleanup
- [ ] **AC-7:** Graceful handling of missing speakers

## Definition of Done

- `pytest tests/test_audio.py` passes (playback tests)
- PR merged into `develop`

---

**EST:** 3 SP

**RT:**
**QA:**

---

### Task: ARCH-003 — Camera / Vision Service

**Status:** 📋 BACKLOG

---

## Task Description

Implement the camera capture module (`src/vision/camera.py`) and basic frame processing (`src/vision/processor.py`).

## User Story

As the Nexus assistant,
I need to see through the computer's camera
so that I can detect user presence and provide context-aware responses.

## Acceptance Criteria

- [ ] **AC-1:** `CameraCapture` class that streams frames from the default camera
- [ ] **AC-2:** Configurable resolution, FPS, and camera index
- [ ] **AC-3:** Non-blocking frame capture in separate thread
- [ ] **AC-4:** `FrameProcessor` base class with extensible pipeline
- [ ] **AC-5:** Presence detection (is there a person in frame?)
- [ ] **AC-6:** Proper resource cleanup (release camera on exit)
- [ ] **AC-7:** Graceful handling of missing camera
- [ ] **AC-8:** Unit tests with mocked OpenCV

## Definition of Done

- `pytest tests/test_vision.py` passes
- PR merged into `develop`

---

**EST:** 5 SP

**RT:**
**QA:**

---

### Task: ARCH-004 — Speech-to-Text Engine

**Status:** 📋 BACKLOG

---

## Task Description

Implement the Speech-to-Text module (`src/stt/engine.py`) using faster-whisper for offline transcription.

## User Story

As the Nexus assistant,
I need to convert user speech to text
so that I can understand and process user commands.

## Acceptance Criteria

- [ ] **AC-1:** `STTEngine` class wrapping faster-whisper
- [ ] **AC-2:** Supports Estonian and English language detection
- [ ] **AC-3:** Configurable model size (tiny, base, small, medium, large)
- [ ] **AC-4:** Real-time transcription with VAD integration
- [ ] **AC-5:** Returns transcription with confidence score
- [ ] **AC-6:** Model downloaded once, cached locally
- [ ] **AC-7:** Async API: `await engine.transcribe(audio_chunk)`
- [ ] **AC-8:** Graceful fallback if model not available

## Definition of Done

- `pytest tests/test_stt.py` passes
- Can transcribe a sample audio file
- PR merged into `develop`

---

**EST:** 8 SP

**RT:**
**QA:**

---

### Task: ARCH-005 — Text-to-Speech Engine

**Status:** 📋 BACKLOG

---

## Task Description

Implement the Text-to-Speech module (`src/tts/engine.py`) using Piper TTS or edge-tts for offline speech synthesis.

## User Story

As the Nexus assistant,
I need to convert text responses to speech
so that I can speak back to the user.

## Acceptance Criteria

- [ ] **AC-1:** `TTSEngine` class that converts text to audio
- [ ] **AC-2:** Supports Estonian and English voices
- [ ] **AC-3:** Configurable voice, speed, and pitch
- [ ] **AC-4:** Returns audio data as numpy array (for direct playback)
- [ ] **AC-5:** Async API: `await engine.speak(text)`
- [ ] **AC-6:** Voice model downloaded once, cached locally
- [ ] **AC-7:** Sentence chunking for long texts
- [ ] **AC-8:** Graceful fallback if voice model not available

## Definition of Done

- `pytest tests/test_tts.py` passes
- Can synthesize a sample phrase to audio file
- PR merged into `develop`

---

**EST:** 5 SP

**RT:**
**QA:**

---

### Task: ARCH-006 — LLM Integration

**Status:** 📋 BACKLOG

---

## Task Description

Implement the LLM client module (`src/llm/client.py`) that connects to a local Ollama instance or llama.cpp server for inference.

## User Story

As the Nexus assistant,
I need a local language model to process user queries
so that I can generate intelligent, context-aware responses without internet.

## Acceptance Criteria

- [ ] **AC-1:** `LLMClient` class that communicates with Ollama API
- [ ] **AC-2:** Supports model switching (llama3, mistral, phi3, etc.)
- [ ] **AC-3:** Streaming response: `async for chunk in client.generate(prompt)`
- [ ] **AC-4:** System prompt injection for assistant persona
- [ ] **AC-5:** Context window management (conversation history)
- [ ] **AC-6:** Temperature, top_p, max_tokens configuration
- [ ] **AC-7:** Health check: `await client.is_ready()` returns True/False
- [ ] **AC-8:** Graceful handling if Ollama is not running
- [ ] **AC-9:** Prompt templates in `src/llm/prompts.py`

## Definition of Done

- `pytest tests/test_llm.py` passes
- Can generate a response from a local model
- PR merged into `develop`

---

**EST:** 5 SP

**RT:**
**QA:**

---

### Task: ARCH-007 — Memory / Vector Store

**Status:** 📋 BACKLOG

---

## Task Description

Implement the memory module (`src/memory/store.py`) that stores conversation history and user preferences in ChromaDB for long-term recall.

## User Story

As the Nexus assistant,
I need persistent memory across sessions
so that I can remember user preferences, past conversations, and learned information.

## Acceptance Criteria

- [ ] **AC-1:** `MemoryStore` class wrapping ChromaDB
- [ ] **AC-2:** Store and retrieve conversation history
- [ ] **AC-3:** Semantic search over past conversations
- [ ] **AC-4:** User preference storage
- [ ] **AC-5:** Configurable storage path (default `~/.nexus/memory/`)
- [ ] **AC-6:** Auto-compaction / cleanup of old entries
- [ ] **AC-7:** Async API
- [ ] **AC-8:** Graceful handling if ChromaDB fails to initialize

## Definition of Done

- `pytest tests/test_memory.py` passes
- Can store and retrieve a document
- PR merged into `develop`

---

**EST:** 5 SP

**RT:**
**QA:**

---

### Task: ARCH-008 — User Interface

**Status:** 📋 BACKLOG

---

## Task Description

Build the user interface (`src/ui/app.py`) for Nexus — either a Gradio web UI or CustomTkinter desktop application.

## User Story

As a user,
I need a visual interface for Nexus
so that I can see transcription, adjust settings, and interact with the assistant.

## Acceptance Criteria

- [ ] **AC-1:** Main window with assistant face (NexusFace) and status indicator
- [ ] **AC-2:** Real-time transcription display
- [ ] **AC-3:** Conversation history panel
- [ ] **AC-4:** Settings panel (mic device, camera device, model selection, voice selection)
- [ ] **AC-5:** Start/Stop listening button
- [ ] **AC-6:** System tray icon with quick actions
- [ ] **AC-7:** Permission request dialogs (camera, mic)
- [ ] **AC-8:** Dark theme by default

## Definition of Done

- UI launches with NexusFace as the main visual element
- All controls function correctly
- PR merged into `develop`

---

**EST:** 8 SP

**RT:**
**QA:**

---

### Task: INTEGRATION-001 — Main Application & Pipeline

**Status:** 📋 BACKLOG

---

## Task Description

Create the main application entry point (`src/main.py`) that wires together all services into a coherent voice-to-voice pipeline.

## User Story

As the Nexus assistant,
I need all modules connected in a single application
so that I can listen → think → speak in a continuous loop.

## Acceptance Criteria

- [ ] **AC-1:** `main.py` initializes all services on startup
- [ ] **AC-2:** Audio pipeline: mic → VAD → STT → LLM → TTS → speaker
- [ ] **AC-3:** Face pipeline: emotion state updates based on current activity
- [ ] **AC-4:** Vision pipeline: camera → processor → context injection
- [ ] **AC-5:** Memory integration: every conversation saved, context loaded
- [ ] **AC-6:** Graceful shutdown on Ctrl+C or window close
- [ ] **AC-7:** Comprehensive logging (loguru)
- [ ] **AC-8:** Error recovery (if a service fails, log and retry)

## Definition of Done

- Full pipeline works: speak into mic → hear response from speakers
- Face shows correct emotion for each pipeline stage
- PR merged into `develop`

---

**EST:** 8 SP

**RT:**
**QA:**

---

### Task: OPS-001 — Packaging & Distribution

**Status:** 📋 BACKLOG

---

## Task Description

Package Nexus as a standalone executable using PyInstaller and create installer for Windows.

## User Story

As an end user,
I want to download and run Nexus without installing Python or dependencies
so that I can use the assistant immediately.

## Acceptance Criteria

- [ ] **AC-1:** `pyinstaller nexus.spec` produces a single `.exe` or folder
- [ ] **AC-2:** All dependencies bundled (models excluded, downloaded on first run)
- [ ] **AC-3:** `scripts/build.bat` for Windows
- [ ] **AC-4:** Auto-update mechanism or version check
- [ ] **AC-5:** Installer created (Inno Setup or NSIS)

## Definition of Done

- Fresh Windows machine can run Nexus from the packaged build
- PR merged into `main`

---

**EST:** 5 SP

**RT:**
**QA:**

---

## Completed Tasks

| Task ID | Name | Completed | By |
|---------|------|-----------|----|
| DOCS-001 | Create Project Documentation Foundation | 2026-07-12 | Documentation Agent |
| UI-FACE-001 | Looi-Style Animated Face Module | 2026-07-12 | Documentation Agent |

---

> **Last updated:** 2026-07-12  
> **Maintainer:** Documentation Agent
