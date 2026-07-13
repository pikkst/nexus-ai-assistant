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
| STT | ✅ Complete (engine.py, 54 tests) |
| TTS | 📋 Planned |
| LLM Integration | ✅ Complete (async Ollama client, prompt/history support, streaming) |
| Camera/Vision | ✅ Complete (camera.py, tests added) |
| Memory Store | ✅ Complete (structured types, provenance, manager, retention, 16 tests) |
| Animated Face UI | ✅ Complete (face.py, face_server.py, demo HTMLs) |
| Selectable Face Themes | ✅ Complete (UI-FACE-002) |
| User Interface | 📋 Planned |
| Main Pipeline | ✅ Complete (INTEGRATION-001) |
| Packaging | 📋 Planned |
| Runtime State Machine | ✅ Complete (CORE-001) |
| Tool Execution & Permissions | ✅ Complete (TOOLS-001) |
| Goals & Resumable Tasks | ✅ Complete (TASKS-001) |
| Plugin & MCP Tool Discovery | ✅ Complete (PLUGIN-001) |
| LLM Tool Selection & Calling | 🔀 Draft PR #18 (TOOLS-002) |
| Local Development Toolset | ⏳ In Progress (TOOLS-003) |
| Structured Memory & Consent | 📋 Planned (MEM-002, MEM-003) |
| Persona & Interaction Modes | ✅ Complete (PERSONA-001) |
| Verification & Safe Learning | ✅ Complete (EVAL-001) |
| Safe Reflection & Learning Loop | ✅ Complete (LEARN-001) |
| Google Calendar Tools | ✅ Complete (CONNECTOR-003) |
| Telegram Tools | ✅ Complete (CONNECTOR-004) |
| LinkedIn Tools | ✅ Complete (CONNECTOR-005) |

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
| D-027 | 2026-07-12 | OpenCV for camera capture | Industry standard, simple Python API | Backend |
| D-028 | 2026-07-12 | Camera runs in background thread | Non-blocking, consistent with audio capture | Backend |
| D-029 | 2026-07-12 | faster-whisper for STT engine | Best offline accuracy, faster than original Whisper | Backend |
| D-030 | 2026-07-12 | STT partial/final callback pattern | Supports streaming UX with interim results | Backend |
| D-031 | 2026-07-12 | Audio preprocessing before STT | Normalize, trim silence, resample to 16kHz | Backend |
| D-032 | 2026-07-12 | Direct async HTTP client for Ollama | Small offline API surface, injectable transport, no orchestration dependency | Backend |
| D-033 | 2026-07-12 | Ollama newline-delimited JSON streaming | Native backend protocol and incremental UI-ready output | Backend |
| D-034 | 2026-07-12 | JSON memory store with token cosine similarity | Dependency-free, transparent local persistence suitable for small conversation histories | Backend |
| D-035 | 2026-07-12 | Atomic writes plus age/capacity pruning | Avoid partial files and bound local storage growth | Backend |
| D-036 | 2026-07-13 | Central NexusRuntime owns the request-response lifecycle | Keeps audio, STT, memory, LLM, TTS, playback, and future UI consumers behind one testable orchestration boundary | Integration |
| D-037 | 2026-07-13 | Runtime dependencies use small protocols and constructor injection | End-to-end behavior can be tested without hardware, model files, or a live Ollama backend | Integration |
| D-038 | 2026-07-13 | STT, TTS, capture, and playback are optional runtime services | Missing local hardware or models must not prevent text interaction from working | Integration |
| D-039 | 2026-07-12 | Build one authoritative Nexus runtime before adding broad autonomy | Existing services need a coherent, testable lifecycle before they can act reliably | Architect |
| D-040 | 2026-07-12 | Separate working, episodic, semantic, preference, and procedural memory | Different information requires different retrieval, confidence, privacy, and retention rules | Architect |
| D-041 | 2026-07-12 | Tool use is typed, permissioned, auditable, and verified | Useful autonomy must remain transparent, bounded, and evidence-based | Architect |
| D-042 | 2026-07-12 | Persona affects expression, not truth or safety standards | Playfulness must not reduce factual reliability or bypass user control | Architect |
| D-043 | 2026-07-12 | Learning produces reviewable lessons and proposals, not uncontrolled self-modification | User approval remains mandatory for code, prompts, permissions, and safety rules | Architect |
| D-044 | 2026-07-13 | RuntimeStateMachine is the sole authority for runtime state | Validated transitions prevent UI, face, and services from presenting contradictory activity | Integration |
| D-045 | 2026-07-13 | State events include previous state, current state, metadata, and UTC timestamp | Consumers can render and audit transitions without reading mutable runtime internals | Integration |
| D-046 | 2026-07-13 | Face emotion is derived through a state adapter | The existing face stays decoupled from orchestration while reflecting truthful runtime state | Integration |
| D-047 | 2026-07-13 | Face themes are palette/render-style presets over the existing SVG engine | Themes preserve emotions and animation without introducing bitmap assets or duplicate renderers | UI |
| D-048 | 2026-07-13 | Classic remains the default and unknown themes fail validation | Existing consumers remain compatible and invalid persisted values cannot silently alter rendering | UI |
| D-049 | 2026-07-13 | Every tool declares one of four explicit risk levels | Read-only, local-write, external, and destructive actions can follow different confirmation policy | Integration |
| D-050 | 2026-07-13 | ToolRegistry returns structured failures while propagating cancellation | Callers can recover from validation, permission, timeout, and execution errors without hiding user cancellation | Integration |
| D-051 | 2026-07-13 | Tool audit stores redacted inputs and status but never tool output | Local accountability is preserved without copying file contents or secrets into logs | Integration |
| D-052 | 2026-07-13 | Goals and plan steps persist as versioned atomic JSON | Task state remains local, transparent, restartable, and consistent with existing storage patterns | Integration |
| D-053 | 2026-07-13 | Active goals and steps recover as paused after process restart | Nexus never assumes interrupted work continued or completed while the process was offline | Integration |
| D-054 | 2026-07-13 | Successful verified steps require machine evidence or explicit user confirmation | LLM assertions alone cannot mark real work complete | Integration |
| D-055 | 2026-07-13 | Tool calls use Ollama's native function schema and role=tool result messages | The local backend receives its documented protocol without an invented intermediary format | Integration |
| D-056 | 2026-07-13 | All model-requested calls execute exclusively through ToolRegistry | Model output cannot bypass schema validation, risk policy, timeout, cancellation, or audit | Integration |
| D-057 | 2026-07-13 | Local development commands are shell-free and explicitly allowlisted | Argument injection cannot become shell execution and unapproved programs remain unavailable | Security |
| D-058 | 2026-07-13 | File edits are atomic and capture workspace-local pre-change snapshots | Interrupted or incorrect edits can be safely restored without writing outside the project root | Data |
| D-059 | 2026-07-13 | Web search and page retrieval depend on provider protocols | Providers remain configurable and tests never require live network access | Integration |
| D-060 | 2026-07-13 | Page retrieval requires an explicit robots policy and streams into a hard byte limit | Callers cannot silently skip robots decisions or download unbounded responses | Security |
| D-061 | 2026-07-13 | Research claims may cite only URLs present in the supplied source set | Nexus rejects fabricated claim-to-source attribution before rendering references | Data |
| D-062 | 2026-07-13 | Connector tokens are persisted only through an OS-keyring adapter | Credentials never enter ordinary JSON configuration or project files | Security |
| D-063 | 2026-07-13 | OAuth lifecycles serialize operations per account | Concurrent requests cannot race refresh, revoke, or credential replacement | Security |
| D-064 | 2026-07-13 | Provider failures are converted to secret-free public OAuth errors | Provider exception text cannot leak access or refresh tokens | Security |
| D-065 | 2026-07-13 | Google Calendar tools reuse the existing tool risk and permission contracts | Read-only listing and free/busy remain safe, while create/update/delete require risk-appropriate confirmation | Integration |
| D-066 | 2026-07-13 | Event creation supports optional idempotency keys | Retried or resumed tasks cannot produce duplicate calendar events | Data |
| D-067 | 2026-07-13 | Audit redaction extended to calendar fields | Event summaries, locations, descriptions, and attendee lists do not leak into local audit logs | Security |
| D-068 | 2026-07-13 | LinkedIn routes local analysis and drafts through permissioned LOCAL_WRITE tools | Profile, post, and company imports work without credentials while keeping credential-free isolation | Integration |
| D-069 | 2026-07-13 | LinkedIn publish and send actions require explicit scope detection via detect_official_api_capabilities | Automated outreach is denied unless the official API scope is explicitly granted | Security |
| D-070 | 2026-07-13 | LinkedIn tools never expose scraping, mass outreach, or hidden browser automation | Terms-aware behaviors are gated behind official API contracts only | Security |
| D-071 | 2026-07-13 | Plugin manifests declare identity, version, tool schemas, permissions, and entry point | Third-party capabilities can be reviewed and installed without modifying core code | Integration |
| D-072 | 2026-07-13 | MCP tool schemas are adapted into existing ToolDescriptor and ToolRequest contracts | External MCP servers expose tools through the same registry, risk, permission, and audit flow | Integration |
| D-073 | 2026-07-13 | Only explicitly installed and enabled providers are loaded | Disabling or removing a provider immediately removes its tools without affecting core tools | Integration |
| D-074 | 2026-07-13 | Plugin tools cannot bypass registry risk policy, timeout, cancellation, or audit | All plugin tool invocations pass through the same ToolRegistry and audit log | Security |
| D-075 | 2026-07-13 | Version conflicts, unavailable servers, duplicate names, and malformed schemas fail safely | Broken or conflicting plugins are skipped or rejected without corrupting the registry | Integration |
| D-076 | 2026-07-13 | Persona settings are persisted in NexusConfig and a dedicated persona.json | Settings survive restarts and UI changes are immediate | Integration |
| D-077 | 2026-07-13 | Persona mode affects system-prompt tone and detail, never factual or permission standards | Playfulness is bounded by explicit factual-accuracy instruction in every persona prompt | Integration |
| D-078 | 2026-07-13 | Proactive suggestions are rate-limited and disabled during quiet hours | Users control interruption through explicit settings rather than hidden heuristics | Integration |
| D-079 | 2026-07-13 | Response metadata is emitted in runtime events for downstream face/voice consumers | Structured metadata decouples persona from rendering while keeping expression coherent | Integration |

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

**Current Task:** EVAL-001 — Result Verification & Feedback

**EVAL-001 validation:** Tests prove that unsupported completion claims are rejected, verification includes evidence/confidence/failure explanation, failed verification returns work to PENDING, user feedback supports positive/negative/explanatory signals, and local metrics track success, corrections, latency, and memory usefulness.

**PLUGIN-001 validation:** 24 plugin discovery tests pass, covering manifest discovery, local plugin loading, MCP tool adaptation, enable/disable, isolation, collisions, failures, uninstall, and adapter validation. Full suite: 295 tests pass (1 pre-existing calendar audit test failure unrelated to this work).

**CONNECTOR-005 validation:** 16 LinkedIn-specific tests pass, covering capabilities detection, draft workflows, scope denial, unsupported actions, and audit redaction. Full suite: 272 tests pass (1 pre-existing calendar audit test failure unrelated to this work).

**CONNECTOR-004 validation:** 9 Telegram-specific tests pass, covering authorization, polling, sending, failures, and audit redaction. Full suite: 255 tests pass (1 pre-existing calendar audit test failure unrelated to this work).

**CONNECTOR-003 validation:** 14 Calendar-specific tests pass, covering pagination, DST, conflicts, recurrence, cancellation, errors, idempotency, and audit redaction. Full suite: 247 tests pass.

**CONNECTOR-001 validation:** 223 tests pass, including mocked connect, refresh, revoke,
reconnect, missing-keyring, recursive-redaction, and concurrent-access coverage.

**WEB-001 validation:** 211 tests pass. Search and page providers are mocked in the web test suite;
no live network access is required.

**TOOLS-003 validation:** 197 tests pass. Ruff is configured but is not installed in the active environment.

**Most recently completed:** CONNECTOR-005 — LinkedIn Assisted Workflow, CONNECTOR-004 — Telegram Tools, CONNECTOR-003 — Google Calendar Tools, CONNECTOR-002 — Gmail Tools, ARCH-007 — Memory / Vector Store, ARCH-006 — LLM Integration, ARCH-005 — Text-to-Speech Engine

**Current work in progress:** EVAL-001 — Result Verification & Feedback

**What was built:**
- `src/tools/telegram_models.py` — typed TelegramUser, Chat, Message, Attachment, Update, MessageDraft, and TelegramProvider protocol
- `src/tools/telegram_provider.py` — MockTelegramProvider with bot identity, authorized chats, polling, and send support
- `src/tools/telegram_tools.py` — permissioned GetBotInfoTool, ListAuthorizedChatsTool, GetChatTool, GetUpdatesTool, DraftMessageTool, SendMessageTool, and SendAttachmentTool
- `src/tools/telegram_factory.py` — create_telegram_registry helper
- `src/tools/linkedin_models.py` — typed LinkedInProfile, LinkedInPost, LinkedInMessage, LinkedInCompany, LinkedInDraft, LinkedInScope, and LinkedInProvider protocol
- `src/tools/linkedin_provider.py` — MockLinkedInProvider with scope configuration, profile/post/company storage, and draft + publish + message send support
- `src/tools/linkedin_tools.py` — permissioned DetectOfficialApiCapabilitiesTool, AnalyzeProfileTool, AnalyzePostTool, ImportProfileTool, ImportPostTool, ImportCompanyTool, CreatePostDraftTool, CreateMessageDraftTool, ImproveProfileTool, PublishPostTool, and SendMessageTool
- `src/tools/linkedin_factory.py` — create_linkedin_registry helper
- `tests/test_linkedin_tools.py` — 16 mocked tests covering capabilities detection, draft workflows, scope denial, unsupported actions, and audit redaction
- `src/tools/__init__.py` — exported LinkedIn models, tools, and factory
- `src/tools/plugin_models.py` — typed PluginManifest, PluginToolSchema, and McpServerConfig contracts
- `src/tools/mcp_client.py` — JSON-RPC client for MCP initialize, tools/list, and tools/call over HTTP
- `src/tools/plugin_adapter.py` — PluginTool and McpTool wrappers that adapt plugin/MCP tools into the Nexus Tool protocol
- `src/tools/plugin_discovery.py` — PluginManager for manifest discovery, local plugin loading, MCP tool adaptation, enable/disable, and uninstall
- `src/tools/plugin_factory.py` — create_plugin_registry and create_and_load_plugin_registry helpers
- `src/config/settings.py` — persisted plugins_dir and enable_plugins configuration
- `tests/test_plugin_discovery.py` — 24 tests covering discovery, loading, collisions, enable/disable, isolation, failures, uninstall, and adapter validation
- `src/llm/tool_types.py` and `LLMClient.chat` — native Ollama tool schemas, calls, and role=tool conversations
- `src/tools/calling.py` — typed completed, waiting-confirmation, and failed agent-run snapshots
- `src/tools/agent.py` — bounded selection, registry invocation, result injection, pause/resume, and recovery loop
- Tool descriptors and built-ins now expose defensive JSON-compatible parameter schemas
- `tests/test_llm_tools.py`, `tests/test_tool_agent.py`, and `tests/test_tool_agent_limits.py` — protocol, selection, confirmation, rejection, timeout, loop, limit, and cancellation tests
- `src/tasks/models.py` — typed goals, plan steps, dependencies, results, evidence, blockers, events, and statuses
- `src/tasks/store.py` and `src/tasks/codec.py` — atomic versioned JSON persistence and full model round-trip
- `src/tasks/operations.py` — validated start, pause, resume, cancel, block, resolve, fail, and complete transitions
- `src/tasks/manager.py` and `src/tasks/base.py` — inspectable, amendable, event-emitting persistent task manager
- `src/tasks/factory.py` — standard local task-manager construction
- `tests/test_tasks_manager.py` and `tests/test_tasks_persistence.py` — lifecycle, evidence, dependency, interruption, blocker, immutability, and restart tests
- `src/config/settings.py` — persisted task storage path
- `src/tools/models.py` — typed tool, request, result, descriptor, risk, and error contracts
- `src/tools/permissions.py` — configurable allow, confirm, and deny decisions by risk level
- `src/tools/registry.py` — discovery, validation, timeout, cancellation, invocation, and audit flow
- `src/tools/audit.py` — append-only JSONL audit with recursive sensitive-key redaction
- `src/tools/filesystem.py` — sandboxed directory listing, text reading, and project inspection
- `src/tools/factory.py` — ready-to-use built-in project registry construction
- `tests/test_tools_registry.py` and `tests/test_tools_filesystem.py` — permission, lifecycle, privacy, sandbox, and end-to-end tool tests
- `src/ui/face_themes.py` — classic, neon blue, pixel, red alert, and cosmic theme presets
- `src/ui/face.py` — runtime theme switching, glow effects, and pixel eye/mouth rendering
- `src/ui/face_server.py` — theme query support, discovery endpoint, and persisted default loading
- `src/ui/settings.py` and `src/config/settings.py` — persisted face-theme selection
- `tests/test_face_themes.py` — theme, emotion, switching, pixel, palette, and validation tests
- `src/app/state_machine.py` — authoritative transition table, validation, interruption, and subscriber delivery
- `src/app/events.py` — expanded typed states and transition events with previous state and UTC timestamp
- `src/app/face_state.py` — runtime-state to face-emotion adapter compatible with `NexusFace`
- `tests/test_state_machine.py` — normal, invalid, interrupted, blocked, recovery, subscriber, and face integration tests
- `src/app/runtime.py` — event-driven `NexusRuntime` for text and captured-audio requests
- `src/app/factory.py` — configuration-driven construction of audio, STT, LLM, memory, TTS, and playback services
- `src/app/events.py` — observable runtime state and event contracts for the future UI
- `src/app/contracts.py` — injectable service protocols for hardware-free integration testing
- `src/app/lifecycle.py` — graceful optional-service startup and shutdown helpers
- `src/main.py` — minimal interactive local text shell with clean lifecycle handling
- `tests/test_app.py` and `tests/test_app_factory.py` — end-to-end, audio, lifecycle, recovery, and configuration smoke tests
- `src/config/settings.py` — persisted audio-input, audio-output, and memory feature toggles
- `src/memory/store.py` — thread-safe JSON memory service with atomic persistence, token-frequency cosine search, metadata, and timestamps
- `src/memory/models.py` — typed memory types (working, episodic, semantic, preference, procedural), provenance fields (source, confidence, importance, sensitivity, scope), MemoryEntry, MemoryResult, RetentionPolicy
- `src/memory/retrieval.py` — unified MemoryRetriever combining keyword and optional embedding search with type/scope filtering and token budgets
- `src/memory/manager.py` — MemoryManager with promotion, duplicate consolidation, contradiction resolution, summarization, and retention policies
- `tests/test_memory.py` — tests for storage, retrieval ranking, custom paths, corrupt data, age/capacity pruning, migration, promotion, consolidation, contradiction, retention, and hybrid retrieval
- `src/config/settings.py` — configurable memory storage format, capacity, and maximum age
- `src/llm/client.py` — async Ollama chat client, structured responses, streaming, and typed backend errors
- `src/llm/prompts.py` — validated system prompt and conversation history construction
- `tests/test_llm.py` — tests for prompt flow, configuration, responses, streaming, timeouts, and backend failures
- `src/config/settings.py` — persisted LLM URL, model, temperature, token limit, timeout, and system prompt settings
- `src/tts/engine.py` — async Piper TTS engine with voice fallback and playback routing
- `tests/test_tts.py` — 7 tests covering synthesis, playback, errors, and fallback behavior
- `src/stt/engine.py` — `STTEngine` with faster-whisper, configurable model size/language, partial/final callbacks, graceful fallback, audio preprocessing utilities
- `tests/test_stt.py` — 54 tests covering config, state management, transcription, callbacks, error handling, audio validation, compute type resolution, and audio preprocessing
- `src/stt/__init__.py` — exports STTEngine, STTConfig, TranscriptionResult, Segment, STTState
- `src/audio/capture.py` — AudioCapture with PyAudio callback mode, VAD integration, background thread
- `src/audio/playback.py` — `AudioPlayback` with PyAudio write-thread, queue-based non-blocking playback, volume control, and file support
- `src/vision/camera.py` — `CameraCapture` with OpenCV, background thread, callback/queue API, and graceful camera-unavailability handling
- `src/config/settings.py` — NexusConfig with JSON persistence
- `src/ui/settings.py` — CustomTkinter settings window with audio device selection
- `tests/test_audio.py` — 28 audio tests (VAD + capture + playback)
- `tests/test_vision.py` — 11 camera tests
- `tests/test_settings.py` — 7 config tests
- `src/tools/calendar_models.py` — typed Calendar, Event, EventDraft, Attendee, RecurrenceRule, Reminder, Timezone, FreeBusySlot, and CalendarProvider protocol
- `src/tools/calendar_provider.py` — MockCalendarProvider with idempotency, conflict detection, pagination, free/busy, and cancellation support
- `src/tools/calendar_tools.py` — permissioned ListCalendarsTool, ListEventsTool, GetEventTool, FindFreeTimeTool, FindConflictsTool, CreateEventDraftTool, CreateEventTool, UpdateEventTool, and DeleteEventTool
- `src/tools/calendar_factory.py` — create_calendar_registry helper
- `tests/test_calendar_tools.py` — 14 tests covering pagination, DST, conflicts, recurrence, cancellation, errors, idempotency, audit redaction, and model validation
- `src/tools/audit.py` — extended sensitive-key redaction to cover calendar fields (summary, location, description, attendee)
- `src/tools/__init__.py` — exported calendar models, tools, and factory
- `src/memory/models.py` — extended with `ConsentAction`, `ConsentPolicy`, `MemoryAuditRecord`, `pinned` field, and default sensitive-keyword constants
- `src/memory/store.py` — added `delete`, `update_text`, `toggle_pin`, audit log, export by type/scope/time-range, clear by type/scope/time-range, consent policy, and sensitive-keyword detection
- `src/memory/manager.py` — added `consent_policy`, `_check_consent`, `search` with multi-field filters, `delete_memory`, `update_memory`, `toggle_pin`, export/clear delegation, and `generate_self_summary`
- `src/memory/__init__.py` — exported new consent, audit, and manager-level control symbols
- `src/config/settings.py` — added `memory_sensitive_policy`, `memory_consent_audit_log`, and `memory_pinned_ids`
- `src/ui/memory_consent.py` — `MemoryConsentWindow` with search, type/scope/source/sensitivity filters, delete, edit, pin, export, clear-by-type, self-summary, and consent policy selector
- `src/ui/__init__.py` — exported `MemoryConsentWindow` and `open_memory_consent`
- `src/app/contracts.py` — extended `MemoryService` protocol with delete, update, pin, export, clear, and audit-log operations
 - `tests/test_memory_consent.py` — 26 tests covering store mutations, audit, export/clear, consent policies, manager filters, self-summary, and UI module import

**PERSONA-001 implementation:**
- `src/persona/models.py` — `PersonaMode` (companion, balanced, focused), `PersonaSettings` (mode, playfulness, proactivity, response_detail, unsolicited_suggestions, quiet_hours), and `PersonaResponseMetadata` (emotion, voice_energy, confidence, detail_level, should_suggest)
- `src/persona/settings.py` — `PersonaManager` with settings mutation, quiet-hours detection, proactive rate-limiting, persona-aware prompt application, and JSON persistence to `~/.nexus/persona.json`
- `src/persona/__init__.py` — exported persona module symbols
- `src/config/settings.py` — persisted persona_mode, persona_playfulness, persona_proactivity, persona_response_detail, persona_unsolicited_suggestions, persona_quiet_hours_start, persona_quiet_hours_end
- `src/llm/prompts.py` — `apply_persona` standalone helper that injects mode, tone, and detail guidance into system prompts while preserving factual-accuracy requirements
- `src/app/runtime.py` — `NexusRuntime` accepts optional `PersonaManager`, applies persona to LLM system prompt on every text request, emits persona metadata in completion events, and exposes `get_persona_metadata`
- `src/app/factory.py` — constructs `PersonaManager` from `NexusConfig` persona fields and injects it into `NexusRuntime`
- `src/ui/settings.py` — persona section in settings window (mode dropdown, playfulness/proactivity/detail sliders, unsolicited suggestions toggle, quiet-hours start/end entries)
- `tests/test_persona.py` — 27 tests covering settings validation, mode behavior, metadata bounds, quiet hours, proactive rate-limiting, prompt integration, config roundtrip, and persistence

**EVAL-001 implementation:**
- `src/tasks/models.py` — added `SuccessCriterion` (id, description, check_type, expression) and `confidence` field to `Evidence`
- `src/tasks/codec.py` — serializes and deserializes `success_criteria` and evidence `confidence`
- `src/tasks/operations.py` — added `revert_step_for_rework` to return failed steps to PENDING
- `src/tasks/manager.py` — exposes `add_step` success_criteria and `revert_step_for_rework`
- `src/eval/models.py` — `VerificationResult`, `FeedbackSignal`, `FeedbackKind`, `EvaluationRecord`, `EvalMetrics`
- `src/eval/verifier.py` — `StepVerifier` evaluates step success criteria against evidence, computes confidence and failure explanations
- `src/eval/feedback.py` — `FeedbackCollector` supports positive, negative, and explanatory signals with summary stats
- `src/eval/store.py` — append-only JSONL persistence for evaluation records
- `src/eval/metrics.py` — `MetricsTracker` records success rate, corrections, latency, and memory usefulness
- `src/eval/factory.py` — `create_eval_layer` helper
- `src/config/settings.py` — persisted `eval_path`
- `tests/test_eval.py` — verifier, feedback, metrics, persistence, integration with task manager, and rejection of unsupported completion claims

**Key decisions:**
- Store lightweight conversation memory as human-readable JSON without requiring an embedding model
- Rank results with Unicode-aware token-frequency cosine similarity
- Prune stale entries by age and enforce a maximum entry count after writes and loads
- Persist through an atomic temporary-file replacement to reduce corruption risk
- Use direct `httpx` integration with Ollama's local `/api/chat` endpoint
- Keep request construction public and deterministic for testing and future backend adapters
- Map backend connectivity/status errors and timeouts to separate LLM exceptions
- Stream Ollama's newline-delimited JSON response as incremental text chunks
- faster-whisper for STT (faster than OpenAI Whisper, good accuracy)
- Partial/final callback pattern for streaming transcription UX
- Audio preprocessing: normalize RMS, trim silence, resample to 16kHz
- Graceful fallback: ImportError/RuntimeError caught, error callback fired, state set to ERROR
- PyAudio callback mode for non-blocking capture
- soundfile for WAV, pydub for MP3
- CustomTkinter for settings panel
- Config persisted to `~/.nexus/config.json`
- Volume applied as a gain factor on float32 audio
- Graceful degradation when no speakers are available
- Audio device enumeration via PyAudio with "Default" fallback
- OpenCV for camera capture with optional import and graceful fallback
- Camera runs in a daemon thread named `nexus-camera-capture`
- Audio input validation: 1-D float32 mono required, non-empty, finite values only
- compute_type validated per device: int8_float16/int16 honored where supported, invalid values fall back with warning
- Segment confidence renamed to speech_probability (1.0 - no_speech_prob proxy)
- transcribe_stream no longer mutates instance callbacks (thread-safe per-call overrides)

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

**New backlog tasks discovered:** `CORE-001`, `TOOLS-001`, `TOOLS-002`, `TOOLS-003`,
`WEB-001`, `CONNECTOR-001`, `CONNECTOR-002`, `CONNECTOR-003`, `CONNECTOR-004`,
`CONNECTOR-005`, `PLUGIN-001`, `TASKS-001`, `MEM-002`, `MEM-003`, `PERSONA-001`,
`EVAL-001`, `LEARN-001`, `UI-008`, and `ARCH-010`.

**External capability implementation order:**

1. `TASKS-001` — persistent goals and resumable plans
2. `TOOLS-002` — LLM tool selection through the existing registry
3. `TOOLS-003` — sandboxed local development work
4. `WEB-001` — cited web research
5. `CONNECTOR-001` — credential vault and OAuth foundation
6. `CONNECTOR-002` and `CONNECTOR-003` — Gmail and Google Calendar
7. `CONNECTOR-004` and `CONNECTOR-005` — Telegram and LinkedIn-assisted workflows
8. `PLUGIN-001` — third-party MCP and plugin discovery

**TOOLS-002 validation:** 189 tests pass. Ruff and mypy are configured in
`pyproject.toml` but are not installed in the current environment. All new Python files compile,
stay within the project's 150-line limit, and `git diff --check` passes.

**Next Task after merge:** PLUGIN-001 — MCP & Plugin Tool Discovery

**CONNECTOR-003 validation:** 14 Calendar-specific tests pass, covering pagination, DST, conflicts, recurrence, cancellation, errors, idempotency, and audit redaction. Full suite: 247 tests pass.

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
    memory_storage_format: str = "json"
    memory_max_entries: int = 1000
    memory_max_age_days: int = 90
    theme: str = "dark"
    language: str = "et"

    def save(self, path: Path | str | None = None) -> None
    @classmethod
    def load(cls, path: Path | str | None = None) -> NexusConfig
```

### Memory Store API

```python
# src/memory/store.py
class MemoryStore:
    def __init__(
        self,
        path: Path | str,
        *,
        storage_format: str = "json",
        max_entries: int = 1000,
        max_age_days: int | None = 90,
    ): ...
    def add(self, text: str, *, metadata: dict | None = None, ...) -> MemoryEntry
    def search(self, query: str, *, limit: int = 5) -> list[MemoryResult]
    def prune(self, *, now: datetime | None = None, persist: bool = True) -> int
    def save(self) -> None
    def load(self) -> None
```

Storage is a versioned JSON document. Search uses token-frequency cosine similarity;
cleanup combines configurable age retention with a maximum entry count.

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

### STT Engine API

```python
# src/stt/engine.py
class STTConfig:
    model_size: str = "base"
    device: str = "auto"
    compute_type: str = "int8"
    language: str = "auto"
    beam_size: int = 5
    vad_filter: bool = True

class STTEngine:
    def __init__(
        self,
        config: STTConfig | None = None,
        on_partial_transcript: Callable[[str], None] | None = None,
        on_final_transcript: Callable[["TranscriptionResult"], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ): ...

    async def load_model(self) -> None
    async def unload_model(self) -> None
    async def transcribe(
        self,
        audio: np.ndarray,
        *,
        fire_partial: bool = True,
        on_partial: Callable[[str], None] | None = None,
        on_final: Callable[[TranscriptionResult], None] | None = None,
    ) -> TranscriptionResult
    async def transcribe_stream(
        self,
        audio: np.ndarray,
        on_partial: Callable[[str], None] | None = None,
        on_final: Callable[[TranscriptionResult], None] | None = None,
    ) -> TranscriptionResult

    @staticmethod
    def normalize_audio(audio: np.ndarray, target_rms: float = 0.1) -> np.ndarray
    @staticmethod
    def trim_silence(audio: np.ndarray, sample_rate: int = 16000, ...) -> np.ndarray
    @staticmethod
    def resample_to_16khz(audio: np.ndarray, original_sample_rate: int) -> np.ndarray
    @staticmethod
    def preprocess(audio: np.ndarray, sample_rate: int = 16000, ...) -> np.ndarray

    @property
    def state(self) -> STTState
    @property
    def is_ready(self) -> bool

@dataclass
class TranscriptionResult:
    text: str
    language: str
    confidence: float
    segments: list[Segment]
    duration: float

@dataclass
class Segment:
    start: float
    end: float
    text: str
    speech_probability: float
```

---

### TTS Engine API

```python
# src/tts/engine.py
class TTSConfig:
    voice: str = "en_US-lessac-medium"
    speed: float = 1.0
    language: str = "en"
    model_dir: Path = Path("~/.nexus/voices")
    fallback_voice: str | None = None

class TTSEngine:
    async def load_model(self) -> None
    async def unload_model(self) -> None
    async def synthesize(self, text: str) -> SynthesisResult
    async def speak(self, text: str, playback: PlaybackService) -> SynthesisResult
```

Piper is the offline backend. Model loading and synthesis run through `asyncio.to_thread`.
Generated 16-bit WAV is converted to mono `float32` samples for `AudioPlayback.play`.
The configured fallback voice is tried when the primary voice is missing or unsupported.

---

### Main Application Runtime API

```python
# src/app/runtime.py
class RuntimeServices:
    llm: LLMService
    memory: MemoryService | None
    capture: CaptureService | None
    playback: PlaybackService | None
    stt: STTService | None
    tts: TTSService | None

class NexusRuntime:
    def subscribe(self, callback: Callable[[RuntimeEvent], None]) -> None
    def interrupt(self, message: str = "Interrupted") -> RuntimeEvent
    async def start(self) -> None
    async def stop(self) -> None
    async def handle_text(self, text: str) -> str
    async def handle_audio(self, audio: np.ndarray) -> str

def create_runtime(config: NexusConfig | None = None) -> NexusRuntime

class RuntimeStateMachine:
    @property
    def state(self) -> RuntimeState
    def subscribe(self, callback: Callable[[RuntimeEvent], None]) -> None
    def can_transition(self, target: RuntimeState) -> bool
    def transition(self, target: RuntimeState, ...) -> RuntimeEvent
    def interrupt(self, message: str = "Interrupted") -> RuntimeEvent

def face_emotion_for(state: RuntimeState) -> str
```

The state machine supports STOPPED, IDLE, LISTENING, UNDERSTANDING, PLANNING, ACTING,
VERIFYING, SPEAKING, WAITING_CONFIRMATION, BLOCKED, ERROR, and SLEEPING. Every transition is
validated before mutation and emits previous/current state metadata. Optional speech services
degrade independently so text interaction remains usable.

---

### Tool Registry API

```python
class RiskLevel(Enum):
    READ_ONLY = "read_only"
    LOCAL_WRITE = "local_write"
    EXTERNAL = "external"
    DESTRUCTIVE = "destructive"

class ToolRegistry:
    def register(self, tool: Tool) -> None
    def discover(self) -> tuple[ToolDescriptor, ...]
    async def invoke(
        self, request: ToolRequest, *, confirmed: bool = False,
        timeout: float | None = None,
    ) -> ToolResult

def create_project_tool_registry(project_root: Path | str, ...) -> ToolRegistry
```

Built-in tools are `filesystem.list_directory`, `filesystem.read_text`, and `project.inspect`.
Resolved paths must remain within the configured project root. Local-write, external, and
destructive tools require confirmation by default. Every attempted invocation creates a redacted
JSONL audit entry, including rejected, failed, timed-out, and cancelled requests.

---

### LLM Tool-Calling API

```python
class ToolCallingAgent:
    async def run(self, prompt: str) -> ToolAgentRun
    async def resume(self, run: ToolAgentRun, *, confirmed: bool) -> ToolAgentRun

class ToolRunStatus(Enum):
    COMPLETED = "completed"
    WAITING_CONFIRMATION = "waiting_confirmation"
    FAILED = "failed"
```

The agent sends registered JSON function schemas through Ollama's native `tools` field, parses
`message.tool_calls`, executes exclusively through `ToolRegistry`, and returns results as
`role: tool` messages. It rejects parallel calls for now and bounds total calls, repeated-call loops,
timeouts, and cancellation. Confirmation-required calls return a resumable snapshot.

Protocol reference: https://docs.ollama.com/capabilities/tool-calling

---

### Goal & Task Manager API

```python
class TaskManager:
    def create_goal(self, objective: str) -> Goal
    def get_goal(self, goal_id: str) -> Goal
    def list_goals(self) -> tuple[Goal, ...]
    def add_step(self, goal_id: str, title: str, ...) -> PlanStep
    def amend_step(self, goal_id: str, step_id: str, ...) -> PlanStep
    def start_goal(self, goal_id: str) -> None
    def start_step(self, goal_id: str, step_id: str) -> None
    def pause_goal(self, goal_id: str) -> None
    def resume_goal(self, goal_id: str) -> None
    def cancel_goal(self, goal_id: str) -> None
    def block_step(self, goal_id: str, step_id: str, reason: str, ...) -> None
    def resolve_blocker(self, goal_id: str, step_id: str) -> None
    def complete_step(self, goal_id: str, step_id: str, summary: str, evidence=()) -> None
    def fail_step(self, goal_id: str, step_id: str, summary: str) -> None
    def complete_goal(self, goal_id: str) -> None
```

Returned goals are deep copies so callers cannot mutate persisted manager state. After restart,
previously active work becomes paused. Dependency checks gate step start, and verified evidence or a
verified user-confirmation artifact gates successful step completion.

---

### Face Theme API

```python
class FaceTheme(Enum):
    CLASSIC = "classic"
    NEON_BLUE = "neon_blue"
    PIXEL = "pixel"
    RED_ALERT = "red_alert"
    COSMIC = "cosmic"

face = NexusFace(theme=FaceTheme.COSMIC)
face.set_theme("pixel")
svg = face.render("happy")
```

The face server accepts `theme` on render and animate requests and exposes available values through
`GET /api/face/themes`. The animated browser demo includes a theme selector.

---

### Google Calendar Tool API

```python
# src/tools/calendar_models.py
class Event:
    id: str
    summary: str
    description: str
    location: str
    start: datetime
    end: datetime
    timezone: Timezone
    attendees: tuple[Attendee, ...]
    recurrence: tuple[RecurrenceRule, ...]
    reminders: tuple[Reminder, ...]
    status: str
    calendar_id: str

class EventDraft:
    id: str
    summary: str
    start: datetime
    end: datetime
    timezone: Timezone
    attendees: tuple[Attendee, ...]
    recurrence: tuple[RecurrenceRule, ...]
    reminders: tuple[Reminder, ...]
    conflicts: tuple[Event, ...]
    idempotency_key: str

class FreeBusySlot:
    start: datetime
    end: datetime

class CalendarProvider(Protocol):
    async def list_calendars(self) -> tuple[list[Calendar], str | None]: ...
    async def list_events(self, calendar_id: str, *, time_min: datetime, time_max: datetime, page_token: str | None = None) -> tuple[list[Event], str | None]: ...
    async def get_event(self, calendar_id: str, event_id: str) -> Event: ...
    async def create_event_draft(self, draft: EventDraft) -> EventDraft: ...
    async def create_event(self, draft: EventDraft, *, confirmed: bool = False) -> Event: ...
    async def update_event(self, calendar_id: str, event_id: str, *, summary: str | None = None, ...) -> Event: ...
    async def delete_event(self, calendar_id: str, event_id: str) -> None: ...
    async def free_busy(self, request: FreeBusyRequest) -> tuple[list[FreeBusySlot], str | None]: ...
    async def find_conflicts(self, calendar_id: str, event: Event) -> tuple[list[Event], str | None]: ...
```

Tools are exposed through `create_calendar_registry(provider)`. Read-only tools (`list_calendars`,
`list_events`, `get_event`, `find_free_time`, `find_conflicts`) do not require confirmation. Draft
creation (`create_event_draft`) is `LOCAL_WRITE`. Event creation, update, and invite are `EXTERNAL`.
Cancellation (`delete_event`) is `DESTRUCTIVE`. Optional `idempotency_key` on draft creation prevents
duplicate events after retry or resumed tasks.

---

## 7. Completed Tasks

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
| MEM-002 | Structured Multi-Layer Memory | 2026-07-13 | Backend Agent |
| MEM-003 | Memory Consent & Management UI | 2026-07-13 | Backend Agent |
| PERSONA-001 | Persona & Interaction Modes | 2026-07-13 | Integration Agent |
| EVAL-001 | Result Verification & Feedback | 2026-07-13 | Integration Agent |
| LEARN-001 | Safe Reflection & Learning Loop | 2026-07-13 | Integration Agent |

---

### Structured Memory API

```python
# src/memory/models.py
class MemoryType(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PREFERENCE = "preference"
    PROCEDURAL = "procedural"

class MemoryScope(str, Enum):
    GLOBAL = "global"
    PROJECT = "project"
    SESSION = "session"

class SensitivityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class MemorySource(str, Enum):
    USER_STATED = "user_stated"
    ASSISTANT_INFERRED = "assistant_inferred"
    TOOL_OUTPUT = "tool_output"
    EXTERNAL = "external"

@dataclass(frozen=True, slots=True)
class MemoryEntry:
    id: str
    memory_type: MemoryType
    text: str
    source: MemorySource
    confidence: float
    importance: float
    sensitivity: SensitivityLevel
    scope: MemoryScope
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = field(default_factory=dict)
    supersedes: str | None = None
    summary_of: tuple[str, ...] = ()

class MemoryManager:
    def add_working_memory(self, text: str, ...) -> MemoryEntry
    def promote_to_long_term(self, entry_id: str) -> MemoryEntry | None
    def consolidate_duplicates(self) -> list[MemoryEntry]
    def handle_contradiction(self, existing: MemoryEntry, incoming: MemoryEntry) -> ContradictionRecord | None
    def summarize(self, source_ids: tuple[str, ...], summary_text: str) -> MemorySummary | None
    def apply_retention(self, policy: RetentionPolicy | None = None) -> int
    def build_retriever(self, *, embedding_fn=None, ...) -> MemoryRetriever
    def retrieve(self, query: RetrievalQuery, *, embedding_fn=None) -> list[MemoryResult]
```

```python
# src/memory/retrieval.py
class RetrievalQuery:
    text: str
    types: tuple[MemoryType, ...] | None = None
    scope: tuple[str, ...] | None = None
    limit: int = 5
    token_budget: int | None = None
    min_confidence: float = 0.0
    min_importance: float = 0.0

class MemoryRetriever:
    def __init__(self, entries, *, embedding_fn=None, keyword_weight=0.6, embedding_weight=0.4)
    def search(self, query: RetrievalQuery) -> list[MemoryResult]
```

Storage is a versioned JSON document (v1 legacy auto-migrates to v2). Search uses token-frequency cosine similarity as baseline; an optional `embedding_fn` enables hybrid retrieval. Retention policies are type-specific.

### Memory Consent & Management API

```python
# src/memory/models.py
class ConsentAction(str, Enum):
    ASK = "ask"
    ALLOW = "allow"
    NEVER_STORE = "never_store"

@dataclass(frozen=True, slots=True)
class ConsentPolicy:
    action: ConsentAction = ConsentAction.ASK
    sensitive_keywords: tuple[str, ...] = (...)
    ask_prompt: str = "Nexus detected potentially sensitive information..."

@dataclass(frozen=True, slots=True)
class MemoryAuditRecord:
    action: str
    entry_id: str
    timestamp: str
    details: dict[str, Any] = field(default_factory=dict)
```

```python
# src/memory/store.py
class MemoryStore:
    def delete(self, entry_id: str) -> MemoryEntry | None: ...
    def update_text(self, entry_id: str, new_text: str) -> MemoryEntry | None: ...
    def toggle_pin(self, entry_id: str) -> MemoryEntry | None: ...
    def audit_log(self) -> tuple[MemoryAuditRecord, ...]: ...
    def export_by_type(self, memory_type: MemoryType) -> str: ...
    def export_by_scope(self, scope: MemoryScope) -> str: ...
    def export_by_time_range(self, start: datetime, end: datetime) -> str: ...
    def clear_by_type(self, memory_type: MemoryType) -> int: ...
    def clear_by_scope(self, scope: MemoryScope) -> int: ...
    def clear_by_time_range(self, start: datetime, end: datetime) -> int: ...
    def check_consent(self, sensitivity: SensitivityLevel, policy: ConsentPolicy) -> bool: ...
    def contains_sensitive(self, text: str, policy: ConsentPolicy) -> bool: ...
```

```python
# src/memory/manager.py
class MemoryManager:
    def __init__(self, store: MemoryStore, consent_policy: ConsentPolicy | None = None): ...
    def delete_memory(self, entry_id: str) -> MemoryEntry | None: ...
    def update_memory(self, entry_id: str, new_text: str) -> MemoryEntry | None: ...
    def toggle_pin(self, entry_id: str) -> MemoryEntry | None: ...
    def export_by_type(self, memory_type: MemoryType) -> str: ...
    def export_by_scope(self, scope: MemoryScope) -> str: ...
    def export_by_time_range(self, start: datetime, end: datetime) -> str: ...
    def clear_by_type(self, memory_type: MemoryType) -> int: ...
    def clear_by_scope(self, scope: MemoryScope) -> int: ...
    def clear_by_time_range(self, start: datetime, end: datetime) -> int: ...
    def search(self, *, query_text="", types=None, scope_filter=None,
               source_filter=None, sensitivity_filter=None, limit=50) -> list[MemoryEntry]: ...
    def generate_self_summary(self, query: str = "user preferences and facts") -> str: ...
```

```python
# src/ui/memory_consent.py
class MemoryConsentWindow(ctk.CTk):
    def __init__(self, manager: MemoryManager, config: NexusConfig | None = None,
                 on_policy_change: Callable[[ConsentPolicy], None] | None = None): ...

def open_memory_consent(manager: MemoryManager, config: NexusConfig | None = None,
                        on_policy_change: Callable[[ConsentPolicy], None] | None = None) -> MemoryConsentWindow: ...
```

```python
# src/config/settings.py
class NexusConfig:
    memory_sensitive_policy: str = "ask"
    memory_consent_audit_log: str = "~/.nexus/memory_audit.jsonl"
    memory_pinned_ids: list[str] = field(default_factory=list)
```

---

### Persona & Interaction Modes API

```python
# src/persona/models.py
class PersonaMode(str, Enum):
    COMPANION = "companion"
    BALANCED = "balanced"
    FOCUSED = "focused"

@dataclass(frozen=True, slots=True)
class PersonaSettings:
    mode: PersonaMode = PersonaMode.BALANCED
    playfulness: float = 0.5
    proactivity: float = 0.5
    response_detail: float = 0.5
    unsolicited_suggestions: bool = True
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None

@dataclass(frozen=True, slots=True)
class PersonaResponseMetadata:
    emotion: str = "neutral"
    voice_energy: float = 0.5
    confidence: float = 0.8
    detail_level: str = "normal"
    should_suggest: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
```

```python
# src/persona/settings.py
class PersonaManager:
    def __init__(self, settings: PersonaSettings | None = None, path: Path | None = None): ...
    def update(self, **kwargs: Any) -> PersonaSettings: ...
    def set_mode(self, mode: PersonaMode | str) -> PersonaSettings: ...
    def is_quiet_hours(self, *, now: datetime | None = None) -> bool: ...
    def can_send_proactive(self, *, now: datetime | None = None) -> bool: ...
    def mark_proactive_sent(self, *, now: datetime | None = None) -> None: ...
    def response_metadata(self, confidence: float = 0.8) -> PersonaResponseMetadata: ...
    def apply_persona(self, base_prompt: str) -> str: ...
    def save(self, path: Path | str | None = None) -> None: ...
    @classmethod
    def load(cls, path: Path | str | None = None) -> PersonaManager: ...
```

Settings persist to `~/.nexus/persona.json`. Quiet hours use `time.fromisoformat` strings. Proactive rate-limiting uses a minimum interval derived from proactivity. `apply_persona` injects mode-specific tone and detail guidance while preserving factual-accuracy and permission standards.

```python
# src/config/settings.py
class NexusConfig:
    persona_mode: str = "balanced"
    persona_playfulness: float = 0.5
    persona_proactivity: float = 0.5
    persona_response_detail: float = 0.5
    persona_unsolicited_suggestions: bool = True
    persona_quiet_hours_start: str | None = None
    persona_quiet_hours_end: str | None = None
```

Quiet hours are stored as ISO-format `HH:MM:SS` strings in `NexusConfig` and converted to `time` objects for `PersonaManager`.

```python
# src/llm/prompts.py
def apply_persona(base_prompt: str, *, mode: str = "balanced", playfulness: float = 0.5, response_detail: float = 0.5) -> str: ...
```

Standalone helper for persona-aware prompt construction without requiring a full `PersonaManager` instance.

---

### Learning Loop API

```python
# src/learn/models.py
class LessonStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    QUARANTINED = "quarantined"
    REJECTED = "rejected"
    APPLIED = "applied"

class ImprovementTarget(str, Enum):
    CODE = "code"
    PROMPT = "prompt"
    PERMISSION = "permission"
    SAFETY_RULE = "safety_rule"
    TOOL = "tool"
    MEMORY = "memory"

@dataclass(frozen=True, slots=True)
class Lesson:
    id: str
    text: str
    scope: str
    confidence: float
    provenance: tuple[str, ...]
    expected_benefit: str
    status: LessonStatus = LessonStatus.PENDING
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True, slots=True)
class ImprovementProposal:
    id: str
    lesson_id: str
    target: ImprovementTarget
    description: str
    proposed_change: str
    rationale: str
    requires_approval: bool = True
    status: str = "pending"
    created_at: datetime

@dataclass(frozen=True, slots=True)
class QuarantineRecord:
    id: str
    lesson_id: str
    reason: str
    conflicting_lesson_ids: tuple[str, ...] = ()
    created_at: datetime

@dataclass(frozen=True, slots=True)
class DevReport:
    generated_at: str
    total_evaluations: int
    successful_verifications: int
    failed_verifications: int
    lessons_generated: int
    lessons_approved: int
    lessons_quarantined: int
    proposals_pending: int
    summary: str = ""
```

```python
# src/learn/reflection.py
class ReflectionEngine:
    def __init__(self, memory_manager, lesson_store, quarantine: QuarantineManager | None = None) -> None: ...
    def reflect(self, eval_records: list[EvaluationRecord], goals: list[Goal]) -> tuple[list[Lesson], list[ImprovementProposal]]: ...

# src/learn/quarantine.py
class QuarantineManager:
    def evaluate(self, lesson: Lesson, existing_lessons: list[Lesson]) -> QuarantineRecord | None: ...
    def release(self, lesson_id: str) -> None: ...
    def is_quarantined(self, lesson_id: str) -> bool: ...

# src/learn/store.py
class LessonStore:
    def add_lesson(self, lesson: Lesson) -> None: ...
    def add_proposal(self, proposal: ImprovementProposal) -> None: ...
    def add_quarantine(self, record: QuarantineRecord) -> None: ...
    def load_lessons(self) -> list[Lesson]: ...
    def load_proposals(self) -> list[ImprovementProposal]: ...
    def load_quarantine(self) -> list[QuarantineRecord]: ...

# src/learn/report.py
class DevReportGenerator:
    def __init__(self, lesson_store: LessonStore, eval_metrics: EvalMetrics | None = None) -> None: ...
    def generate(self) -> DevReport: ...
```

`ReflectionEngine.reflect` consumes `EvaluationRecord` instances and `Goal` data to produce lessons. Confidence is derived from verification confidence merged with feedback rating. `QuarantineManager` quarantines lessons with confidence below 0.5 or with text conflicts against existing approved lessons. `ImprovementProposal` instances infer a target type from lesson text but are never applied automatically; all changes to code, prompts, permissions, and safety rules require explicit user approval. `DevReportGenerator` produces a local summary from evaluation metrics, lesson counts, and pending proposals. Configuration key `learning_path` defaults to `~/.nexus/learning`.

---

Consent policies control whether sensitive memories are stored (`ask` prompts, `allow` stores unconditionally, `never_store` blocks). Every mutation appends a redacted `MemoryAuditRecord` to the in-memory audit log. The UI exposes search, filter, edit, delete, pin, export, and bulk-clear operations.

---

> **Last updated:** 2026-07-13
> **Maintainer:** Documentation Agent
