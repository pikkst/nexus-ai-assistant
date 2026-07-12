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

### Task: ARCH-004 — Speech-to-Text Engine

**Status:** 📋 BACKLOG

**EST:** 8 SP

---

### Task: ARCH-005 — Text-to-Speech Engine

**Status:** 📋 BACKLOG

**EST:** 5 SP

---

### Task: ARCH-006 — LLM Integration

**Status:** 📋 BACKLOG

**EST:** 5 SP

---

### Task: ARCH-007 — Memory / Vector Store

**Status:** 📋 BACKLOG

**EST:** 5 SP

---

### Task: ARCH-008 — User Interface

**Status:** 📋 BACKLOG

**EST:** 8 SP

---

### Task: INTEGRATION-001 — Main Application & Pipeline

**Status:** 📋 BACKLOG

**EST:** 8 SP

---

### Task: OPS-001 — Packaging & Distribution

**Status:** 📋 BACKLOG

**EST:** 5 SP

---

### Task: ARCH-009 — UI Settings Panel

**Status:** 📋 BACKLOG

---

## Task Description

Implement a settings panel for the Nexus UI allowing users to configure audio devices, volume, TTS voice, and language.

## User Story

As a Nexus user,
I want to adjust audio settings, voice, and language from the UI
so that I can personalize my experience.

## Acceptance Criteria

- [ ] **AC-1:** Settings window with audio section (volume slider, sample rate, device selection)
- [ ] **AC-2:** TTS voice/tone selection
- [ ] **AC-3:** Language selection (et/en)
- [ ] **AC-4:** Persist settings to `~/.nexus/config.json`
- [ ] **AC-5:** Load settings on startup

## Definition of Done

- `pytest tests/test_settings.py` passes
- Settings window opens and saves correctly

---

**EST:** 3 SP

**RT:**
**QA:**

---

## Completed Tasks

| Task ID | Name | Completed | By |
|---------|------|-----------|----|
| DOCS-001 | Create Project Documentation Foundation | 2026-07-12 | Documentation Agent |
| DOCS-002 | Initialize Project Structure & Git | 2026-07-12 | Documentation Agent |
| UI-FACE-001 | Looi-Style Animated Face Module | 2026-07-12 | Documentation Agent |
| ARCH-001 | Audio Capture Service | 2026-07-12 | Backend Agent |
| ARCH-002 | Audio Playback Service | 2026-07-12 | Backend Agent |

---

> **Last updated:** 2026-07-12  
> **Maintainer:** Documentation Agent
