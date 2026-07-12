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

**Status:** ✅ DONE

---

## Task Description

Implement a camera/vision module for the Nexus assistant so the system can capture webcam frames, process them for basic vision features, and expose a clean interface for future computer-vision use cases.

## User Story

As the Nexus assistant,
I need live camera input
so that I can perceive the environment and support future vision-based interactions.

## Acceptance Criteria

- [x] **AC-1:** `CameraCapture` or equivalent service that opens the default webcam
- [x] **AC-2:** Configurable device index, resolution, and frame rate
- [x] **AC-3:** Non-blocking frame capture in a background thread or worker
- [x] **AC-4:** Frame callback / queue API for downstream processing
- [x] **AC-5:** Graceful handling of missing or unavailable camera devices
- [x] **AC-6:** Unit tests with mocked frame sources or OpenCV stubs

## Definition of Done

- Camera module can be imported and instantiated without errors
- Frame capture can start/stop cleanly and release resources
- Tests for camera startup, shutdown, and fallback behavior pass
- PR created from `feature/camera-vision-service` into `develop`

---

**EST:** 5 SP

**RT:** 2026-07-12
**QA:** 2026-07-12

---

### Task: ARCH-004 — Speech-to-Text Engine

**Status:** ✅ DONE

---

## Task Description

Implement a local speech-to-text engine that converts microphone audio into text transcripts for the Nexus assistant pipeline.

## User Story

As the Nexus assistant,
I need reliable speech recognition
so that I can understand user requests and respond meaningfully.

## Acceptance Criteria

- [x] **AC-1:** STT service that accepts audio chunks or a live microphone stream
- [x] **AC-2:** Configurable model size and language settings
- [x] **AC-3:** Support for partial and final transcript callbacks
- [x] **AC-4:** Low-latency processing suitable for interactive use
- [x] **AC-5:** Graceful fallback when the model is unavailable or cannot load
- [x] **AC-6:** Unit tests for audio preprocessing and transcript handling

## Definition of Done

- STT can process sample audio and return structured transcript output
- The module integrates cleanly with the audio capture pipeline
- Tests for successful and failed recognition flows pass
- PR created from `feature/speech-to-text-engine` into `develop`

---

**EST:** 8 SP

**RT:** 2026-07-12
**QA:** 2026-07-12

---

### Task: ARCH-005 — Text-to-Speech Engine

**Status:** ✅ DONE

**EST:** 5 SP

---

## Task Description

Implement a text-to-speech engine that turns assistant responses into speech and sends them to the playback service.

## User Story

As the Nexus assistant,
I need a voice output pipeline
so that I can respond to the user verbally.

## Acceptance Criteria

- [x] **AC-1:** TTS service that accepts text and produces audio data
- [x] **AC-2:** Configurable voice, speed, and language settings
- [x] **AC-3:** Non-blocking synthesis path for assistant responses
- [x] **AC-4:** Output can be routed into the existing playback module
- [x] **AC-5:** Graceful handling of unsupported voices or missing model files
- [x] **AC-6:** Unit tests for synthesis request handling and fallback behavior

## Definition of Done

- TTS can generate audio from sample text input
- Output format is compatible with the playback service
- Tests for synthesis and error handling pass
- PR created from `feature/text-to-speech-engine` into `develop`

---

**EST:** 5 SP

**RT:** 2026-07-12
**QA:** 2026-07-12

---

### Task: ARCH-006 — LLM Integration

**Status:** ✅ DONE

**EST:** 5 SP

---

## Task Description

Integrate the local LLM layer so the assistant can generate replies using a configured model backend, prompt templates, and conversation context.

## User Story

As the Nexus assistant,
I need access to a language model
so that I can reason about user input and produce useful responses.

## Acceptance Criteria

- [x] **AC-1:** LLM client configurable for a local backend such as Ollama
- [x] **AC-2:** Support for system prompts and conversation history
- [x] **AC-3:** Configurable temperature, max tokens, and model selection
- [x] **AC-4:** Error handling for unavailable backend or timeouts
- [x] **AC-5:** Response streaming or asynchronous execution path
- [x] **AC-6:** Unit tests for prompt construction and backend failure cases

## Definition of Done

- The assistant can send a sample prompt and receive a structured response
- Configuration for model URL and model name is persisted in settings
- Tests for prompt flow and backend errors pass
- PR created from `feature/llm-integration` into `develop`

---

**EST:** 5 SP

**RT:** 2026-07-12
**QA:** 2026-07-12

---

### Task: ARCH-007 — Memory / Vector Store

**Status:** ✅ DONE

**EST:** 5 SP

---

## Task Description

Implement persistent memory for the assistant using a lightweight vector store or a similar retrieval layer so the system can remember prior interactions and retrieve relevant context.

## User Story

As the Nexus assistant,
I need a memory layer
so that I can recall past conversations and provide more contextual responses.

## Acceptance Criteria

- [x] **AC-1:** Memory service that stores conversation snippets or embeddings
- [x] **AC-2:** Save/load support for persistent local storage
- [x] **AC-3:** Basic retrieval by similarity or keyword search
- [x] **AC-4:** Configurable memory path and storage format
- [x] **AC-5:** Cleanup and pruning strategy for stale entries
- [x] **AC-6:** Unit tests for store, retrieve, and persistence behavior

## Definition of Done

- Memory can save and retrieve sample entries reliably
- Retrieval works with basic semantic or keyword queries
- Tests for storage and retrieval pass
- PR created from `feature/memory-vector-store` into `develop`

---

**EST:** 5 SP

**RT:** 2026-07-12
**QA:** 2026-07-12

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

**Status:** ⏳ IN PROGRESS

**EST:** 8 SP

---

## Task Description

Create the main assistant application pipeline that wires together audio capture, STT, LLM, TTS, playback, memory, and UI into one cohesive runtime flow.

## User Story

As a Nexus user,
I want the system to work end to end
so that I can speak to the assistant and receive a spoken response.

## Acceptance Criteria

- [x] **AC-1:** Bootstrapping flow for all major services
- [x] **AC-2:** Event-driven orchestration between modules
- [x] **AC-3:** Clean startup and shutdown lifecycle
- [x] **AC-4:** Configuration-driven wiring for enabled or disabled features
- [x] **AC-5:** Basic error recovery and logging across modules
- [x] **AC-6:** End-to-end smoke test for a simple request-response cycle

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

## Companion & Workhorse Roadmap

The following backlog turns the existing collection of services into a coherent assistant. The
recommended implementation order is: runtime integration, state machine, tools, task management,
structured memory, persona, evaluation, safe learning, unified UI, and packaging repair.

---

### Task: CORE-001 — Assistant Runtime State Machine

**Status:** 📋 BACKLOG

---

## Task Description

Implement the authoritative Nexus runtime state machine and event model. Runtime states must drive
the UI and face rather than being inferred independently by each component.

## User Story

As a Nexus user,
I need clear and truthful feedback about what the assistant is doing
so that listening, planning, acting, waiting, and failure states are understandable.

## Acceptance Criteria

- [ ] **AC-1:** Typed states for IDLE, LISTENING, UNDERSTANDING, PLANNING, ACTING, VERIFYING, SPEAKING, WAITING_CONFIRMATION, BLOCKED, ERROR, and SLEEPING
- [ ] **AC-2:** Validated state transitions and typed transition events
- [ ] **AC-3:** Subscriber API for UI, face, logging, and tests
- [ ] **AC-4:** Invalid transitions fail predictably without corrupting runtime state
- [ ] **AC-5:** Face emotions are mapped from authoritative runtime state
- [ ] **AC-6:** Unit tests cover normal, interrupted, blocked, and error flows

## Definition of Done

- State machine tests pass
- UI and face can consume state events without direct service coupling
- PR merged from `feature/runtime-state-machine` into `develop`

---

**EST:** 5 SP

---

### Task: TOOLS-001 — Tool Protocol, Registry & Permissions

**Status:** 📋 BACKLOG

---

## Task Description

Create a typed tool interface and registry through which Nexus can inspect and act on local
resources. Every invocation must have a risk level, permission decision, structured result, and
audit entry.

## User Story

As a Nexus user,
I need the assistant to perform useful work within explicit boundaries
so that it can act without hiding risky or destructive operations.

## Acceptance Criteria

- [ ] **AC-1:** Typed Tool, ToolRequest, ToolResult, and ToolError contracts
- [ ] **AC-2:** Registry supports discovery, validation, invocation, timeout, and cancellation
- [ ] **AC-3:** Risk classes distinguish read-only, local-write, external, and destructive actions
- [ ] **AC-4:** Permission policy requires confirmation according to configured risk level
- [ ] **AC-5:** Initial read-only filesystem and project-inspection tools are implemented
- [ ] **AC-6:** Every invocation produces a local audit record without leaking secrets

## Definition of Done

- Tool contract and permission tests pass
- A mocked end-to-end request can select, invoke, and verify a tool
- PR merged from `feature/tool-registry-permissions` into `develop`

---

**EST:** 8 SP

---

### Task: TASKS-001 — Goals, Plans & Resumable Tasks

**Status:** 📋 BACKLOG

---

## Task Description

Add persistent goals and task execution records so Nexus can plan multi-step work, report progress,
handle blockers, and resume interrupted work.

## User Story

As a Nexus user,
I need complex requests to become visible and resumable plans
so that I can trust progress and continue work across sessions.

## Acceptance Criteria

- [ ] **AC-1:** Typed goal, plan step, dependency, result, blocker, and status models
- [ ] **AC-2:** Plans support pending, active, waiting, blocked, failed, and completed states
- [ ] **AC-3:** Task state persists locally and can be resumed after restart
- [ ] **AC-4:** User can inspect, pause, cancel, or amend a plan
- [ ] **AC-5:** Completion requires evidence or explicit verification, not only an LLM claim
- [ ] **AC-6:** Tests cover interruption, recovery, cancellation, and blocked tasks

## Definition of Done

- A multi-step mocked task survives restart and resumes correctly
- Progress is available to both UI and conversational responses
- PR merged from `feature/goals-resumable-tasks` into `develop`

---

**EST:** 8 SP

---

### Task: MEM-002 — Structured Multi-Layer Memory

**Status:** 📋 BACKLOG

---

## Task Description

Evolve the current conversation-snippet store into working, episodic, semantic, preference, and
procedural memory with explicit provenance, confidence, importance, sensitivity, and retention.

## User Story

As a Nexus user,
I need the assistant to remember useful context accurately
so that it becomes more helpful without storing everything indiscriminately.

## Acceptance Criteria

- [ ] **AC-1:** Schema supports working, episodic, semantic, preference, and procedural memory types
- [ ] **AC-2:** Every memory records source, confidence, importance, sensitivity, timestamps, and scope
- [ ] **AC-3:** Memory manager decides what is promoted to long-term memory
- [ ] **AC-4:** Retrieval combines keyword and optional local embedding search behind one interface
- [ ] **AC-5:** Duplicate consolidation, contradiction handling, summaries, and retention policies are supported
- [ ] **AC-6:** Existing JSON memories migrate safely or remain readable

## Definition of Done

- Migration and retrieval tests pass
- Context builder can request only relevant memory types within a token budget
- PR merged from `feature/structured-memory` into `develop`

---

**EST:** 8 SP

---

### Task: MEM-003 — Memory Consent & Management UI

**Status:** 📋 BACKLOG

---

## Task Description

Give the user transparent control over what Nexus remembers, including inspection, correction,
deletion, export, retention, and sensitive-memory consent.

## User Story

As a privacy-conscious Nexus user,
I need to see and control the assistant's memory
so that personalization remains understandable and reversible.

## Acceptance Criteria

- [ ] **AC-1:** UI lists memories by type, scope, source, and sensitivity
- [ ] **AC-2:** User can search, edit, delete, pin, and correct individual memories
- [ ] **AC-3:** User can export or clear memory by type, project, or time range
- [ ] **AC-4:** Sensitive information follows configurable ask, allow, or never-store policy
- [ ] **AC-5:** Nexus can answer “What do you remember about me?” from actual stored data
- [ ] **AC-6:** Memory changes are audited and immediately affect retrieval

## Definition of Done

- Memory-control smoke tests pass
- Deleted memories are no longer returned by retrieval
- PR merged from `feature/memory-consent-ui` into `develop`

---

**EST:** 5 SP

---

### Task: PERSONA-001 — Persona & Interaction Modes

**Status:** 📋 BACKLOG

---

## Task Description

Create a bounded, configurable Nexus persona that stays consistent across text, voice, face, and
proactive behavior while preserving factual reliability.

## User Story

As a Nexus user,
I need a playful but adjustable companion
so that interaction feels personal without interfering with focused work.

## Acceptance Criteria

- [ ] **AC-1:** Companion, balanced, and focused interaction modes are available
- [ ] **AC-2:** Settings include playfulness, proactivity, response detail, quiet hours, and unsolicited suggestions
- [ ] **AC-3:** Persona changes expression and delivery but never lowers factual or permission standards
- [ ] **AC-4:** Structured response metadata can drive emotion, voice delivery, and confidence cues
- [ ] **AC-5:** Proactive behavior is rate-limited, interruptible, and disabled during quiet hours
- [ ] **AC-6:** Tests verify stable behavior and settings persistence

## Definition of Done

- Mode changes visibly affect style without changing task correctness
- Persona settings persist and are exposed in the settings UI
- PR merged from `feature/persona-interaction-modes` into `develop`

---

**EST:** 5 SP

---

### Task: EVAL-001 — Result Verification & Feedback

**Status:** 📋 BACKLOG

---

## Task Description

Add an evaluation layer that verifies tool outcomes, records evidence, collects user feedback, and
prevents Nexus from reporting success when required work remains incomplete.

## User Story

As a Nexus user,
I need completed work to be checked before it is reported as finished
so that the assistant is dependable rather than merely convincing.

## Acceptance Criteria

- [ ] **AC-1:** Task steps can define machine-checkable or user-confirmed success criteria
- [ ] **AC-2:** Verification results include evidence, confidence, and failure explanation
- [ ] **AC-3:** Failed verification returns work to an actionable state
- [ ] **AC-4:** User feedback supports positive, negative, and explanatory signals
- [ ] **AC-5:** Local metrics track success, corrections, latency, and memory usefulness
- [ ] **AC-6:** Tests prove that unsupported completion claims are rejected

## Definition of Done

- Mocked tasks cannot complete without satisfying their verification contract
- Evaluation records can be consumed by the learning layer
- PR merged from `feature/result-verification` into `develop`

---

**EST:** 5 SP

---

### Task: LEARN-001 — Safe Reflection & Learning Loop

**Status:** 📋 BACKLOG

---

## Task Description

Implement a local reflection loop that converts verified outcomes and user feedback into procedural
lessons and improvement proposals. Source code, security policy, permissions, and core prompts must
not be changed automatically.

## User Story

As a Nexus user,
I need the assistant to learn from successful and failed work safely
so that repeated tasks improve while I retain control over system changes.

## Acceptance Criteria

- [ ] **AC-1:** Reflection consumes task evidence and user feedback rather than model opinion alone
- [ ] **AC-2:** Lessons include scope, confidence, provenance, and measurable expected benefit
- [ ] **AC-3:** Lessons are stored as reviewable procedural memory
- [ ] **AC-4:** Conflicting or low-confidence lessons are quarantined for review
- [ ] **AC-5:** Code, prompts, permissions, and safety rules require explicit user approval to change
- [ ] **AC-6:** A local development report summarizes outcomes and proposed improvements

## Definition of Done

- A repeated mocked task can reuse an approved lesson
- No protected system artifact is modified without confirmation
- PR merged from `feature/safe-learning-loop` into `develop`

---

**EST:** 8 SP

---

### Task: UI-008 — Unified Companion Workspace

**Status:** 📋 BACKLOG

---

## Task Description

Extend the main UI into a unified workspace combining the animated face, conversation, runtime
state, active plan, tool activity, evidence, confirmations, memory controls, and settings.

## User Story

As a Nexus user,
I need one clear workspace for companionship and serious work
so that I can understand and control the assistant without switching interfaces.

## Acceptance Criteria

- [ ] **AC-1:** Face, transcript, runtime status, and current task are visible together
- [ ] **AC-2:** Plan steps, tool activity, and verification evidence update live
- [ ] **AC-3:** Permission requests are explicit and show action, scope, and risk
- [ ] **AC-4:** User can interrupt speech, cancel work, mute sensors, and open memory controls
- [ ] **AC-5:** Layout supports companion, balanced, and focused modes
- [ ] **AC-6:** Accessibility and desktop-responsive smoke tests pass

## Definition of Done

- The complete mocked assistant lifecycle is understandable from the UI
- Controls remain responsive during model, audio, and tool operations
- PR merged from `feature/unified-companion-workspace` into `develop`

---

**EST:** 8 SP

---

### Task: ARCH-010 — Package Layout & CLI Repair

**Status:** 📋 BACKLOG

---

## Task Description

Align the Python source layout, package discovery, documentation, and executable entry point. The
current packaging configuration searches for `nexus*` packages while source modules are located
directly under `src/`.

## User Story

As a Nexus maintainer,
I need a consistent installable package layout
so that development imports and distributed installations behave the same way.

## Acceptance Criteria

- [ ] **AC-1:** A documented package layout decision is made and implemented
- [ ] **AC-2:** Setuptools discovers every intended runtime package
- [ ] **AC-3:** A `nexus` CLI entry point starts the application or reports missing services clearly
- [ ] **AC-4:** Tests run against the installed package, not only the repository path
- [ ] **AC-5:** README and installation instructions match the actual layout
- [ ] **AC-6:** Clean-environment build and import smoke tests pass

## Definition of Done

- Wheel and source distribution build successfully
- Installed CLI and module imports work in a clean environment
- PR merged from `fix/package-layout-cli` into `develop`

---

**EST:** 5 SP

---

## Completed Tasks

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

---

> **Last updated:** 2026-07-12  
> **Maintainer:** Documentation Agent
