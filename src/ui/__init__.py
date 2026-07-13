#  
"""Nexus user-interface components."""

import tkinter
import customtkinter


def _patch_customtkinter_click_animation() -> None:
    try:
        from customtkinter.windows.widgets.ctk_button import CTkButton

        original_on_release = CTkButton._on_release

        def _safe_on_release(self, event=None):
            try:
                original_on_release(self, event)
            except tkinter.TclError:
                pass

        CTkButton._on_release = _safe_on_release
    except Exception:
        pass


_patch_customtkinter_click_animation()

from .face import Emotion, FaceConfig, FaceState, NexusFace
from .face_themes import FaceTheme
from .memory_consent import MemoryConsentWindow, open_memory_consent
from .settings import open_settings
from .workspace import (
    EvidenceEntry,
    EvidencePanel,
    FacePanel,
    PlanPanel,
    TranscriptEntry,
    TranscriptPanel,
    ToolActivityEntry,
    ToolsPanel,
    WorkspaceApp,
    WorkspaceLayout,
    create_workspace,
)

__all__ = [
    "Emotion",
    "EvidenceEntry",
    "EvidencePanel",
    "FaceConfig",
    "FacePanel",
    "FaceState",
    "FaceTheme",
    "MemoryConsentWindow",
    "NexusFace",
    "PlanPanel",
    "TranscriptEntry",
    "TranscriptPanel",
    "ToolActivityEntry",
    "ToolsPanel",
    "WorkspaceApp",
    "WorkspaceLayout",
    "create_workspace",
    "open_memory_consent",
    "open_settings",
]
