"""
Nexus Memory Consent & Management UI.

CustomTkinter-based window for inspecting, editing, deleting, pinning,
exporting, and clearing memories, plus configuring sensitive-data consent.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import customtkinter as ctk

from src.config.settings import NexusConfig
from src.memory import (
    ConsentAction,
    ConsentPolicy,
    MemoryEntry,
    MemoryManager,
    MemoryScope,
    MemorySource,
    MemoryType,
    SensitivityLevel,
)

logger = logging.getLogger(__name__)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

MEMORY_TYPES = [t.value for t in MemoryType]
SCOPES = [s.value for s in MemoryScope]
SOURCES = [s.value for s in MemorySource]
SENSITIVITIES = [s.value for s in SensitivityLevel]
CONSENT_ACTIONS = [a.value for a in ConsentAction]


class MemoryConsentWindow(ctk.CTk):
    """Memory consent and management window."""

    def __init__(
        self,
        manager: MemoryManager,
        config: NexusConfig | None = None,
        on_policy_change: Callable[[ConsentPolicy], None] | None = None,
    ) -> None:
        super().__init__()
        self.manager = manager
        self.config = config or NexusConfig.load()
        self._on_policy_change = on_policy_change
        self.title("Nexus — Mälu seaded")
        self.geometry("900x700")
        self.resizable(True, True)

        self._filter_type = ctk.StringVar(value="")
        self._filter_scope = ctk.StringVar(value="")
        self._filter_source = ctk.StringVar(value="")
        self._filter_sensitivity = ctk.StringVar(value="")
        self._search_var = ctk.StringVar(value="")
        self._consent_action = ctk.StringVar(value=self.config.memory_sensitive_policy)
        self._editing_id: str | None = None

        self._build_ui()
        self._refresh_memory_list()

    def _build_ui(self) -> None:
        container = ctk.CTkScrollableFrame(self, width=880, height=680)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            container, text="Mälu haldus", font=("Arial", 20, "bold")
        ).pack(anchor="w", pady=(0, 8))

        filters_frame = ctk.CTkFrame(container)
        filters_frame.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(filters_frame, text="Otsi:").grid(row=0, column=0, padx=4, pady=4, sticky="w")
        search_entry = ctk.CTkEntry(filters_frame, textvariable=self._search_var, width=200)
        search_entry.grid(row=0, column=1, padx=4, pady=4)
        search_entry.bind("<KeyRelease>", lambda _: self._refresh_memory_list())

        ctk.CTkLabel(filters_frame, text="Tüüp:").grid(row=0, column=2, padx=4, pady=4, sticky="w")
        type_menu = ctk.CTkOptionMenu(
            filters_frame, variable=self._filter_type, values=[""] + MEMORY_TYPES,
            command=lambda _: self._refresh_memory_list(),
        )
        type_menu.grid(row=0, column=3, padx=4, pady=4)

        ctk.CTkLabel(filters_frame, text="Ulatus:").grid(row=0, column=4, padx=4, pady=4, sticky="w")
        scope_menu = ctk.CTkOptionMenu(
            filters_frame, variable=self._filter_scope, values=[""] + SCOPES,
            command=lambda _: self._refresh_memory_list(),
        )
        scope_menu.grid(row=0, column=5, padx=4, pady=4)

        ctk.CTkLabel(filters_frame, text="Allikas:").grid(row=1, column=0, padx=4, pady=4, sticky="w")
        source_menu = ctk.CTkOptionMenu(
            filters_frame, variable=self._filter_source, values=[""] + SOURCES,
            command=lambda _: self._refresh_memory_list(),
        )
        source_menu.grid(row=1, column=1, padx=4, pady=4)

        ctk.CTkLabel(filters_frame, text="Tundlikkus:").grid(row=1, column=2, padx=4, pady=4, sticky="w")
        sens_menu = ctk.CTkOptionMenu(
            filters_frame, variable=self._filter_sensitivity, values=[""] + SENSITIVITIES,
            command=lambda _: self._refresh_memory_list(),
        )
        sens_menu.grid(row=1, column=3, padx=4, pady=4)

        self._memory_listbox = ctk.CTkTextbox(container, height=250)
        self._memory_listbox.pack(fill="both", expand=True, pady=(0, 8))

        btn_frame = ctk.CTkFrame(container)
        btn_frame.pack(fill="x", pady=(0, 8))

        ctk.CTkButton(btn_frame, text="Kustuta", command=self._delete_selected).pack(
            side="left", padx=4
        )
        ctk.CTkButton(btn_frame, text="Muuda", command=self._edit_selected).pack(
            side="left", padx=4
        )
        ctk.CTkButton(btn_frame, text="Salvesta muudatus", command=self._save_edit).pack(
            side="left", padx=4
        )
        ctk.CTkButton(btn_frame, text="Kirjuta üles / tühista", command=self._toggle_pin).pack(
            side="left", padx=4
        )
        ctk.CTkButton(btn_frame, text="Mälu suurus", command=self._show_summary).pack(
            side="left", padx=4
        )

        export_frame = ctk.CTkFrame(container)
        export_frame.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(export_frame, text="Ekspordi:").pack(side="left", padx=4)
        self._export_type = ctk.StringVar(value=MEMORY_TYPES[0])
        ctk.CTkOptionMenu(export_frame, variable=self._export_type, values=MEMORY_TYPES).pack(
            side="left", padx=4
        )
        ctk.CTkButton(export_frame, text="Ekspordi tüübi järgi", command=self._export_type).pack(
            side="left", padx=4
        )

        ctk.CTkLabel(export_frame, text="Kustuta:").pack(side="left", padx=4)
        self._clear_type = ctk.StringVar(value=MEMORY_TYPES[0])
        ctk.CTkOptionMenu(export_frame, variable=self._clear_type, values=MEMORY_TYPES).pack(
            side="left", padx=4
        )
        ctk.CTkButton(export_frame, text="Kustuta tüübi järgi", command=self._clear_type).pack(
            side="left", padx=4
        )

        consent_frame = ctk.CTkFrame(container)
        consent_frame.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(consent_frame, text="Tundliku info poliitika:").pack(side="left", padx=4)
        ctk.CTkOptionMenu(
            consent_frame, variable=self._consent_action, values=CONSENT_ACTIONS,
            command=self._on_consent_change,
        ).pack(side="left", padx=4)

        ctk.CTkButton(container, text="Sulge", command=self.destroy).pack(
            fill="x", pady=(8, 0)
        )

    def _refresh_memory_list(self) -> None:
        query = self._search_var.get().strip()
        type_val = self._filter_type.get() or None
        scope_val = self._filter_scope.get() or None
        source_val = self._filter_source.get() or None
        sens_val = self._filter_sensitivity.get() or None

        types = (MemoryType(type_val),) if type_val else None
        scope_filter = (scope_val,) if scope_val else None
        source_filter = (source_val,) if source_val else None
        sens_filter = (sens_val,) if sens_val else None

        entries = self.manager.search(
            query_text=query,
            types=types,
            scope_filter=scope_filter,
            source_filter=source_filter,
            sensitivity_filter=sens_filter,
            limit=50,
        )

        self._memory_listbox.delete("1.0", "end")
        for entry in entries:
            pin_marker = "[PINNED] " if entry.pinned else ""
            line = (
                f"{pin_marker}[{entry.memory_type.value}] "
                f"[{entry.scope.value}] [{entry.source.value}] "
                f"[{entry.sensitivity.value}] {entry.text[:120]}\n"
            )
            self._memory_listbox.insert("end", line)
        self._memory_listbox.insert("end", f"\nKokku: {len(entries)} mälukirjet\n")

    def _delete_selected(self) -> None:
        selection = self._memory_listbox.get("insert linestart", "insert lineend")
        for entry in self.manager.store.entries:
            if entry.text[:50] in selection:
                self.manager.delete_memory(entry.id)
                self._refresh_memory_list()
                return

    def _edit_selected(self) -> None:
        selection = self._memory_listbox.get("insert linestart", "insert lineend")
        for entry in self.manager.store.entries:
            if entry.text[:50] in selection:
                self._editing_id = entry.id
                self._memory_listbox.delete("1.0", "end")
                self._memory_listbox.insert("end", f"Muuda kirjet {entry.id}:\n")
                self._memory_listbox.insert("end", entry.text)
                return

    def _save_edit(self) -> None:
        if self._editing_id is None:
            return
        content = self._memory_listbox.get("3.0", "end").strip()
        if content:
            self.manager.update_memory(self._editing_id, content)
            self._editing_id = None
            self._refresh_memory_list()

    def _toggle_pin(self) -> None:
        selection = self._memory_listbox.get("insert linestart", "insert lineend")
        for entry in self.manager.store.entries:
            if entry.text[:50] in selection:
                self.manager.toggle_pin(entry.id)
                self._refresh_memory_list()
                return

    def _export_type(self) -> None:
        memory_type = MemoryType(self._export_type.get())
        data = self.manager.export_by_type(memory_type)
        path = Path(f"~/.nexus/export_{memory_type.value}_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.json").expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding="utf-8")
        logger.info("Exported %s memories to %s", memory_type.value, path)

    def _clear_type(self) -> None:
        memory_type = MemoryType(self._clear_type.get())
        count = self.manager.clear_by_type(memory_type)
        logger.info("Cleared %d memories of type %s", count, memory_type.value)
        self._refresh_memory_list()

    def _show_summary(self) -> None:
        summary = self.manager.generate_self_summary()
        self._memory_listbox.delete("1.0", "end")
        self._memory_listbox.insert("end", summary)

    def _on_consent_change(self, value: str) -> None:
        self.config.memory_sensitive_policy = value
        self.config.save()
        action = ConsentAction(value)
        self.manager.consent_policy = ConsentPolicy(action=action)
        if self._on_policy_change:
            self._on_policy_change(self.manager.consent_policy)


def open_memory_consent(
    manager: MemoryManager,
    config: NexusConfig | None = None,
    on_policy_change: Callable[[ConsentPolicy], None] | None = None,
) -> MemoryConsentWindow:
    """Open the memory consent and management window."""
    window = MemoryConsentWindow(manager, config=config, on_policy_change=on_policy_change)
    window.mainloop()
    return window
