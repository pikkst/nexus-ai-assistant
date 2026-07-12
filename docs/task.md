# Nexus Local AI Assistant — Task Board

> **Version:** 1.2.0  
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

**EST:** 5 SP | **RT:** 2026-07-12 | **QA:** 2026-07-12

---

### Task: DOCS-002 — Initialize Project Structure & Git

**Status:** ✅ DONE

**EST:** 3 SP

---

### Task: UI-FACE-001 — Looi-Style Animated Face Module

**Status:** ✅ DONE

**EST:** 8 SP | **RT:** 2026-07-12 | **QA:** 2026-07-12

---

### Task: ARCH-001 — Audio Capture Service

**Status:** ✅ DONE

---

## Task Description

Implement the audio capture module (`src/audio/capture.py`) that reads microphone input. Includes voice activity detection (VAD) to detect when the user is speaking.

## User Story

As the Nexus assistant,
I need to capture audio from the microphone in real-time
so that I can process user speech for STT.

## Acceptance Criteria

- [x] **AC-1:** `AudioCapture` class that streams audio from default microphone
- [x] **AC-2:** Configurable sample rate (default 16000 Hz), chunk size, and device index
- [x] **AC-3:** Voice Activity Detection (VAD) using webrtcvad
- [x] **AC-4:** Callback-based API: `on_speech_start`, `on_speech_end`, `on_audio_chunk`
- [x] **AC-5:** Non-blocking — runs in a separate thread
- [x] **AC-6:** Proper resource cleanup (context manager)
- [x] **AC-7:** Graceful handling of missing microphone (logs warning, returns silence)
- [x] **AC-8:** Unit tests with mocked PyAudio — 17 tests passing
- [x] **AC-9:** Updated `memory.md` with implementation notes

## Definition of Done

- `pytest tests/test_audio.py -v` passes (17/17)
- Module can be imported and instantiated without errors
- PR merged from `feature/audio-capture-service` into `develop`

---

**EST:** 5 SP

**RT:** 2026-07-12
**QA:** 2026-07-12

---

### Task: ARCH-002 — Audio Playback Service

**Status:** ✅ DONE

---



## Task Description

Implement the audio playback module (`src/audio/playback.py`) that sends audio to speakers for TTS output.

## User Story

As the Nexus assistant,
I need to play audio through the speakers
so that I can respond to the user with speech.

## Acceptance Criteria

- [x] **AC-1:** `AudioPlayback` class that plays audio to default output device
- [x] **AC-2:** Supports WAV, MP3, and raw PCM formats
- [x] **AC-3:** Non-blocking playback with queue
- [x] **AC-4:** Volume control (0.0 to 1.0)
- [x] **AC-5:** Stop/ interrupt current playback
- [x] **AC-6:** Proper resource cleanup
- [x] **AC-7:** Graceful handling of missing speakers

## Definition of Done

- `pytest tests/test_audio.py` passes (playback tests)
- PR merged into `develop`

---

**EST:** 3 SP

**RT:** 2026-07-12
**QA:** 2026-07-12

---

---

### Task: ARCH-003 — Camera / Vision Service

**Status:** 📋 BACKLOG

**EST:** 5 SP

---

## Task Description

Implement a camera/vision module for the Nexus assistant so the system can capture webcam frames, process them for basic vision features, and expose a clean interface for future computer-vision use cases.

## User Story

As the Nexus assistant,
I need live camera input
so that I can perceive the environment and support future vision-based interactions.

## Acceptance Criteria

- [ ] **AC-1:** `CameraCapture` or equivalent service that opens the default webcam
- [ ] **AC-2:** Configurable device index, resolution, and frame rate
- [ ] **AC-3:** Non-blocking frame capture in a background thread or worker
- [ ] **AC-4:** Frame callback / queue API for downstream processing
- [ ] **AC-5:** Graceful handling of missing or unavailable camera devices
- [ ] **AC-6:** Unit tests with mocked frame sources or OpenCV stubs

## Definition of Done

- Camera module can be imported and instantiated without errors
- Frame capture can start/stop cleanly and release resources
- Tests for camera startup, shutdown, and fallback behavior pass
- PR created from `feature/camera-vision-service` into `develop`

---

**EST:** 5 SP

---

### Task: ARCH-004 — Speech-to-Text Engine

**Status:** 📋 BACKLOG

**EST:** 8 SP

---

## Task Description

Implement a local speech-to-text engine that converts microphone audio into text transcripts for the Nexus assistant pipeline.

## User Story

As the Nexus assistant,
I need reliable speech recognition
so that I can understand user requests and respond meaningfully.

## Acceptance Criteria

- [ ] **AC-1:** STT service that accepts audio chunks or a live microphone stream
- [ ] **AC-2:** Configurable model size and language settings
- [ ] **AC-3:** Support for partial and final transcript callbacks
- [ ] **AC-4:** Low-latency processing suitable for interactive use
- [ ] **AC-5:** Graceful fallback when the model is unavailable or cannot load
- [ ] **AC-6:** Unit tests for audio preprocessing and transcript handling

## Definition of Done

- STT can process sample audio and return structured transcript output
- The module integrates cleanly with the audio capture pipeline
- Tests for successful and failed recognition flows pass
- PR created from `feature/speech-to-text-engine` into `develop`

---

**EST:** 8 SP

---

### Task: ARCH-005 — Text-to-Speech Engine

**Status:** 📋 BACKLOG

**EST:** 5 SP

---

## Task Description

Implement a text-to-speech engine that turns assistant responses into speech and sends them to the playback service.

## User Story

As the Nexus assistant,
I need a voice output pipeline
so that I can respond to the user verbally.

## Acceptance Criteria

- [ ] **AC-1:** TTS service that accepts text and produces audio data
- [ ] **AC-2:** Configurable voice, speed, and language settings
- [ ] **AC-3:** Non-blocking synthesis path for assistant responses
- [ ] **AC-4:** Output can be routed into the existing playback module
- [ ] **AC-5:** Graceful handling of unsupported voices or missing model files
- [ ] **AC-6:** Unit tests for synthesis request handling and fallback behavior

## Definition of Done

- TTS can generate audio from sample text input
- Output format is compatible with the playback service
- Tests for synthesis and error handling pass
- PR created from `feature/text-to-speech-engine` into `develop`

---

**EST:** 5 SP

---

### Task: ARCH-006 — LLM Integration

**Status:** 📋 BACKLOG

**EST:** 5 SP

---

## Task Description

Integrate the local LLM layer so the assistant can generate replies using a configured model backend, prompt templates, and conversation context.

## User Story

As the Nexus assistant,
I need access to a language model
so that I can reason about user input and produce useful responses.

## Acceptance Criteria

- [ ] **AC-1:** LLM client configurable for a local backend such as Ollama
- [ ] **AC-2:** Support for system prompts and conversation history
- [ ] **AC-3:** Configurable temperature, max tokens, and model selection
- [ ] **AC-4:** Error handling for unavailable backend or timeouts
- [ ] **AC-5:** Response streaming or asynchronous execution path
- [ ] **AC-6:** Unit tests for prompt construction and backend failure cases

## Definition of Done

- The assistant can send a sample prompt and receive a structured response
- Configuration for model URL and model name is persisted in settings
- Tests for prompt flow and backend errors pass
- PR created from `feature/llm-integration` into `develop`

---

**EST:** 5 SP

---

### Task: ARCH-007 — Memory / Vector Store

**Status:** 📋 BACKLOG

**EST:** 5 SP

---

## Task Description

Implement persistent memory for the assistant using a lightweight vector store or a similar retrieval layer so the system can remember prior interactions and retrieve relevant context.

## User Story

As the Nexus assistant,
I need a memory layer
so that I can recall past conversations and provide more contextual responses.

## Acceptance Criteria

- [ ] **AC-1:** Memory service that stores conversation snippets or embeddings
- [ ] **AC-2:** Save/load support for persistent local storage
- [ ] **AC-3:** Basic retrieval by similarity or keyword search
- [ ] **AC-4:** Configurable memory path and storage format
- [ ] **AC-5:** Cleanup and pruning strategy for stale entries
- [ ] **AC-6:** Unit tests for store, retrieve, and persistence behavior

## Definition of Done

- Memory can save and retrieve sample entries reliably
- Retrieval works with basic semantic or keyword queries
- Tests for storage and retrieval pass
- PR created from `feature/memory-vector-store` into `develop`

---

**EST:** 5 SP

---

### Task: ARCH-008 — User Interface

**Status:** 📋 BACKLOG

**EST:** 8 SP

---

## Task Description

Build the main Nexus user interface so the assistant can display the animated face, conversation transcript, controls, and settings in a single coherent experience.

## User Story

As a Nexus user,
I want a simple interactive interface
so that I can see the assistant’s state and interact with it intuitively.

## Acceptance Criteria

- [ ] **AC-1:** Main window or web UI shell with a face area and conversation view
- [ ] **AC-2:** Controls for start/stop, mute, and settings access
- [ ] **AC-3:** Live status indicators for listening, speaking, and thinking
- [ ] **AC-4:** Integration with the existing face demo and settings panel
- [ ] **AC-5:** Responsive layout suitable for desktop use
- [ ] **AC-6:** Unit or smoke tests for UI bootstrap and layout wiring

## Definition of Done

- The UI can launch successfully and render the core panels
- Settings and face modules are accessible from the main experience
- Smoke tests for startup and basic interactions pass
- PR created from `feature/main-ui` into `develop`

---

**EST:** 8 SP

---

### Task: INTEGRATION-001 — Main Application & Pipeline

**Status:** 📋 BACKLOG

**EST:** 8 SP

---

## Task Description

Create the main assistant application pipeline that wires together audio capture, STT, LLM, TTS, playback, memory, and UI into one cohesive runtime flow.

## User Story

As a Nexus user,
I want the system to work end to end
so that I can speak to the assistant and receive a spoken response.

## Acceptance Criteria

- [ ] **AC-1:** Bootstrapping flow for all major services
- [ ] **AC-2:** Event-driven orchestration between modules
- [ ] **AC-3:** Clean startup and shutdown lifecycle
- [ ] **AC-4:** Configuration-driven wiring for enabled or disabled features
- [ ] **AC-5:** Basic error recovery and logging across modules
- [ ] **AC-6:** End-to-end smoke test for a simple request-response cycle

## Definition of Done

- The application can start, process a sample request, and respond end to end
- Major modules are connected through a single orchestration layer
- Smoke tests for startup and basic pipeline flow pass
- PR created from `feature/main-app-pipeline` into `develop`

---

**EST:** 8 SP

---

### Task: OPS-001 — Packaging & Distribution

**Status:** 📋 BACKLOG

**EST:** 5 SP

---

## Task Description

Package the Nexus assistant for local installation and distribution so it can be installed, launched, and updated consistently across machines.

## User Story

As a Nexus maintainer,
I need a reliable installable package
so that the assistant can be distributed and run easily.

## Acceptance Criteria

- [ ] **AC-1:** Packaging configuration for Python install and execution
- [ ] **AC-2:** CLI entry point for launching the assistant
- [ ] **AC-3:** Clear installation and startup instructions in documentation
- [ ] **AC-4:** Build artifacts that can be created from the repository
- [ ] **AC-5:** Basic packaging smoke test in a clean environment
- [ ] **AC-6:** Versioned release workflow for future updates

## Definition of Done

- The project can be installed from source with a documented command
- A build or install smoke test succeeds in a clean environment
- Documentation reflects the packaging process
- PR created from `feature/packaging-distribution` into `develop`

---

**EST:** 5 SP

---

### Task: ARCH-009 — UI Settings Panel

**Status:** ✅ DONE

---



## Task Description

Implement a settings panel for the Nexus UI allowing users to configure audio devices, volume, TTS voice, and language.

## User Story

As a Nexus user,
I want to adjust audio settings, voice, and language from the UI
so that I can personalize my experience.

## Acceptance Criteria

- [x] **AC-1:** Settings window with audio section (volume slider, sample rate, device selection)
- [x] **AC-2:** TTS voice/tone selection
- [x] **AC-3:** Language selection (et/en)
- [x] **AC-4:** Persist settings to `~/.nexus/config.json`
- [x] **AC-5:** Load settings on startup

## Definition of Done

- `pytest tests/test_settings.py` passes
- Settings window opens and saves correctly

---

**EST:** 3 SP

**RT:** 2026-07-12
**QA:** 2026-07-12

---

## Completed Tasks

| Task ID | Name | Completed | By |
|---------|------|-----------|----|
| DOCS-001 | Create Project Documentation Foundation | 2026-07-12 | Documentation Agent |
| DOCS-002 | Initialize Project Structure & Git | 2026-07-12 | Documentation Agent |
| UI-FACE-001 | Looi-Style Animated Face Module | 2026-07-12 | Documentation Agent |
| ARCH-001 | Audio Capture Service | 2026-07-12 | Backend Agent |
| ARCH-002 | Audio Playback Service | 2026-07-12 | Backend Agent |
| ARCH-009 | UI Settings Panel | 2026-07-12 | Backend Agent |

---

> **Last updated:** 2026-07-12  
> **Maintainer:** Documentation Agent
