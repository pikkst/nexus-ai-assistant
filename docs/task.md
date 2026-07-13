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

**Status:** ✅ DONE

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

**Status:** ✅ DONE

---

## Task Description

Implement the authoritative Nexus runtime state machine and event model. Runtime states must drive
the UI and face rather than being inferred independently by each component.

## User Story

As a Nexus user,
I need clear and truthful feedback about what the assistant is doing
so that listening, planning, acting, waiting, and failure states are understandable.

## Acceptance Criteria

- [x] **AC-1:** Typed states for IDLE, LISTENING, UNDERSTANDING, PLANNING, ACTING, VERIFYING, SPEAKING, WAITING_CONFIRMATION, BLOCKED, ERROR, and SLEEPING
- [x] **AC-2:** Validated state transitions and typed transition events
- [x] **AC-3:** Subscriber API for UI, face, logging, and tests
- [x] **AC-4:** Invalid transitions fail predictably without corrupting runtime state
- [x] **AC-5:** Face emotions are mapped from authoritative runtime state
- [x] **AC-6:** Unit tests cover normal, interrupted, blocked, and error flows

## Definition of Done

- State machine tests pass
- UI and face can consume state events without direct service coupling
- PR merged from `feature/runtime-state-machine` into `develop`

---

**EST:** 5 SP

---

### Task: TOOLS-001 — Tool Protocol, Registry & Permissions

**Status:** ✅ DONE

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

- [x] **AC-1:** Typed Tool, ToolRequest, ToolResult, and ToolError contracts
- [x] **AC-2:** Registry supports discovery, validation, invocation, timeout, and cancellation
- [x] **AC-3:** Risk classes distinguish read-only, local-write, external, and destructive actions
- [x] **AC-4:** Permission policy requires confirmation according to configured risk level
- [x] **AC-5:** Initial read-only filesystem and project-inspection tools are implemented
- [x] **AC-6:** Every invocation produces a local audit record without leaking secrets

## Definition of Done

- Tool contract and permission tests pass
- A mocked end-to-end request can select, invoke, and verify a tool
- PR merged from `feature/tool-registry-permissions` into `develop`

---

**EST:** 8 SP

---

### Task: TOOLS-002 — LLM Tool Selection & Calling

**Status:** ⏳ IN PROGRESS

---

## Task Description

Expose registered tool schemas to the local LLM and implement a controlled loop that parses tool
calls, invokes the registry, returns structured results to the model, and prevents unbounded calls.

## User Story

As a Nexus user,
I need the assistant to select appropriate available tools
so that natural-language requests can become safe, concrete actions.

## Acceptance Criteria

- [x] **AC-1:** Tool descriptors expose validated JSON-compatible argument schemas
- [x] **AC-2:** LLM responses can request a tool through a typed structured call
- [x] **AC-3:** Requested tools and arguments are validated exclusively by ToolRegistry
- [x] **AC-4:** Confirmation-required results pause and resume the tool-calling loop
- [x] **AC-5:** Per-request call count, timeout, cancellation, and loop-detection limits are enforced
- [x] **AC-6:** Mocked end-to-end tests cover selection, result injection, rejection, and recovery

## Definition of Done

- A natural-language mocked request selects and invokes the expected registered tool
- The model cannot bypass registry permissions or invent executable tool names
- PR merged from `feature/llm-tool-calling` into `develop`

---

**EST:** 8 SP

---

### Task: TOOLS-003 — Local Development Toolset

**Status:** 🔀 IN REVIEW

---

## Task Description

Add permissioned local tools for file search, patch-based editing, terminal commands, tests, builds,
and Git inspection so Nexus can create and maintain software projects inside configured roots.

## User Story

As a Nexus user,
I need the assistant to inspect, edit, test, and verify local projects
so that it can perform useful programming work without unrestricted system access.

## Acceptance Criteria

- [x] **AC-1:** File search, text creation, and patch-based editing tools are sandboxed to project roots
- [x] **AC-2:** Terminal commands use argument arrays, allowlists, timeouts, output limits, and cancellation
- [x] **AC-3:** Test, lint, build, Git status, and Git diff tools return structured evidence
- [x] **AC-4:** Local writes require policy approval and destructive commands are denied by default
- [x] **AC-5:** Atomic writes and pre-change snapshots support recovery from failed edits
- [x] **AC-6:** Tests cover traversal, injection, symlinks, large output, rollback, and missing executables

## Definition of Done

- Nexus can patch a sample project and verify it with tests in a sandbox
- No tool can write outside the explicitly configured workspace
- PR merged from `feature/local-development-tools` into `develop`

---

**EST:** 13 SP

---

### Task: WEB-001 — Web Research & Source Management

**Status:** 🔀 IN REVIEW

---

## Task Description

Implement permissioned web search, page retrieval, content extraction, source comparison, citation,
and research-note tools with transparent provenance and bounded downloads.

## User Story

As a Nexus user,
I need current internet research with visible sources
so that information gathering is useful, verifiable, and organized.

## Acceptance Criteria

- [x] **AC-1:** Search and page-open tools use configurable provider adapters
- [x] **AC-2:** Results retain URL, title, publication date, retrieval time, and source type
- [x] **AC-3:** Robots, content size, timeout, redirect, and supported-format limits are enforced
- [x] **AC-4:** Multiple sources can be compared and cited without fabricating attribution
- [x] **AC-5:** Research notes can be saved locally only through permissioned write tools
- [x] **AC-6:** Tests use mocked providers and cover unsafe URLs, failures, duplicates, and citations

## Definition of Done

- A mocked research request produces a cited multi-source summary
- External access is explicit, auditable, cancellable, and provider-independent
- PR merged from `feature/web-research-tools` into `develop`

---

**EST:** 8 SP

---

### Task: CONNECTOR-001 — Credential Vault & OAuth Foundation

**Status:** 🔀 IN REVIEW

---

## Task Description

Build the shared authentication foundation for external connectors using OAuth where available and
OS-backed secret storage. Tokens must never enter prompts, ordinary configuration, or audit logs.

## User Story

As a Nexus user,
I need external accounts connected securely and revocably
so that Nexus can use approved services without exposing credentials.

## Acceptance Criteria

- [x] **AC-1:** Provider-neutral account, scope, token-state, and consent models are defined
- [x] **AC-2:** Secrets use Windows Credential Manager or another supported OS keyring
- [x] **AC-3:** OAuth authorization, refresh, expiry, revocation, and reconnect flows are supported
- [x] **AC-4:** Connector scopes are minimized and visible to the user before authorization
- [x] **AC-5:** Tokens are redacted from logs, exceptions, tool arguments, memory, and LLM context
- [x] **AC-6:** Tests cover refresh, revocation, missing keyring, redaction, and concurrent access

## Definition of Done

- A mocked OAuth provider can connect, refresh, revoke, and reconnect safely
- Security review confirms that credentials are never persisted as plain JSON
- PR merged from `feature/connector-credential-vault` into `develop`

---

**EST:** 8 SP

---

### Task: CONNECTOR-002 — Gmail Tools

**Status:** ✅ DONE

---

## Task Description

Add Gmail tools for searching and reading messages, composing drafts, replying, labeling, archiving,
and sending mail through the credential vault and permission system.

## User Story

As a Nexus user,
I need help organizing and writing email
so that routine correspondence is faster while I control every external action.

## Acceptance Criteria

- [x] **AC-1:** Search, read, thread-summary, and attachment-metadata tools are read-only
- [x] **AC-2:** Draft creation and editing are distinct from message sending
- [x] **AC-3:** Send, reply, label, archive, and delete actions use appropriate risk and confirmation levels
- [x] **AC-4:** Recipients, subject, body, attachment limits, and message identifiers are validated
- [x] **AC-5:** Message bodies and addresses are not copied into audit logs or long-term memory by default
- [x] **AC-6:** Mocked Gmail API tests cover pagination, drafts, confirmation, failures, and duplicate sends

## Definition of Done

- Nexus can find an email, prepare a reply draft, and send only after explicit confirmation
- Required Gmail scopes and account-disconnect instructions are documented
- PR merged from `feature/gmail-tools` into `develop`

---

**EST:** 8 SP

**RT:** 2026-07-13
**QA:** 2026-07-13

---

### Task: CONNECTOR-003 — Google Calendar Tools

**Status:** ✅ DONE

---

## Task Description

Add Google Calendar tools for listing schedules, finding free time, preparing event drafts, and
creating, updating, or deleting confirmed events.

## User Story

As a Nexus user,
I need the assistant to understand and manage my calendar
so that scheduling becomes faster without accidental invitations or deletions.

## Acceptance Criteria

- [x] **AC-1:** Calendar, event, attendee, recurrence, timezone, and free/busy models are typed
- [x] **AC-2:** Listing events and finding free time are read-only operations
- [x] **AC-3:** Event drafts show timezone, attendees, reminders, and conflicts before creation
- [x] **AC-4:** Create, update, invite, and delete operations require risk-appropriate confirmation
- [x] **AC-5:** Idempotency prevents duplicate events after retry or resumed tasks
- [x] **AC-6:** Mocked API tests cover pagination, DST, conflicts, recurrence, cancellation, and errors

## Definition of Done

- Nexus can propose a conflict-free event and create it only after user confirmation
- Calendar scopes, privacy behavior, and account revocation are documented
- PR merged from `feature/google-calendar-tools` into `develop`

---

**EST:** 8 SP

**RT:** 2026-07-13
**QA:** 2026-07-13

---

### Task: CONNECTOR-004 — Telegram Tools

**Status:** ✅ DONE

---

## Task Description

Implement Telegram messaging through a provider abstraction, beginning with the official Bot API.
Keep bot identity separate from any future user-account integration.

## User Story

As a Nexus user,
I need approved Telegram conversations and notifications available as tools
so that Nexus can assist with messaging without impersonating my personal account.

## Acceptance Criteria

- [ ] **AC-1:** Bot identity, chat, message, attachment, and update models are typed
- [ ] **AC-2:** Listing authorized chats and reading received bot updates are read-only
- [ ] **AC-3:** Drafting is separated from sending messages and attachments
- [ ] **AC-4:** Sending requires confirmation and an allowlisted chat or recipient
- [ ] **AC-5:** Rate limits, retries, duplicate-update handling, and attachment limits are enforced
- [ ] **AC-6:** Mocked Bot API tests cover authorization, polling, sending, failures, and redaction

## Definition of Done

- Nexus can read a mocked bot update and send a confirmed response to an authorized chat
- Personal-account automation remains explicitly out of scope until separately reviewed
- PR merged from `feature/telegram-tools` into `develop`

---

**EST:** 8 SP

---

### Task: CONNECTOR-005 — LinkedIn Assisted Workflow

**Status:** ✅ DONE

---

## Task Description

Provide a terms-aware LinkedIn assistance workflow focused on profile analysis, post and message
drafting, and user-reviewed handoff. Automated account actions require an approved official API.

## User Story

As a Nexus user,
I need help improving LinkedIn content and correspondence
so that I can work efficiently without unsafe automation or account-policy violations.

## Acceptance Criteria

- [x] **AC-1:** Profile, post, message, and company content can be imported or entered for local analysis
- [x] **AC-2:** Nexus can create editable post, profile, and response drafts without publishing them
- [x] **AC-3:** Official API capability and granted scopes are detected before offering account actions
- [x] **AC-4:** Scraping, mass outreach, and hidden browser automation are denied by default
- [x] **AC-5:** Any supported publish or message action requires preview and explicit confirmation
- [x] **AC-6:** Tests cover draft workflows, unsupported actions, scope denial, and sensitive data handling

## Definition of Done

- Local draft and profile-improvement workflows work without LinkedIn credentials
- Automated capabilities are limited to officially supported and explicitly authorized APIs
- PR merged from `feature/linkedin-assisted-workflow` into `develop`

---

**EST:** 5 SP

**RT:** 2026-07-13
**QA:** 2026-07-13

---

### Task: PLUGIN-001 — MCP & Plugin Tool Discovery

**Status:** ✅ DONE

**EST:** 13 SP | **RT:** 2026-07-13 | **QA:** 2026-07-13

---

## Task Description

Add controlled discovery and loading of tools from installed local plugins and configured MCP
servers, adapting them into the same registry, risk, permission, and audit contracts.

## User Story

As a Nexus maintainer,
I need capabilities to be added without modifying the core application
so that service integrations can evolve as isolated, reviewable packages.

## Acceptance Criteria

- [x] **AC-1:** Plugin manifests define identity, version, tool schemas, permissions, and entry point
- [x] **AC-2:** MCP tool schemas are validated and adapted into ToolDescriptor and ToolRequest contracts
- [x] **AC-3:** Only explicitly installed and enabled providers are loaded
- [x] **AC-4:** Provider tools cannot bypass registry risk policy, timeout, cancellation, or audit
- [x] **AC-5:** Version conflicts, unavailable servers, duplicate names, and malformed schemas fail safely
- [x] **AC-6:** Tests cover discovery, enable/disable, isolation, collisions, failures, and uninstall behavior

## Definition of Done

- A mocked local plugin and MCP server expose tools through the normal Nexus registry
- Disabling or removing a provider immediately removes its tools without affecting core tools
- PR merged from `feature/plugin-mcp-discovery` into `develop`

---

**EST:** 13 SP

---

### Task: TASKS-001 — Goals, Plans & Resumable Tasks

**Status:** ✅ DONE

---

## Task Description

Add persistent goals and task execution records so Nexus can plan multi-step work, report progress,
handle blockers, and resume interrupted work.

## User Story

As a Nexus user,
I need complex requests to become visible and resumable plans
so that I can trust progress and continue work across sessions.

## Acceptance Criteria

- [x] **AC-1:** Typed goal, plan step, dependency, result, blocker, and status models
- [x] **AC-2:** Plans support pending, active, waiting, blocked, failed, and completed states
- [x] **AC-3:** Task state persists locally and can be resumed after restart
- [x] **AC-4:** User can inspect, pause, cancel, or amend a plan
- [x] **AC-5:** Completion requires evidence or explicit verification, not only an LLM claim
- [x] **AC-6:** Tests cover interruption, recovery, cancellation, and blocked tasks

## Definition of Done

- A multi-step mocked task survives restart and resumes correctly
- Progress is available to both UI and conversational responses
- PR merged from `feature/goals-resumable-tasks` into `develop`

---

**EST:** 8 SP

---

### Task: MEM-002 — Structured Multi-Layer Memory

**Status:** ✅ DONE

**EST:** 8 SP | **RT:** 2026-07-13 | **QA:** 2026-07-13

---

## Task Description

Evolve the current conversation-snippet store into working, episodic, semantic, preference, and
procedural memory with explicit provenance, confidence, importance, sensitivity, and retention.

## User Story

As a Nexus user,
I need the assistant to remember useful context accurately
so that it becomes more helpful without storing everything indiscriminately.

## Acceptance Criteria

- [x] **AC-1:** Schema supports working, episodic, semantic, preference, and procedural memory types
- [x] **AC-2:** Every memory records source, confidence, importance, sensitivity, timestamps, and scope
- [x] **AC-3:** Memory manager decides what is promoted to long-term memory
- [x] **AC-4:** Retrieval combines keyword and optional local embedding search behind one interface
- [x] **AC-5:** Duplicate consolidation, contradiction handling, summaries, and retention policies are supported
- [x] **AC-6:** Existing JSON memories migrate safely or remain readable

## Definition of Done

- Migration and retrieval tests pass (16/16)
- Context builder can request only relevant memory types within a token budget
- PR created from `feature/structured-memory` into `develop`

---

**EST:** 8 SP

---

### Task: MEM-003 — Memory Consent & Management UI

**Status:** ✅ DONE

---

## Task Description

Give the user transparent control over what Nexus remembers, including inspection, correction,
deletion, export, retention, and sensitive-memory consent.

## User Story

As a privacy-conscious Nexus user,
I need to see and control the assistant's memory
so that personalization remains understandable and reversible.

## Acceptance Criteria

- [x] **AC-1:** UI lists memories by type, scope, source, and sensitivity
- [x] **AC-2:** User can search, edit, delete, pin, and correct individual memories
- [x] **AC-3:** User can export or clear memory by type, project, or time range
- [x] **AC-4:** Sensitive information follows configurable ask, allow, or never-store policy
- [x] **AC-5:** Nexus can answer "What do you remember about me?" from actual stored data
- [x] **AC-6:** Memory changes are audited and immediately affect retrieval

## Definition of Done

- Memory-control smoke tests pass
- Deleted memories are no longer returned by retrieval
- PR merged from `feature/memory-consent-ui` into `develop`

---

**EST:** 5 SP

**RT:** 2026-07-13
**QA:** 2026-07-13

---

### Task: PERSONA-001 — Persona & Interaction Modes

**Status:** ✅ DONE

**EST:** 5 SP | **RT:** 2026-07-13 | **QA:** 2026-07-13

---

## Task Description

Create a bounded, configurable Nexus persona that stays consistent across text, voice, face, and
proactive behavior while preserving factual reliability.

## User Story

As a Nexus user,
I need a playful but adjustable companion
so that interaction feels personal without interfering with focused work.

## Acceptance Criteria

- [x] **AC-1:** Companion, balanced, and focused interaction modes are available
- [x] **AC-2:** Settings include playfulness, proactivity, response detail, quiet hours, and unsolicited suggestions
- [x] **AC-3:** Persona changes expression and delivery but never lowers factual or permission standards
- [x] **AC-4:** Structured response metadata can drive emotion, voice delivery, and confidence cues
- [x] **AC-5:** Proactive behavior is rate-limited, interruptible, and disabled during quiet hours
- [x] **AC-6:** Tests verify stable behavior and settings persistence

## Definition of Done

- Mode changes visibly affect style without changing task correctness
- Persona settings persist and are exposed in the settings UI
- PR merged from `feature/persona-interaction-modes` into `develop`

---

**EST:** 5 SP

**RT:** 2026-07-13
**QA:** 2026-07-13

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

### Task: UI-FACE-002 — Selectable Face Themes

**Status:** ✅ DONE

---

## Task Description

Add selectable visual themes to the animated Nexus face while preserving every emotion and
animation. Include minimalist blue, pixel, red alert, and science-fiction variants alongside the
classic appearance.

## User Story

As a Nexus user,
I need several distinct face appearances
so that the assistant can match my preferred mood and desktop style.

## Acceptance Criteria

- [x] **AC-1:** Classic, neon blue, pixel, red alert, and cosmic themes are available
- [x] **AC-2:** Themes preserve every existing emotion and animation API
- [x] **AC-3:** Pixel theme renders crisp rectangular eyes and mouth
- [x] **AC-4:** Theme can be selected at construction time or changed while running
- [x] **AC-5:** Face server exposes theme selection and theme discovery endpoints
- [x] **AC-6:** Theme preference persists in NexusConfig and is available in settings UI
- [x] **AC-7:** Unit tests cover all themes, emotions, runtime switching, and invalid values

## Definition of Done

- Theme tests and the complete regression suite pass
- Existing face consumers continue to work with the classic default
- PR created from `feature/face-themes` into `develop` after CORE-001 is merged

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
| INTEGRATION-001 | Main Application & Pipeline | 2026-07-13 | Integration Agent |
| CORE-001 | Assistant Runtime State Machine | 2026-07-13 | Integration Agent |
| UI-FACE-002 | Selectable Face Themes | 2026-07-13 | UI Agent |
| TOOLS-001 | Tool Protocol, Registry & Permissions | 2026-07-13 | Integration Agent |
| TASKS-001 | Goals, Plans & Resumable Tasks | 2026-07-13 | Integration Agent |
| CONNECTOR-002 | Gmail Tools | 2026-07-13 | Integration Agent |
| CONNECTOR-003 | Google Calendar Tools | 2026-07-13 | Integration Agent |
| CONNECTOR-004 | Telegram Tools | 2026-07-13 | Integration Agent |
| CONNECTOR-005 | LinkedIn Assisted Workflow | 2026-07-13 | Integration Agent |
| PLUGIN-001 | MCP & Plugin Tool Discovery | 2026-07-13 | Integration Agent |
| MEM-003 | Memory Consent & Management UI | 2026-07-13 | Backend Agent |
| PERSONA-001 | Persona & Interaction Modes | 2026-07-13 | Integration Agent |

---

> **Last updated:** 2026-07-13
> **Maintainer:** Documentation Agent
