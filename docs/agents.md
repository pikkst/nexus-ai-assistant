# Nexus Local AI Assistant — Agents Documentation

> **Version:** 1.0.0  
> **Language:** English  
> **Purpose:** This document defines how AI agents collaborate to build the Nexus Local AI Assistant — a privacy-first, locally-run desktop assistant that uses the computer's camera, microphone, and speakers.

---

## 1. Project Overview

**Nexus** is a local AI assistant that runs entirely on the user's machine. It:

- **Sees** via the computer's camera (gesture recognition, visual context, user presence detection)
- **Listens** via the microphone (speech-to-text, voice commands)
- **Speaks** via the speakers (text-to-speech, audio feedback)
- **Thinks** via a local LLM (e.g., Ollama, llama.cpp, GPT4All)
- **Remembers** via a local vector store (e.g., ChromaDB, LanceDB)

All processing is offline. No data leaves the machine.

---

## 2. Agent Roles & Responsibilities

### 2.1 Architect Agent
- Designs system architecture (component diagrams, data flow)
- Defines API contracts between modules
- Chooses technology stack and justifies decisions
- Writes `tehnika.md` and keeps it up-to-date

### 2.2 Backend Agent
- Implements core services:
  - Audio capture & playback
  - Video/camera capture
  - Speech-to-text (STT) engine
  - Text-to-speech (TTS) engine
  - Local LLM integration
  - Memory/vector store integration
- Writes unit tests for all services
- Creates Python package structure

### 2.3 Frontend/UI Agent
- Builds the user interface (TUI or GUI)
- Implements settings/configuration panel
- Connects UI to backend via IPC or local API
- Handles permission management (camera, mic, speaker)

### 2.4 Integration Agent
- Wires all modules together
- Creates the main application entry point
- Implements error handling and logging
- Writes integration tests
- Creates startup scripts and system tray integration

### 2.5 Documentation Agent
- Maintains `agents.md`, `task.md`, `memory.md`
- Writes user-facing documentation
- Creates `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`

---

## 3. Workflow Rules

### 3.1 Branch Strategy
```
main              → Stable releases
develop           → Integration branch
feature/*         → New features (branched from develop)
fix/*             → Bug fixes
docs/*            → Documentation changes
```

### 3.2 Task Lifecycle (Every Task MUST follow this)

```
1. CREATE a new branch from develop:
   git checkout develop
   git pull
   git checkout -b feature/descriptive-name

2. READ memory.md and task.md to understand current state

3. IMPLEMENT the task

4. UPDATE memory.md with what was done, decisions made, problems encountered

5. UPDATE task.md — mark the completed task, add new tasks if discovered

6. CREATE a Pull Request:
   - Title: concise summary
   - Description: links to task, what was done, how to test
   - Assign: relevant agent role

7. MERGE only after:
   - All AC met
   - Tests pass
   - Code review done (simulated or human)
```

### 3.3 Communication Between Agents
- **memory.md** is the shared context — always read it before starting work
- **task.md** is the shared backlog — always update it after completing work
- When one agent needs input from another, they add a note in `task.md` under "Blockers"
- Never overwrite another agent's work without coordination

### 3.4 File Change Protocol
- Always read a file before modifying it
- Make one focused change at a time
- After change, verify the file is still syntactically valid
- If a change breaks something, revert immediately and document why

---

## 4. Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Language | Python 3.11+ | Best ecosystem for AI/ML, audio, video |
| Local LLM | Ollama + Llama 3 / Mistral | Runs locally, good performance |
| STT | Whisper (OpenAI) or faster-whisper | Best offline speech recognition |
| TTS | Piper TTS or edge-tts | Fast, local, multilingual |
| Camera | OpenCV (cv2) | Industry standard for camera capture |
| Audio I/O | PyAudio or sounddevice | Low-latency audio capture/playback |
| Vector Store | ChromaDB | Simple, local, no server needed |
| UI | Gradio or CustomTkinter | Lightweight, cross-platform |
| ASR/LLM Bridge | LangChain or custom | Orchestration between components |
| Packaging | PyInstaller | Single executable distribution |

---

## 5. Coding Standards

### 5.1 Python
- Type hints required for all function signatures
- Docstrings: Google style
- Max line length: 100 characters
- Use `pathlib` for file paths (never `os.path`)
- Use `dataclasses` for data containers
- Use `enum` for fixed constants
- Async for I/O-bound operations (aiofiles, asyncio subprocess)

### 5.2 Project Structure
```
nexus/
├── src/
│   ├── __init__.py
│   ├── main.py                # Entry point
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── capture.py         # Mic input
│   │   ├── playback.py        # Speaker output
│   │   └── vad.py             # Voice activity detection
│   ├── vision/
│   │   ├── __init__.py
│   │   ├── camera.py          # Camera capture
│   │   └── processor.py       # Frame processing
│   ├── stt/
│   │   ├── __init__.py
│   │   └── engine.py          # Speech-to-text
│   ├── tts/
│   │   ├── __init__.py
│   │   └── engine.py          # Text-to-speech
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py          # LLM API client
│   │   └── prompts.py         # System prompts
│   ├── memory/
│   │   ├── __init__.py
│   │   └── store.py           # Vector store wrapper
│   ├── ui/
│   │   ├── __init__.py
│   │   └── app.py             # User interface
│   └── config/
│       ├── __init__.py
│       └── settings.py        # Configuration management
├── tests/
│   ├── test_audio.py
│   ├── test_vision.py
│   ├── test_stt.py
│   ├── test_tts.py
│   ├── test_llm.py
│   └── test_memory.py
├── docs/
│   ├── agents.md
│   ├── task.md
│   ├── memory.md
│   └── tehnika.md
├── scripts/
│   ├── setup.sh
│   └── run.sh
├── requirements.txt
├── pyproject.toml
├── README.md
└── CHANGELOG.md
```

### 5.3 Testing
- Every module must have unit tests
- Use `pytest` with `pytest-asyncio` for async tests
- Mock hardware devices in CI (no real camera/mic needed)
- Minimum 80% code coverage

---

## 6. Constraints & Non-Goals

### 6.1 Constraints
- Everything must run **offline** — no cloud API calls
- Must work on **Windows 11** as primary target (Linux/Mac secondary)
- **Privacy-first**: no data logged to disk unless user explicitly opts in
- Low latency: voice-to-voice response under 3 seconds on modern hardware
- Graceful degradation if camera/mic unavailable

### 6.2 Non-Goals (for v1.0)
- Cloud sync
- Mobile apps
- Multi-user support
- Plugin system

---

## 7. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-07-12 | Python as primary language | Best AI/ML ecosystem |
| 2026-07-12 | Ollama for LLM | Simplest local setup |
| 2026-07-12 | Whisper for STT | Best accuracy offline |
| 2026-07-12 | ChromaDB for memory | Zero-config vector store |

---

## 8. Getting Started for Agents

1. Read this file completely
2. Read `tehnika.md` for technical architecture
3. Read `memory.md` for current project state
4. Read `task.md` for the active task
5. Create a new branch for your task
6. Implement, document, PR

---

> **Last updated:** 2026-07-12  
> **Maintainer:** Documentation Agent
