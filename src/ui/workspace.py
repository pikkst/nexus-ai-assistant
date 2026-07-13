"""Unified companion workspace for Nexus.

Combines animated face, conversation, runtime state, active plan, tool activity,
evidence, confirmations, memory controls, and settings in one CustomTkinter window.

Layout modes:
- companion: spacious face, friendly panels, side panels collapsible
- balanced: face left, transcript center, plan/tools/evidence right
- focused: minimal chrome, transcript dominant, panels minimized
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import customtkinter as ctk

from src.app.contracts import MemoryService
from src.app.events import RuntimeEvent, RuntimeState
from src.app.face_state import face_emotion_for
from src.config.settings import NexusConfig
from src.tasks.manager import TaskManager
from src.tools.models import RiskLevel
from src.ui.face import Emotion, FaceConfig, FaceState, NexusFace
from src.ui.memory_consent import MemoryConsentWindow, open_memory_consent
from src.ui.settings import open_settings

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

logger = logging.getLogger(__name__)


class WorkspaceLayout(Enum):
    COMPANION = "companion"
    BALANCED = "balanced"
    FOCUSED = "focused"


_RISK_COLORS = {
    RiskLevel.READ_ONLY: "#4ecdc4",
    RiskLevel.LOCAL_WRITE: "#ffe66d",
    RiskLevel.EXTERNAL: "#ff9f43",
    RiskLevel.DESTRUCTIVE: "#ff6b6b",
}

_RISK_LABELS = {
    RiskLevel.READ_ONLY: "Lugemine",
    RiskLevel.LOCAL_WRITE: "Kohalik kirjutamine",
    RiskLevel.EXTERNAL: "Väline",
    RiskLevel.DESTRUCTIVE: "Kriitiline",
}

_STATE_COLORS = {
    RuntimeState.STOPPED: "#55556a",
    RuntimeState.IDLE: "#4ecdc4",
    RuntimeState.LISTENING: "#6ec6ff",
    RuntimeState.UNDERSTANDING: "#a29bfe",
    RuntimeState.PLANNING: "#ffe66d",
    RuntimeState.ACTING: "#ff9f43",
    RuntimeState.VERIFYING: "#a29bfe",
    RuntimeState.SPEAKING: "#ff6b8a",
    RuntimeState.WAITING_CONFIRMATION: "#ffe66d",
    RuntimeState.BLOCKED: "#ff6b6b",
    RuntimeState.ERROR: "#ff6b6b",
    RuntimeState.SLEEPING: "#55556a",
}


@dataclass(slots=True)
class TranscriptEntry:
    role: str
    text: str
    ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class ToolActivityEntry:
    name: str
    risk: str
    status: str
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    error: str | None = None


@dataclass(slots=True)
class EvidenceEntry:
    kind: str
    summary: str
    verified: bool = False
    confidence: float = 1.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class FacePanel(ctk.CTkFrame):
    def __init__(self, master: ctk.CTk | ctk.CTkFrame, **kw: Any) -> None:
        super().__init__(master, **kw)
        self.face = NexusFace()
        self._container = ctk.CTkFrame(self, fg_color="transparent")
        self._container.pack(fill="both", expand=True)
        self._label = ctk.CTkLabel(self._container, text="", anchor="center")
        self._label.pack(fill="both", expand=True)
        self._emotion = Emotion.IDLE
        self._animating = False
        self._after_id: str | None = None

    def set_emotion(self, emotion: Emotion | str) -> None:
        self._emotion = Emotion(emotion) if isinstance(emotion, str) else emotion
        svg = self.face.render(self._emotion)
        self._label.configure(text=svg)

    def start_animation(self) -> None:
        if self._animating:
            return
        self._animating = True
        self._animate()

    def stop_animation(self) -> None:
        self._animating = False
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None

    def _animate(self) -> None:
        if not self._animating:
            return
        svg = self.face.animate(dt=0.05)
        self._label.configure(text=svg)
        self._after_id = self.after(50, self._animate)


class TranscriptPanel(ctk.CTkFrame):
    def __init__(self, master: ctk.CTk | ctk.CTkFrame, **kw: Any) -> None:
        super().__init__(master, **kw)
        self._entries: list[TranscriptEntry] = []
        self._build_ui()

    def _build_ui(self) -> None:
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(top, text="Vestlus", font=("Arial", 14, "bold")).pack(side="left")
        self._status = ctk.CTkLabel(top, text="", text_color="#888899", font=("Arial", 11))
        self._status.pack(side="right")
        self._text = ctk.CTkTextbox(self, wrap="word", font=("Arial", 12), height=200)
        self._text.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._text.configure(state="disabled")
        entry_frame = ctk.CTkFrame(self, fg_color="transparent")
        entry_frame.pack(fill="x", padx=8, pady=(0, 8))
        self._entry = ctk.CTkEntry(entry_frame, placeholder_text="Kirjuta sõnum...")
        self._entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self._entry.bind("<Return>", lambda _e: self._send())
        send_btn = ctk.CTkButton(entry_frame, text="Saada", width=80, command=self._send)
        send_btn.pack(side="right")

    def _send(self) -> None:
        text = self._entry.get().strip()
        if not text:
            return
        self._entry.delete(0, "end")
        if self._on_send:
            self._on_send(text)

    def add_user(self, text: str) -> None:
        self._add("Kasutaja", text, "#6ec6ff")

    def add_assistant(self, text: str) -> None:
        self._add("Nexus", text, "#a29bfe")

    def add_system(self, text: str) -> None:
        self._add("Süsteem", text, "#888899")

    def _add(self, role: str, text: str, color: str) -> None:
        self._entries.append(TranscriptEntry(role=role, text=text))
        self._text.configure(state="normal")
        tag = f"c{len(self._entries)}"
        self._text.insert("end", f"{role}: ", (tag,))
        self._text.insert("end", f"{text}\n\n", (tag,))
        self._text.tag_config(tag, foreground=color)
        self._text.see("end")
        self._text.configure(state="disabled")

    def set_status(self, text: str) -> None:
        self._status.configure(text=text)

    on_send: Callable[[str], None] | None = None


class PlanPanel(ctk.CTkFrame):
    def __init__(self, master: ctk.CTk | ctk.CTkFrame, **kw: Any) -> None:
        super().__init__(master, **kw)
        self._goal: Any = None
        self._build_ui()

    def _build_ui(self) -> None:
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(top, text="Aktiivne ülesanne", font=("Arial", 14, "bold")).pack(side="left")
        self._goal_label = ctk.CTkLabel(self, text="Aktiivne eesmärk pole", anchor="w", text_color="#888899")
        self._goal_label.pack(fill="x", padx=8, pady=(0, 6))
        self._steps = ctk.CTkScrollableFrame(self, height=160)
        self._steps.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def set_goal(self, goal: Any) -> None:
        self._goal = goal
        if goal is None:
            self._goal_label.configure(text="Aktiivne eesmärk pole")
            return
        self._goal_label.configure(text=goal.objective)
        for child in self._steps.winfo_children():
            child.destroy()
        for step in goal.steps:
            step_frame = ctk.CTkFrame(self._steps, fg_color="#1e1e38", corner_radius=6)
            step_frame.pack(fill="x", pady=2)
            status_text = step.status.value.upper()
            ctk.CTkLabel(
                step_frame, text=f"[{status_text}] {step.title}",
                anchor="w", font=("Arial", 11),
            ).pack(fill="x", padx=6, pady=3)
            if step.blocker:
                ctk.CTkLabel(
                    step_frame, text=f"Blocked: {step.blocker.reason}",
                    anchor="w", text_color="#ff6b6b", font=("Arial", 10),
                ).pack(fill="x", padx=6, pady=(0, 3))


class ToolsPanel(ctk.CTkFrame):
    def __init__(self, master: ctk.CTk | ctk.CTkFrame, **kw: Any) -> None:
        super().__init__(master, **kw)
        self._entries: list[ToolActivityEntry] = []
        self._build_ui()

    def _build_ui(self) -> None:
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(top, text="Tööriistade aktiivsus", font=("Arial", 14, "bold")).pack(side="left")
        self._list = ctk.CTkScrollableFrame(self, height=160)
        self._list.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def add_tool(self, name: str, risk: RiskLevel, status: str, error: str | None = None) -> None:
        entry = ToolActivityEntry(name=name, risk=risk.value, status=status, error=error)
        self._entries.append(entry)
        if len(self._entries) > 50:
            self._entries.pop(0)
        self._render_row(entry)

    def _render_row(self, entry: ToolActivityEntry) -> None:
        row = ctk.CTkFrame(self._list, fg_color="#1e1e38", corner_radius=6)
        row.pack(fill="x", pady=2)
        color = _RISK_COLORS.get(RiskLevel(entry.risk), "#888899")
        risk_text = _RISK_LABELS.get(RiskLevel(entry.risk), entry.risk)
        ctk.CTkLabel(
            row, text=f"{entry.name} [{risk_text}] — {entry.status}",
            anchor="w", font=("Arial", 11), text_color=color,
        ).pack(fill="x", padx=6, pady=3)
        if entry.error:
            ctk.CTkLabel(
                row, text=f"Viga: {entry.error}",
                anchor="w", text_color="#ff6b6b", font=("Arial", 10),
            ).pack(fill="x", padx=6, pady=(0, 3))


class EvidencePanel(ctk.CTkFrame):
    def __init__(self, master: ctk.CTk | ctk.CTkFrame, **kw: Any) -> None:
        super().__init__(master, **kw)
        self._entries: list[EvidenceEntry] = []
        self._build_ui()

    def _build_ui(self) -> None:
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(top, text="Kinnitused ja tõendid", font=("Arial", 14, "bold")).pack(side="left")
        self._list = ctk.CTkScrollableFrame(self, height=120)
        self._list.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def add_evidence(self, kind: str, summary: str, verified: bool = False, confidence: float = 1.0) -> None:
        entry = EvidenceEntry(kind=kind, summary=summary, verified=verified, confidence=confidence)
        self._entries.append(entry)
        row = ctk.CTkFrame(self._list, fg_color="#1e1e38", corner_radius=6)
        row.pack(fill="x", pady=2)
        status_text = "Kinnitatud" if verified else "Ootel"
        color = "#4ecdc4" if verified else "#ffe66d"
        ctk.CTkLabel(
            row, text=f"[{status_text}] {kind}: {summary}",
            anchor="w", font=("Arial", 11), text_color=color,
        ).pack(fill="x", padx=6, pady=3)
        if not verified:
            ctk.CTkLabel(
                row, text=f"Usaldus: {confidence:.0%}",
                anchor="w", text_color="#888899", font=("Arial", 10),
            ).pack(fill="x", padx=6, pady=(0, 3))


class ConfirmationDialog(ctk.CTkToplevel):
    def __init__(self, master: ctk.CTk | ctk.CTkFrame, title: str, action: str, scope: str, risk: RiskLevel, on_confirm: Callable[[bool], None]) -> None:
        super().__init__(master)
        self._on_confirm = on_confirm
        self.title("Nõusoleku küsimine")
        self.geometry("440x220")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        ctk.CTkLabel(self, text=title, font=("Arial", 16, "bold")).pack(anchor="w", padx=16, pady=(16, 8))
        ctk.CTkLabel(self, text=f"Tegevus: {action}", anchor="w").pack(fill="x", padx=16)
        ctk.CTkLabel(self, text=f"Ulatus: {scope}", anchor="w", text_color="#888899").pack(fill="x", padx=16, pady=(0, 8))
        risk_label = _RISK_LABELS.get(risk, risk.value)
        risk_color = _RISK_COLORS.get(risk, "#888899")
        ctk.CTkLabel(self, text=f"Risk: {risk_label}", anchor="w", text_color=risk_color).pack(fill="x", padx=16, pady=(0, 12))
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkButton(btn_frame, text="Loobu", fg_color="#55556a", command=lambda: self._done(False)).pack(side="right", padx=(4, 0))
        ctk.CTkButton(btn_frame, text="Nõus", fg_color="#4ecdc4", command=lambda: self._done(True)).pack(side="right")

    def _done(self, confirmed: bool) -> None:
        self.grab_release()
        self.destroy()
        self._on_confirm(confirmed)


class WorkspaceApp(ctk.CTk):
    def __init__(self, runtime: Any | None = None, config: NexusConfig | None = None) -> None:
        super().__init__()
        self.config = config or NexusConfig.load()
        self._runtime = runtime
        self._layout = WorkspaceLayout(self.config.persona_mode if hasattr(self.config, 'persona_mode') else "balanced")
        self._transcript: list[TranscriptEntry] = []
        self._tool_entries: list[ToolActivityEntry] = []
        self._evidence_entries: list[EvidenceEntry] = []
        self._muted = False
        self._task_manager: TaskManager | None = None
        self._memory: MemoryService | None = None
        self._current_goal: Any = None
        self._pending_confirmations: list[dict[str, Any]] = []
        self._loop: asyncio.AbstractEventLoop | None = None
        self._build_ui()
        self._apply_layout()
        if self._runtime is not None:
            self._runtime.subscribe(self._on_runtime_event)

    def _build_ui(self) -> None:
        self.title("Nexus — Unified Workspace")
        self.geometry("1200x800")
        self.minsize(900, 600)
        self._sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self._sidebar.pack(side="left", fill="y")
        self._main = ctk.CTkFrame(self, corner_radius=0)
        self._main.pack(side="right", fill="both", expand=True)
        self._build_sidebar()
        self._build_main()

    def _build_sidebar(self) -> None:
        ctk.CTkLabel(self._sidebar, text="NEXUS", font=("Arial", 22, "bold")).pack(anchor="w", padx=16, pady=(16, 4))
        ctk.CTkLabel(self._sidebar, text="Unified Workspace", text_color="#888899").pack(anchor="w", padx=16, pady=(0, 16))
        self._state_label = ctk.CTkLabel(self._sidebar, text="IDLE", font=("Arial", 18, "bold"), text_color="#4ecdc4")
        self._state_label.pack(anchor="w", padx=16, pady=(0, 16))
        self._mode_label = ctk.CTkLabel(self._sidebar, text=f"Režiim: {self._layout.value}", text_color="#888899")
        self._mode_label.pack(anchor="w", padx=16, pady=(0, 20))
        ctk.CTkButton(self._sidebar, text="Peata kõne", command=self._interrupt).pack(fill="x", padx=16, pady=4)
        ctk.CTkButton(self._sidebar, text="Tühista töö", command=self._cancel_work).pack(fill="x", padx=16, pady=4)
        self._mute_btn = ctk.CTkButton(self._sidebar, text="Vaigista andurid", command=self._toggle_mute)
        self._mute_btn.pack(fill="x", padx=16, pady=4)
        ctk.CTkButton(self._sidebar, text="Mälu juhtimine", command=self._open_memory).pack(fill="x", padx=16, pady=4)
        ctk.CTkButton(self._sidebar, text="Seaded", command=self._open_settings).pack(fill="x", padx=16, pady=4)
        ctk.CTkButton(self._sidebar, text="Välju", fg_color="#ff6b6b", command=self._quit).pack(fill="x", padx=16, pady=(20, 16))
        self._confirm_section = ctk.CTkScrollableFrame(self._sidebar, height=200)
        self._confirm_section.pack(fill="x", padx=8, pady=(0, 8))
        ctk.CTkLabel(self._confirm_section, text="Nõusolekud", font=("Arial", 12, "bold")).pack(anchor="w", padx=8, pady=(0, 4))

    def _build_main(self) -> None:
        self._face_panel = FacePanel(self._main)
        self._transcript_panel = TranscriptPanel(self._main)
        self._plan_panel = PlanPanel(self._main)
        self._tools_panel = ToolsPanel(self._main)
        self._evidence_panel = EvidencePanel(self._main)
        self._status_bar = ctk.CTkFrame(self._main, height=32)
        self._status_bar.pack(fill="x", side="bottom")
        self._status_label = ctk.CTkLabel(self._status_bar, text="Nexus valmis", anchor="w")
        self._status_label.pack(fill="x", padx=12, pady=4)

    def _apply_layout(self) -> None:
        mode = self._layout
        for child in self._main.winfo_children():
            child.pack_forget()
        if mode == WorkspaceLayout.COMPANION:
            self._face_panel.pack(fill="both", expand=True, padx=8, pady=8)
            self._transcript_panel.pack(fill="x", side="bottom", padx=8, pady=(0, 8))
            self._plan_panel.pack_forget()
            self._tools_panel.pack_forget()
            self._evidence_panel.pack_forget()
        elif mode == WorkspaceLayout.BALANCED:
            left = ctk.CTkFrame(self._main, fg_color="transparent")
            left.pack(side="left", fill="both", expand=True, padx=8, pady=8)
            right = ctk.CTkFrame(self._main, width=320)
            right.pack(side="right", fill="y", padx=(0, 8), pady=8)
            self._face_panel.pack(in_=left, fill="both", expand=True)
            self._transcript_panel.pack(in_=left, fill="x", side="bottom", pady=(8, 0))
            self._plan_panel.pack(in_=right, fill="x", pady=(0, 4))
            self._tools_panel.pack(in_=right, fill="x", pady=4)
            self._evidence_panel.pack(in_=right, fill="x", pady=(4, 0))
        else:
            self._face_panel.configure(height=180)
            self._face_panel.pack(fill="x", padx=8, pady=(8, 4))
            self._transcript_panel.pack(fill="both", expand=True, padx=8, pady=4)
            self._plan_panel.pack_forget()
            self._tools_panel.pack_forget()
            self._evidence_panel.pack_forget()
        self._mode_label.configure(text=f"Režiim: {mode.value}")

    def _on_runtime_event(self, event: RuntimeEvent) -> None:
        self.after(0, lambda: self._handle_runtime_event(event))

    def _handle_runtime_event(self, event: RuntimeEvent) -> None:
        state = event.state
        emotion = face_emotion_for(state)
        self._face_panel.set_emotion(emotion)
        color = _STATE_COLORS.get(state, "#888899")
        self._state_label.configure(text=state.value.upper(), text_color=color)
        self._status_label.configure(text=event.message or state.value)
        self._transcript_panel.set_status(event.message or state.value)
        if state == RuntimeState.LISTENING:
            self._face_panel.start_animation()
        elif state in (RuntimeState.IDLE, RuntimeState.STOPPED, RuntimeState.SLEEPING):
            self._face_panel.stop_animation()
        if state == RuntimeState.SPEAKING and self._muted:
            self.after(0, self._interrupt)

    def set_runtime(self, runtime: Any) -> None:
        self._runtime = runtime
        runtime.subscribe(self._on_runtime_event)

    def set_task_manager(self, manager: TaskManager) -> None:
        self._task_manager = manager
        manager.subscribe(self._on_task_event)

    def set_memory(self, memory: MemoryService) -> None:
        self._memory = memory

    def _on_task_event(self, event: Any) -> None:
        self.after(0, self._refresh_plan)

    def _refresh_plan(self) -> None:
        if self._task_manager is None:
            return
        goals = self._task_manager.list_goals()
        active = next((g for g in goals if g.status.value in ("active", "paused", "waiting", "blocked")), None)
        self._current_goal = active
        if active is not None:
            self._plan_panel.set_goal(active)

    def add_tool_activity(self, name: str, risk: RiskLevel, status: str, error: str | None = None) -> None:
        self.after(0, lambda: self._tools_panel.add_tool(name, risk, status, error))

    def add_evidence(self, kind: str, summary: str, verified: bool = False, confidence: float = 1.0) -> None:
        self.after(0, lambda: self._evidence_panel.add_evidence(kind, summary, verified, confidence))

    def request_confirmation(self, title: str, action: str, scope: str, risk: RiskLevel, on_confirm: Callable[[bool], None]) -> None:
        self.after(0, lambda: ConfirmationDialog(self, title, action, scope, risk, on_confirm))

    def _interrupt(self) -> None:
        if self._runtime is not None:
            event = self._runtime.interrupt()
            self._handle_runtime_event(event)
        self._transcript_panel.add_system("Kõne katkestatud")

    def _cancel_work(self) -> None:
        if self._task_manager is not None and self._current_goal is not None:
            self._task_manager.cancel_goal(self._current_goal.id)
            self._refresh_plan()
        self._transcript_panel.add_system("Töö tühistatud")
        if self._runtime is not None:
            event = self._runtime.interrupt()
            self._handle_runtime_event(event)

    def _toggle_mute(self) -> None:
        self._muted = not self._muted
        label = "Luba andurid" if self._muted else "Vaigista andurid"
        self._mute_btn.configure(text=label)

    def _open_memory(self) -> None:
        open_memory_consent()

    def _open_settings(self) -> None:
        def on_save(config: NexusConfig) -> None:
            mode = getattr(config, "persona_mode", "balanced")
            try:
                self._layout = WorkspaceLayout(mode)
            except ValueError:
                self._layout = WorkspaceLayout.BALANCED
            self._apply_layout()
        open_settings(on_save=on_save)

    def _quit(self) -> None:
        if self._runtime is not None:
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                pass
        self.destroy()

    def run(self) -> None:
        self.mainloop()


def create_workspace(runtime: Any | None = None, config: NexusConfig | None = None, task_manager: TaskManager | None = None, memory: MemoryService | None = None) -> WorkspaceApp:
    app = WorkspaceApp(runtime=runtime, config=config)
    if task_manager is not None:
        app.set_task_manager(task_manager)
    if memory is not None:
        app.set_memory(memory)
    return app
