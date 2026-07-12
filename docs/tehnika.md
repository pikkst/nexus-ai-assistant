# Nexus Local AI Assistant — Technical Documentation

> **Version:** 1.1.0  
> **Language:** English  
> **Purpose:** Complete technical architecture reference for all agents implementing the Nexus system.

---

## 1. System Architecture Overview

Nexus follows a **modular pipeline architecture** where each component is an independent service communicating via in-process message passing.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           NEXUS APPLICATION                                 │
│                                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────────────┐    │
│  │  AUDIO   │   │  VISION  │   │   LLM    │   │       MEMORY         │    │
│  │ CAPTURE  │   │ CAPTURE  │   │  CLIENT  │   │    VECTOR STORE      │    │
│  │ (PyAudio)│   │ (OpenCV) │   │ (Ollama) │   │     (ChromaDB)       │    │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └──────────┬───────────┘    │
│       │              │              │                    │                │
│       ▼              ▼              ▼                    ▼                │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────────────┐    │
│  │   VAD    │   │  FRAME   │   │  SYSTEM   │   │  CONVERSATION       │    │
│  │  (WebRTC)│   │PROCESSOR │   │  PROMPTS  │   │  HISTORY            │    │
│  └────┬─────┘   └──────────┘   └──────────┘   └──────────────────────┘    │
│       │                                                                     │
│       ▼                                                                     │
│  ┌──────────┐   ┌──────────┐   ┌──────────────────────────────────────┐    │
│  │   STT    │──▶│   LLM    │──▶│             TTS                     │    │
│  │ (Whisper)│   │  REASON  │   │          (Piper/edge-tts)          │    │
│  └──────────┘   └──────────┘   └──────────────┬──────────────────────┘    │
│                                                │                            │
│                                                ▼                            │
│                                     ┌──────────────────┐                   │
│                                     │  AUDIO PLAYBACK  │                   │
│                                     │   (PyAudio)      │                   │
│                                     └──────────────────┘                   │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     ANIMATED FACE (NexusFace)                         │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │  │
│  │  │  IDLE    │  │ LISTENING│  │ THINKING  │  │      SPEAKING       │  │  │
│  │  │  😊     │  │  👂     │  │  🤔      │  │      🗣️            │  │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     USER INTERFACE (Gradio/CTk)                       │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │  │
│  │  │  NexusFace   │  │ Conversation │  │  Settings    │  │  Status  │ │  │
│  │  │  (SVG embed) │  │   History    │  │   Panel      │  │  Text    │ │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.1 Data Flow — Voice Interaction

```
User speaks → Microphone → PyAudio → AudioCapture
    → VAD (detects speech start)
    → Face: LISTENING
    → Audio chunks buffered
    → VAD (detects speech end)
    → Face: THINKING
    → STT Engine (Whisper) transcribes to text
    → MemoryStore (save utterance)
    → LLM Client (Ollama) generates response
    → MemoryStore (save response)
    → Face: SPEAKING
    → TTS Engine (Piper) synthesizes audio
    → AudioPlayback → Speakers → User hears response
    → Face: IDLE
```

### 1.2 Data Flow — Vision

```
Camera → OpenCV → CameraCapture → FrameProcessor
    → Person detection (presence)
    → Optional: gesture, expression, object detection
    → Context injection into LLM prompt
```

---

## 2. Component Specifications

### 2.1 Audio Capture (`src/audio/capture.py`)

**Purpose:** Capture microphone audio in real-time.

**Technology:** PyAudio or sounddevice

**API:**

```python
class AudioCapture:
    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_size: int = 1024,
        device_index: int | None = None,
    ): ...

    async def start(self) -> None: ...        # Begin capture
    async def stop(self) -> None: ...         # Stop capture
    async def __aenter__(self) -> "AudioCapture": ...
    async def __aexit__(self, ...) -> None: ...

    # Callbacks (set before start)
    on_audio_chunk: Callable[[np.ndarray], None]  # Raw PCM data
    on_speech_start: Callable[[], None]
    on_speech_end: Callable[[], None]
```

**VAD Integration:**

- Use `webrtcvad` (lightweight) or `silero-vad` (more accurate)
- VAD processes each audio chunk
- `on_speech_start` fired when VAD transitions from silence → speech
- `on_speech_end` fired after N consecutive silence frames (configurable, default 500ms)
- Chunks during speech are accumulated into a buffer for STT

**Error Handling:**
- If no microphone detected → log warning, `on_audio_chunk` never fires, `start()` returns silently
- If device busy → retry once after 1s, then log error

---

### 2.2 Audio Playback (`src/audio/playback.py`)

**Purpose:** Play audio through speakers.

**Technology:** PyAudio or sounddevice

**API:**

```python
class AudioPlayback:
    def __init__(self, device_index: int | None = None): ...

    async def play(self, audio: np.ndarray, sample_rate: int = 24000) -> None: ...
    async def play_file(self, path: Path) -> None: ...
    async def stop(self) -> None: ...          # Interrupt current
    async def set_volume(self, volume: float) -> None: ...  # 0.0–1.0
    async def __aenter__(self) -> "AudioPlayback": ...
    async def __aexit__(self, ...) -> None: ...
```

**Features:**
- Internal queue for non-blocking playback
- `stop()` immediately clears queue and closes stream
- Volume applied as gain factor on float32 audio
- Supports WAV via `scipy.io.wavfile` or `soundfile`

---

### 2.3 Voice Activity Detection (VAD) (`src/audio/vad.py`)

**Purpose:** Detect when a person is speaking.

**Technology:** WebRTCVAD (built-in to webrtcvad package)

**API:**

```python
class VoiceActivityDetector:
    def __init__(
        self,
        aggressiveness: int = 3,   # 0–3 (3 = most aggressive filtering)
        sample_rate: int = 16000,
        frame_ms: int = 30,        # 10, 20, or 30ms
        silence_duration_ms: int = 500,  # ms of silence to end utterance
    ): ...

    def is_speech(self, frame: bytes) -> bool: ...
    def process_chunk(self, chunk: np.ndarray) -> VadState: ...
    def reset(self) -> None: ...
```

**States:**
- `SILENCE` — no speech detected
- `SPEECH` — speech actively detected
- `ENDING` — speech ended but within grace period

---

### 2.4 Speech-to-Text (`src/stt/engine.py`)

**Purpose:** Convert audio to text offline.

**Technology:** faster-whisper (whisper.cpp bindings)

**API:**

```python
class STTEngine:
    def __init__(
        self,
        model_size: str = "base",    # tiny, base, small, medium, large
        device: str = "auto",        # cpu, cuda, auto
        compute_type: str = "int8",  # int8, float16, float32
        language: str = "auto",      # "et", "en", or "auto" for detection
    ): ...

    async def transcribe(self, audio: np.ndarray) -> TranscriptionResult: ...
    async def load_model(self) -> None: ...   # Preload model
    async def unload_model(self) -> None: ... # Free memory

@dataclass
class TranscriptionResult:
    text: str
    language: str
    confidence: float
    segments: list[Segment]
```

**Model Management:**
- Models downloaded on first use (cached in `~/.cache/whisper/`)
- `tiny` model loads in ~1s, good for testing
- `base` recommended for production use
- Language: if `auto`, whisper detects; explicitly set "et" or "en" for better accuracy

---

### 2.5 Text-to-Speech (`src/tts/engine.py`)

**Purpose:** Convert text to speech offline.

**Technology:** Piper TTS (primary) or edge-tts (fallback)

**API:**

```python
class TTSEngine:
    def __init__(
        self,
        voice: str = "en_US-lessac-medium",   # Piper voice name
        speed: float = 1.0,                    # 0.5–2.0
        device: str = "cpu",                   # cpu or cuda
    ): ...

    async def speak(self, text: str) -> np.ndarray: ...  # Returns audio
    async def speak_to_file(self, text: str, path: Path) -> None: ...
    async def load_voice(self) -> None: ...
    async def set_voice(self, voice: str) -> None: ...
```

**Voice Management:**
- Piper voices downloaded on first use
- Storage: `~/.nexus/voices/`
- Estonian voices: `et_EE-harri-medium` (Harri)
- English voices: `en_US-lessac-medium`, `en_GB-southern_english_female-medium`
- Fallback: if Piper model not found, use `edge-tts` (requires internet for first run, caches after)

**Text Chunking:**
- Split long responses at sentence boundaries (`. ! ?`)
- Each chunk processed separately to avoid UI freeze
- Chunks concatenated in returned numpy array

---

### 2.6 LLM Client (`src/llm/client.py`)

**Purpose:** Generate text responses using a local LLM.

**Technology:** Ollama REST API (or llama.cpp server)

**API:**

```python
class LLMClient:
    def __init__(
        self,
        model: str = "llama3.1",
        base_url: str = "http://localhost:11434",
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ): ...

    async def generate(self, prompt: str) -> AsyncIterator[str]: ...
    async def generate_full(self, prompt: str) -> str: ...
    async def is_ready(self) -> bool: ...      # Check if Ollama is running
    async def list_models(self) -> list[str]: ...
    async def set_model(self, model: str) -> None: ...
```

**Context Management:**
- Conversation history stored as list of `{"role": "user"|"assistant", "content": str}`
- Sent to LLM as chat messages (Ollama chat API)
- Truncate to fit context window (sliding window: keep last N messages)
- Vision context injected as text description in system prompt

**Prompt Templates** (`src/llm/prompts.py`):

```python
SYSTEM_PROMPT = """You are Nexus, a privacy-first local AI assistant.
You run entirely on the user's machine with no internet access.

Capabilities:
- You can speak and listen via the computer's microphone and speakers
- You can see through the camera (you receive visual descriptions)
- You have memory of past conversations

Rules:
- Be concise and helpful
- If unsure, say so
- Never invent information
- Respect user privacy at all times"""

VISION_CONTEXT_TEMPLATE = "Visual context from camera: {description}"
```

**Error Handling:**
- If Ollama not running → `is_ready()` returns False → UI shows "LLM not available"
- If model not pulled → return specific error message with instruction to `ollama pull <model>`

---

### 2.7 Camera Capture (`src/vision/camera.py`)

**Purpose:** Capture video frames from the computer's camera.

**Technology:** OpenCV (cv2)

**API:**

```python
@dataclass
class CameraCaptureConfig:
    device_index: int = 0
    width: int = 640
    height: int = 480
    fps: int = 15

class CameraCapture:
    def __init__(self, config: CameraCaptureConfig | None = None): ...

    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    def get_frame(self, timeout: float = 1.0) -> np.ndarray | None: ...
    @property
    def is_active(self) -> bool: ...
    async def __aenter__(self) -> "CameraCapture": ...
    async def __aexit__(self, *args: Any) -> None: ...

    on_frame: Callable[[np.ndarray], None] | None
```

**Threading:**
- Camera runs in a background thread.
- `on_frame` callback fires for each captured frame.
- `get_frame()` pulls the latest frame from an internal queue.
- `start()` returns silently if OpenCV is missing or the camera is unavailable.

**Graceful Degradation:**
- If camera unavailable → log warning, `is_active` is False.
- Failed frame reads are logged and skipped.

---

### 2.8 Frame Processor (`src/vision/processor.py`)

**Purpose:** Process camera frames to extract useful information.

**Technology:** OpenCV with optional ONNX models

**API:**

```python
class FrameProcessor:
    def __init__(self): ...

    async def detect_presence(self, frame: np.ndarray) -> bool: ...
    async def describe_scene(self, frame: np.ndarray) -> str: ...
    async def process(self, frame: np.ndarray) -> VisionContext: ...

@dataclass
class VisionContext:
    person_present: bool
    scene_description: str
    timestamp: float
```

**Implementation Notes (v1.0):**
- Presence detection: background subtraction + contour detection (lightweight, no ML needed)
- Scene description: not implemented in v1.0 (returns empty string)
- Extensible via subclassing for future ML models

---

### 2.9 Memory Store (`src/memory/store.py`)

**Purpose:** Persistent storage for conversations, preferences, and learned information.

**Technology:** ChromaDB

**API:**

```python
class MemoryStore:
    def __init__(
        self,
        storage_path: Path = Path("~/.nexus/memory").expanduser(),
        collection_name: str = "nexus_memory",
    ): ...

    async def store_conversation(
        self, user_message: str, assistant_response: str
    ) -> None: ...

    async def search_similar(
        self, query: str, n_results: int = 5
    ) -> list[ConversationEntry]: ...

    async def get_conversation_history(
        self, limit: int = 50
    ) -> list[ConversationEntry]: ...

    async def store_preference(self, key: str, value: str) -> None: ...
    async def get_preference(self, key: str) -> str | None: ...

    async def clear(self) -> None: ...

@dataclass
class ConversationEntry:
    id: str
    user_message: str
    assistant_response: str
    timestamp: float
    metadata: dict
```

**Storage Layout:**
```
~/.nexus/
├── memory/
│   ├── chroma.sqlite3
│   └── chroma_data/
├── voices/
│   └── *.onnx
├── config.json
└── logs/
```

---

### 2.10 Animated Face (`src/ui/face.py`)

**Purpose:** Provide a Looi-style animated face for the Nexus assistant.

**Technology:** Pure SVG generation — zero external dependencies.

**Emotions:**

| State | When | Eyes | Mouth | Eyebrows | Blush |
|-------|------|------|-------|----------|-------|
| idle | Waiting for input | Open, soft gaze | Gentle smile | Neutral | Subtle |
| listening | User is speaking | Open, focused | Slight smile | Raised, attentive | Medium |
| thinking | LLM processing | Looking up/around | Pursed | One raised | Subtle |
| speaking | TTS playback | Open, talking | Open, animated | Neutral | Subtle |
| happy | Greeting/success | Squinted (^_^) | Wide smile | Lowered | Strong |
| sad | Error/negative | Droopy, half-closed | Frown | Angled up inner | Faint |
| surprised | Unexpected input | Wide open (1.3x) | Open O shape | Very raised | Faint |
| confused | Uncertain query | One squinted | Wavy/wry | One up, one down | Subtle |
| sleeping | Inactive | Closed (U shape) | Slightly open | Relaxed | None |

**API:**

```python
class NexusFace:
    def __init__(self, config: FaceConfig | None = None): ...

    def render(self, emotion: Emotion | str = Emotion.IDLE) -> str:
        """Render the face as an SVG string."""

    def render_state(self, state: FaceState | None = None) -> str:
        """Render using a custom FaceState for animation."""

    def animate(self, dt: float = 0.05) -> str:
        """Advance animation by dt seconds, return next SVG frame.
        Handles: blink cycle, gaze jitter, mouth movement, eye scaling."""

@dataclass
class FaceConfig:
    width: int = 400
    height: int = 500
    bg_color: str = "#1a1a2e"
    head_color: str = "#2d2d44"
    eye_white: str = "#f0f0f5"
    iris_color: str = "#2a8bcc"

@dataclass
class FaceState:
    emotion: Emotion = Emotion.IDLE
    blink: BlinkState = BlinkState.OPEN
    blink_timer: int = 0
    gaze_x: float = 0.0
    gaze_y: float = 0.0
    mouth_open: float = 0.0
    eye_scale: float = 1.0
    talking_frame: int = 0
    time: float = 0.0
```

**Face Server** (`src/ui/face_server.py`):

```python
# HTTP API endpoints:
GET /api/face/render?emotion=happy      # → SVG (static)
GET /api/face/animate?emotion=listening  # → SVG (animated frame)
GET /api/face/emotions                   # → JSON list of emotions
GET /api/face/state                      # → JSON current state
GET /face-demo                           # → Interactive demo HTML
GET /face-grid                           # → Emotion grid HTML
```

Run: `python -m nexus.ui.face_server` → http://localhost:8765/face-demo

---

### 2.11 Configuration (`src/config/settings.py`)

**Purpose:** Central configuration management.

**Technology:** Pydantic Settings + JSON file

**API:**

```python
@dataclass
class NexusConfig:
    # Audio
    mic_device_index: int | None = None
    speaker_device_index: int | None = None
    sample_rate: int = 16000

    # STT
    stt_model_size: str = "base"
    stt_language: str = "auto"

    # TTS
    tts_voice: str = "en_US-lessac-medium"
    tts_speed: float = 1.0

    # LLM
    llm_model: str = "llama3.1"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2048
    ollama_url: str = "http://localhost:11434"

    # Vision
    camera_index: int = 0
    camera_resolution: tuple = (640, 480)
    camera_fps: int = 15

    # Memory
    memory_path: Path = Path("~/.nexus/memory")

    # UI
    theme: str = "dark"
    language: str = "en"

    @classmethod
    def load(cls) -> "NexusConfig": ...
    def save(self) -> None: ...
```

**Config File:** `~/.nexus/config.json` — auto-created with defaults on first run.

---

## 3. Error Handling Strategy

### 3.1 Graceful Degradation

| Missing Component | Behaviour |
|------------------|-----------|
| Microphone | Log warning, disable voice input, allow text input via UI, face shows "idle" |
| Camera | Log warning, disable vision features, continue without |
| Speakers | Log warning, disable voice output, show text responses in UI |
| Ollama | Show "LLM not available" in UI (face remains idle), retry every 30s |
| STT Model | Show download progress, fall back to text input while downloading |
| TTS Voice | Show download progress, fall back to text output while downloading |

### 3.2 Error Logging

- Use `loguru` for structured logging
- Log file: `~/.nexus/logs/nexus_{date}.log`
- Log levels: DEBUG, INFO, WARNING, ERROR
- Console output shows INFO and above
- File output shows DEBUG and above

---

## 4. Performance Targets

| Metric | Target | Measured At |
|--------|--------|-------------|
| Voice-to-voice latency | < 3 seconds | From end of user speech to start of assistant speech |
| STT latency | < 1 second | Audio end → text available |
| LLM first token | < 500ms | Prompt sent → first token received |
| TTS latency | < 500ms | Text sent → first audio heard |
| Frame processing | < 100ms | Per frame at 640x480 |
| Memory search | < 200ms | Semantic search over 1000 entries |
| **Face render** | **< 5ms** | **SVG generation per frame** |
| **Face server response** | **< 10ms** | **HTTP request → SVG response** |
| UI response | < 100ms | UI action → visual feedback |
| Memory usage | < 500MB | Idle (no models loaded) |
| Disk usage | < 5GB | All models, voices, and data |

---

## 5. Dependencies

### 5.1 Core Dependencies (`requirements.txt`)

```
# Audio
pyaudio>=0.2.13
sounddevice>=0.4.6
webrtcvad>=2.0.10
numpy>=1.26.0
soundfile>=0.12.1

# Vision
opencv-python>=4.9.0

# STT
faster-whisper>=1.0.0

# TTS
piper-tts>=1.2.0

# LLM
httpx>=0.27.0
ollama>=0.4.0

# Memory
chromadb>=0.5.0

# UI
gradio>=4.44.0          # Option 1
customtkinter>=5.2.0    # Option 2 (alternative)

# Config
pydantic>=2.7.0
pydantic-settings>=2.2.0

# Async
asyncio>=3.4
aiofiles>=23.2.0

# Logging
loguru>=0.7.0

# Testing
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-mock>=3.14.0
```

**Note:** The face module (`src/ui/face.py`) has **zero external dependencies** — it only uses Python stdlib.

### 5.2 System Dependencies (Windows)

- Microsoft Visual C++ Redistributable (for PyAudio)
- PortAudio (bundled with PyAudio wheel for Windows)
- Ollama (separate install: https://ollama.com)

---

## 6. Directory & Module Reference

```
nexus/                              # Python package root
├── __init__.py                     # Package metadata
├── main.py                         # Entry point, wires everything
├── audio/
│   ├── __init__.py
│   ├── capture.py                  # AudioCapture class
│   ├── playback.py                 # AudioPlayback class
│   └── vad.py                      # VoiceActivityDetector class
├── vision/
│   ├── __init__.py
│   ├── camera.py                   # CameraCapture class
│   └── processor.py                # FrameProcessor class
├── stt/
│   ├── __init__.py
│   └── engine.py                   # STTEngine class
├── tts/
│   ├── __init__.py
│   └── engine.py                   # TTSEngine class
├── llm/
│   ├── __init__.py
│   ├── client.py                   # LLMClient class
│   └── prompts.py                  # System prompt templates
├── memory/
│   ├── __init__.py
│   └── store.py                    # MemoryStore class
├── ui/
│   ├── __init__.py
│   ├── face.py                     # NexusFace class (SVG animated face)
│   ├── face_server.py              # HTTP API server for face
│   ├── face_demo_grid.html         # Emotion grid demo (generated)
│   ├── face_demo_animated.html     # Interactive demo (generated)
│   └── app.py                      # Main UI (Gradio or CTk)
└── config/
    ├── __init__.py
    └── settings.py                 # NexusConfig dataclass
```

---

## 7. Development Setup

### 7.1 Prerequisites

```bash
# 1. Install Python 3.11+
# 2. Install Ollama from https://ollama.com
# 3. Pull default model:
ollama pull llama3.1

# 4. Clone repo & setup:
git clone <repo-url>
cd nexus
python -m venv .venv
.venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

### 7.2 Running

```bash
# Face server (standalone):
python src/ui/face_server.py
# Open http://localhost:8765/face-demo

# Development (with hot reload for Gradio):
python -m nexus.main

# Tests:
pytest tests/ -v

# Type checking:
mypy src/
```

### 7.3 Building

```bash
pip install pyinstaller
pyinstaller nexus.spec
```

---

> **Last updated:** 2026-07-12  
> **Maintainer:** Architect Agent
