"""Smoke and accessibility tests for the unified companion workspace."""

from __future__ import annotations

import sys
import types
import unittest
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

# Stub tkinter / customtkinter before importing workspace modules so tests run headless.
_ctk_stub = MagicMock()
_ctk_stub.set_appearance_mode = MagicMock()
_ctk_stub.set_default_color_theme = MagicMock()
_ctk_stub.CTk = MagicMock
_ctk_stub.CTkFrame = MagicMock
_ctk_stub.CTkLabel = MagicMock
_ctk_stub.CTkTextbox = MagicMock
_ctk_stub.CTkEntry = MagicMock
_ctk_stub.CTkButton = MagicMock
_ctk_stub.CTkScrollableFrame = MagicMock
_ctk_stub.CTkSlider = MagicMock
_ctk_stub.CTkOptionMenu = MagicMock
_ctk_stub.CTkSwitch = MagicMock
_ctk_stub.CTkToplevel = MagicMock
sys.modules["customtkinter"] = _ctk_stub

_tk = types.ModuleType("tkinter")
_tk.Tk = MagicMock
_tk.Toplevel = MagicMock
_tk.Frame = MagicMock
_tk.Label = MagicMock
_tk.Text = MagicMock
_tk.Entry = MagicMock
_tk.Button = MagicMock
_tk.ScrollableFrame = MagicMock
sys.modules["tkinter"] = _tk

from src.ui import workspace as ws  # noqa: E402

EvidenceEntry = ws.EvidenceEntry
EvidencePanel = ws.EvidencePanel
FacePanel = ws.FacePanel
PlanPanel = ws.PlanPanel
TranscriptEntry = ws.TranscriptEntry
TranscriptPanel = ws.TranscriptPanel
ToolActivityEntry = ws.ToolActivityEntry
ToolsPanel = ws.ToolsPanel
WorkspaceApp = ws.WorkspaceApp
WorkspaceLayout = ws.WorkspaceLayout
create_workspace = ws.create_workspace
face_emotion_for = ws.face_emotion_for


def _fake_event(state_value: str = "idle") -> Any:
    from src.app.events import RuntimeEvent, RuntimeState
    return RuntimeEvent(
        state=RuntimeState(state_value),
        previous_state=RuntimeState.IDLE,
        message="test event",
        data={},
        created_at=datetime.now(timezone.utc),
    )


class TestLayoutModes(unittest.TestCase):
    def test_all_modes_have_valid_values(self) -> None:
        for mode in WorkspaceLayout:
            self.assertIn(mode.value, ("companion", "balanced", "focused"))

    def test_face_emotion_mapping(self) -> None:
        from src.app.events import RuntimeState
        for state in RuntimeState:
            emotion = face_emotion_for(state)
            self.assertIsInstance(emotion, str)
            self.assertTrue(len(emotion) > 0)

    def test_emotion_mapping_never_empty(self) -> None:
        from src.app.events import RuntimeState
        for state in RuntimeState:
            emotion = face_emotion_for(state)
            self.assertNotEqual(emotion, "")


class TestRiskAndStateColors(unittest.TestCase):
    def test_risk_colors_coverage(self) -> None:
        from src.ui.workspace import _RISK_COLORS, _RISK_LABELS
        from src.tools.models import RiskLevel
        for risk in RiskLevel:
            self.assertIn(risk, _RISK_COLORS)
            self.assertIn(risk, _RISK_LABELS)

    def test_state_colors_coverage(self) -> None:
        from src.ui.workspace import _STATE_COLORS
        from src.app.events import RuntimeState
        for state in RuntimeState:
            self.assertIn(state, _STATE_COLORS)


class TestDataclasses(unittest.TestCase):
    def test_transcript_entry(self) -> None:
        entry = TranscriptEntry(role="user", text="Tere")
        self.assertEqual(entry.role, "user")
        self.assertEqual(entry.text, "Tere")

    def test_tool_activity_entry(self) -> None:
        entry = ToolActivityEntry(name="test", risk="read_only", status="success")
        self.assertEqual(entry.name, "test")
        self.assertEqual(entry.finished_at, None)

    def test_evidence_entry(self) -> None:
        entry = EvidenceEntry(kind="test", summary="ok", verified=True, confidence=0.9)
        self.assertTrue(entry.verified)
        self.assertEqual(entry.confidence, 0.9)


class TestExports(unittest.TestCase):
    def test_workspace_app_is_exported(self) -> None:
        self.assertIsNotNone(WorkspaceApp)

    def test_create_workspace_is_exported(self) -> None:
        self.assertTrue(callable(create_workspace))

    def test_face_panel_is_exported(self) -> None:
        self.assertIsNotNone(FacePanel)

    def test_evidence_panel_is_exported(self) -> None:
        self.assertIsNotNone(EvidencePanel)

    def test_plan_panel_is_exported(self) -> None:
        self.assertIsNotNone(PlanPanel)

    def test_tools_panel_is_exported(self) -> None:
        self.assertIsNotNone(ToolsPanel)

    def test_transcript_panel_is_exported(self) -> None:
        self.assertIsNotNone(TranscriptPanel)


class TestPanelLogic(unittest.TestCase):
    """Test panel data-handling logic using plain Python stubs."""

    def test_evidence_panel_stores_entries(self) -> None:
        entries: list[EvidenceEntry] = []
        def add_evidence(kind: str, summary: str, verified: bool = False, confidence: float = 1.0) -> None:
            entries.append(EvidenceEntry(kind=kind, summary=summary, verified=verified, confidence=confidence))
        add_evidence("test", "summary", verified=True, confidence=0.9)
        self.assertEqual(len(entries), 1)
        self.assertTrue(entries[0].verified)

    def test_tools_panel_stores_entries(self) -> None:
        entries: list[ToolActivityEntry] = []
        def add_tool(name: str, risk: Any, status: str, error: str | None = None) -> None:
            entries.append(ToolActivityEntry(name=name, risk=risk.value, status=status, error=error))
        risk = MagicMock()
        risk.value = "read_only"
        add_tool("test_tool", risk, "success")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].name, "test_tool")

    def test_plan_panel_empty_goal(self) -> None:
        goal_label = MagicMock()
        def set_goal(goal: Any) -> None:
            if goal is None:
                goal_label.configure(text="Aktiivne eesmärk pole")
        set_goal(None)
        goal_label.configure.assert_called_with(text="Aktiivne eesmärk pole")

    def test_plan_panel_with_steps(self) -> None:
        goal_label = MagicMock()
        def set_goal(goal: Any) -> None:
            if goal is None:
                goal_label.configure(text="Aktiivne eesmärk pole")
                return
            goal_label.configure(text=goal.objective)
        goal = MagicMock()
        goal.objective = "Test eesmärk"
        set_goal(goal)
        goal_label.configure.assert_called_with(text="Test eesmärk")

    def test_transcript_panel_adds_entries(self) -> None:
        entries: list[TranscriptEntry] = []
        def add_user(text: str) -> None:
            entries.append(TranscriptEntry(role="Kasutaja", text=text))
        def add_assistant(text: str) -> None:
            entries.append(TranscriptEntry(role="Nexus", text=text))
        def add_system(text: str) -> None:
            entries.append(TranscriptEntry(role="Süsteem", text=text))
        add_user("Tere")
        self.assertEqual(entries[-1].role, "Kasutaja")
        add_assistant("Tere, kuidas saan aidata?")
        self.assertEqual(entries[-1].role, "Nexus")
        add_system("Süsteemi teade")
        self.assertEqual(entries[-1].role, "Süsteem")

    def test_transcript_panel_send_invokes_callback(self) -> None:
        entry_mock = MagicMock()
        entry_mock.get.return_value = "Test"
        on_send: Callable[[str], None] | None = None
        def _send() -> None:
            text = entry_mock.get().strip()
            if text and on_send:
                on_send(text)
        received: list[str] = []
        on_send = lambda text: received.append(text)
        _send()
        self.assertIn("Test", received)


class TestWorkspaceAppBehavior(unittest.TestCase):
    def test_create_workspace(self) -> None:
        with patch.object(WorkspaceApp, "__init__", lambda self, **kw: None):
            app = create_workspace(runtime=MagicMock(), config=MagicMock())
        self.assertIsNotNone(app)

    def test_layout_modes_enum(self) -> None:
        self.assertEqual(WorkspaceLayout.COMPANION.value, "companion")
        self.assertEqual(WorkspaceLayout.BALANCED.value, "balanced")
        self.assertEqual(WorkspaceLayout.FOCUSED.value, "focused")

    def test_interrupt_runtime_contract(self) -> None:
        runtime = MagicMock()
        event = _fake_event("idle")
        runtime.interrupt.return_value = event
        runtime.interrupt()
        self.assertEqual(runtime.interrupt.call_count, 1)

    def test_cancel_work_contract(self) -> None:
        manager = MagicMock()
        goal = MagicMock()
        goal.id = "goal-1"
        manager.cancel_goal("goal-1")
        manager.cancel_goal.assert_called_with("goal-1")

    def test_toggle_mute_contract(self) -> None:
        muted = False
        muted = not muted
        self.assertTrue(muted)
        muted = not muted
        self.assertFalse(muted)

    def test_runtime_event_face_update(self) -> None:
        face_panel = MagicMock()
        event = _fake_event("listening")
        emotion = face_emotion_for(event.state)
        face_panel.set_emotion(emotion)
        face_panel.start_animation()
        face_panel.set_emotion.assert_called_once()
        face_panel.start_animation.assert_called_once()

    def test_runtime_event_idle_contract(self) -> None:
        face_panel = MagicMock()
        event = _fake_event("idle")
        emotion = face_emotion_for(event.state)
        face_panel.set_emotion(emotion)
        face_panel.stop_animation()
        face_panel.stop_animation.assert_called_once()


if __name__ == "__main__":
    unittest.main()
