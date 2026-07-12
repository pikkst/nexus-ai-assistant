"""
Nexus Settings Panel.

CustomTkinter-based settings window for audio, TTS, language, and more.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from typing import Callable

import customtkinter as ctk

from src.config.settings import NexusConfig


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


AVAILABLE_VOICES = [
    "en_US-lessac-medium",
    "en_US-ryan-medium",
    "en_GB-southern_english_female-medium",
    "et_EE-harri-medium",
]

LANGUAGES = [
    ("Eesti", "et"),
    ("English", "en"),
]


class SettingsWindow(ctk.CTk):
    """Settings panel window."""

    def __init__(
        self,
        config: NexusConfig | None = None,
        on_save: Callable[[NexusConfig], None] | None = None,
    ) -> None:
        super().__init__()
        self.config = config or NexusConfig.load()
        self._on_save = on_save
        self.title("Nexus — Seaded")
        self.geometry("520x620")
        self.resizable(False, False)

        self._build_ui()

    def _build_ui(self) -> None:
        container = ctk.CTkScrollableFrame(self, width=500, height=600)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(container, text="Heli seaded", font=("Arial", 18, "bold")).pack(
            anchor="w", pady=(0, 8)
        )

        # Volume
        self._volume_label = ctk.CTkLabel(container, text=f"Heli tugevus: {int(self.config.playback_volume * 100)}%")
        self._volume_label.pack(anchor="w")
        self._volume_slider = ctk.CTkSlider(
            container, from_=0.0, to=1.0, number_of_steps=100,
            command=self._on_volume_change,
        )
        self._volume_slider.set(self.config.playback_volume)
        self._volume_slider.pack(fill="x", pady=(0, 12))

        # Sample rate
        ctk.CTkLabel(container, text="Sample rate:").pack(anchor="w")
        self._sample_rate_menu = ctk.CTkOptionMenu(
            container, values=["16000", "24000", "44100", "48000"],
            command=lambda v: setattr(self.config, "sample_rate", int(v)),
        )
        self._sample_rate_menu.set(str(self.config.sample_rate))
        self._sample_rate_menu.pack(fill="x", pady=(0, 12))

        # TTS voice
        ctk.CTkLabel(container, text="TTS hääl (toon):").pack(anchor="w")
        self._voice_menu = ctk.CTkOptionMenu(
            container, values=AVAILABLE_VOICES,
            command=lambda v: setattr(self.config, "tts_voice", v),
        )
        self._voice_menu.set(self.config.tts_voice)
        self._voice_menu.pack(fill="x", pady=(0, 12))

        # TTS speed
        ctk.CTkLabel(container, text=f"TTS kiirus: {self.config.tts_speed}x").pack(anchor="w")
        self._speed_slider = ctk.CTkSlider(
            container, from_=0.5, to=2.0, number_of_steps=15,
            command=lambda v: self._speed_label.configure(text=f"TTS kiirus: {float(v):.1f}x") or setattr(self.config, "tts_speed", float(v)),
        )
        self._speed_slider.set(self.config.tts_speed)
        self._speed_slider.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(container, text="Keel", font=("Arial", 18, "bold")).pack(
            anchor="w", pady=(12, 8)
        )

        # Language
        self._lang_menu = ctk.CTkOptionMenu(
            container, values=[label for label, _ in LANGUAGES],
            command=self._on_language_change,
        )
        self._lang_menu.set(next(label for label, code in LANGUAGES if code == self.config.language))
        self._lang_menu.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(container, text="Muud", font=("Arial", 18, "bold")).pack(
            anchor="w", pady=(12, 8)
        )

        # Theme
        ctk.CTkLabel(container, text="Teema:").pack(anchor="w")
        self._theme_menu = ctk.CTkOptionMenu(
            container, values=["dark", "light", "system"],
            command=lambda v: setattr(self.config, "theme", v),
        )
        self._theme_menu.set(self.config.theme)
        self._theme_menu.pack(fill="x", pady=(0, 12))

        # Save button
        ctk.CTkButton(container, text="Salvesta seaded", command=self._save).pack(
            fill="x", pady=(16, 0)
        )

    def _on_volume_change(self, value: float) -> None:
        self.config.playback_volume = float(value)
        self._volume_label.configure(text=f"Heli tugevus: {int(value * 100)}%")

    def _on_language_change(self, label: str) -> None:
        code = next(code for lbl, code in LANGUAGES if lbl == label)
        self.config.language = code

    def _save(self) -> None:
        self.config.save()
        if self._on_save:
            self._on_save(self.config)
        self.destroy()


def open_settings(on_save: Callable[[NexusConfig], None] | None = None) -> SettingsWindow:
    """Open the settings window."""
    window = SettingsWindow(on_save=on_save)
    window.mainloop()
    return window
