"""
Nexus Settings Panel.

CustomTkinter-based settings window for audio, TTS, language, and more.
"""

from __future__ import annotations

from datetime import datetime, time
from typing import Callable

import customtkinter as ctk

from src.config.settings import NexusConfig
from src.persona import PersonaMode, PersonaSettings


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


def _list_pyaudio_devices() -> tuple[list[str], list[str]]:
    """Return (input_devices, output_devices) name lists from PyAudio."""
    input_devices: list[str] = ["Default"]
    output_devices: list[str] = ["Default"]
    try:
        import pyaudio

        pa = pyaudio.PyAudio()
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            name = info.get("name", f"Device {i}")
            if info.get("max_input_channels", 0) > 0:
                input_devices.append(name)
            if info.get("max_output_channels", 0) > 0:
                output_devices.append(name)
        pa.terminate()
    except Exception:
        pass
    return input_devices, output_devices


PERSONA_MODES = [
    ("Kaaslane", PersonaMode.COMPANION.value),
    ("Tasakaalus", PersonaMode.BALANCED.value),
    ("Fookuses", PersonaMode.FOCUSED.value),
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
        self._persona = PersonaSettings(
            mode=PersonaMode(self.config.persona_mode),
            playfulness=self.config.persona_playfulness,
            proactivity=self.config.persona_proactivity,
            response_detail=self.config.persona_response_detail,
            unsolicited_suggestions=self.config.persona_unsolicited_suggestions,
            quiet_hours_start=(
                datetime.fromisoformat(self.config.persona_quiet_hours_start).time()
                if self.config.persona_quiet_hours_start
                else None
            ),
            quiet_hours_end=(
                datetime.fromisoformat(self.config.persona_quiet_hours_end).time()
                if self.config.persona_quiet_hours_end
                else None
            ),
        )
        self._on_save = on_save
        self.title("Nexus — Seaded")
        self.geometry("560x720")
        self.resizable(False, False)

        self._input_devices, self._output_devices = _list_pyaudio_devices()
        self._build_ui()

    def _build_ui(self) -> None:
        container = ctk.CTkScrollableFrame(self, width=540, height=700)
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

        # Input device
        ctk.CTkLabel(container, text="Mikrofon:").pack(anchor="w")
        self._input_menu = ctk.CTkOptionMenu(
            container, values=self._input_devices,
            command=self._on_input_device_change,
        )
        current_input = "Default"
        if self.config.mic_device_index is not None:
            idx = self.config.mic_device_index + 1
            if 0 <= idx < len(self._input_devices):
                current_input = self._input_devices[idx]
        self._input_menu.set(current_input)
        self._input_menu.pack(fill="x", pady=(0, 12))

        # Output device
        ctk.CTkLabel(container, text="Kõlar:").pack(anchor="w")
        self._output_menu = ctk.CTkOptionMenu(
            container, values=self._output_devices,
            command=self._on_output_device_change,
        )
        current_output = "Default"
        if self.config.speaker_device_index is not None:
            idx = self.config.speaker_device_index + 1
            if 0 <= idx < len(self._output_devices):
                current_output = self._output_devices[idx]
        self._output_menu.set(current_output)
        self._output_menu.pack(fill="x", pady=(0, 12))

        # TTS voice
        ctk.CTkLabel(container, text="TTS hääl (toon):").pack(anchor="w")
        self._voice_menu = ctk.CTkOptionMenu(
            container, values=AVAILABLE_VOICES,
            command=lambda v: setattr(self.config, "tts_voice", v),
        )
        self._voice_menu.set(self.config.tts_voice)
        self._voice_menu.pack(fill="x", pady=(0, 12))

        # TTS speed
        self._speed_label = ctk.CTkLabel(container, text=f"TTS kiirus: {self.config.tts_speed}x")
        self._speed_label.pack(anchor="w")
        self._speed_slider = ctk.CTkSlider(
            container, from_=0.5, to=2.0, number_of_steps=15,
            command=lambda v: self._on_speed_change(float(v)),
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

        ctk.CTkLabel(container, text="Näo teema:").pack(anchor="w")
        self._face_theme_menu = ctk.CTkOptionMenu(
            container,
            values=["classic", "neon_blue", "pixel", "red_alert", "cosmic"],
            command=lambda value: setattr(self.config, "face_theme", value),
        )
        self._face_theme_menu.set(self.config.face_theme)
        self._face_theme_menu.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(container, text="Persona", font=("Arial", 18, "bold")).pack(
            anchor="w", pady=(12, 8)
        )

        ctk.CTkLabel(container, text="Suhtlusrežiim:").pack(anchor="w")
        self._persona_mode_menu = ctk.CTkOptionMenu(
            container,
            values=[label for label, _ in PERSONA_MODES],
            command=self._on_persona_mode_change,
        )
        current_mode = next(
            (label for label, code in PERSONA_MODES if code == self.config.persona_mode),
            PERSONA_MODES[1][0],
        )
        self._persona_mode_menu.set(current_mode)
        self._persona_mode_menu.pack(fill="x", pady=(0, 12))

        self._playfulness_label = ctk.CTkLabel(
            container, text=f"Mängulikkus: {int(self.config.persona_playfulness * 100)}%"
        )
        self._playfulness_label.pack(anchor="w")
        self._playfulness_slider = ctk.CTkSlider(
            container, from_=0.0, to=1.0, number_of_steps=100,
            command=lambda v: self._on_playfulness_change(float(v)),
        )
        self._playfulness_slider.set(self.config.persona_playfulness)
        self._playfulness_slider.pack(fill="x", pady=(0, 12))

        self._proactivity_label = ctk.CTkLabel(
            container, text=f"Proaktiivsus: {int(self.config.persona_proactivity * 100)}%"
        )
        self._proactivity_label.pack(anchor="w")
        self._proactivity_slider = ctk.CTkSlider(
            container, from_=0.0, to=1.0, number_of_steps=100,
            command=lambda v: self._on_proactivity_change(float(v)),
        )
        self._proactivity_slider.set(self.config.persona_proactivity)
        self._proactivity_slider.pack(fill="x", pady=(0, 12))

        self._detail_label = ctk.CTkLabel(
            container, text=f"Detailitus: {int(self.config.persona_response_detail * 100)}%"
        )
        self._detail_label.pack(anchor="w")
        self._detail_slider = ctk.CTkSlider(
            container, from_=0.0, to=1.0, number_of_steps=100,
            command=lambda v: self._on_detail_change(float(v)),
        )
        self._detail_slider.set(self.config.persona_response_detail)
        self._detail_slider.pack(fill="x", pady=(0, 12))

        self._suggestions_switch = ctk.CTkSwitch(
            container,
            text="Soovitused ilma küsimata",
            command=self._on_suggestions_toggle,
        )
        if self.config.persona_unsolicited_suggestions:
            self._suggestions_switch.select()
        self._suggestions_switch.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(container, text="Vaikeseadete aeg:").pack(anchor="w")
        quiet_frame = ctk.CTkFrame(container)
        quiet_frame.pack(fill="x", pady=(0, 12))
        self._quiet_start_entry = ctk.CTkEntry(quiet_frame, placeholder_text="Algus (HH:MM)")
        self._quiet_start_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self._quiet_end_entry = ctk.CTkEntry(quiet_frame, placeholder_text="Lõpp (HH:MM)")
        self._quiet_end_entry.pack(side="left", fill="x", expand=True, padx=(4, 0))
        if self._persona.quiet_hours_start:
            self._quiet_start_entry.insert(0, self._persona.quiet_hours_start.strftime("%H:%M"))
        if self._persona.quiet_hours_end:
            self._quiet_end_entry.insert(0, self._persona.quiet_hours_end.strftime("%H:%M"))

        # Save button
        ctk.CTkButton(container, text="Salvesta seaded", command=self._save).pack(
            fill="x", pady=(16, 0)
        )

    def _on_volume_change(self, value: float) -> None:
        self.config.playback_volume = float(value)
        self._volume_label.configure(text=f"Heli tugevus: {int(value * 100)}%")

    def _on_speed_change(self, value: float) -> None:
        self.config.tts_speed = value
        self._speed_label.configure(text=f"TTS kiirus: {value:.1f}x")

    def _on_language_change(self, label: str) -> None:
        code = next(code for lbl, code in LANGUAGES if lbl == label)
        self.config.language = code

    def _on_input_device_change(self, value: str) -> None:
        if value == "Default":
            self.config.mic_device_index = None
        else:
            self.config.mic_device_index = self._input_devices.index(value) - 1

    def _on_output_device_change(self, value: str) -> None:
        if value == "Default":
            self.config.speaker_device_index = None
        else:
            self.config.speaker_device_index = self._output_devices.index(value) - 1

    def _on_persona_mode_change(self, label: str) -> None:
        code = next(code for lbl, code in PERSONA_MODES if lbl == label)
        self.config.persona_mode = code

    def _on_playfulness_change(self, value: float) -> None:
        self.config.persona_playfulness = value
        self._playfulness_label.configure(text=f"Mängulikkus: {int(value * 100)}%")

    def _on_proactivity_change(self, value: float) -> None:
        self.config.persona_proactivity = value
        self._proactivity_label.configure(text=f"Proaktiivsus: {int(value * 100)}%")

    def _on_detail_change(self, value: float) -> None:
        self.config.persona_response_detail = value
        self._detail_label.configure(text=f"Detailitus: {int(value * 100)}%")

    def _on_suggestions_toggle(self) -> None:
        self.config.persona_unsolicited_suggestions = bool(self._suggestions_switch.get())

    def _save(self) -> None:
        self._apply_quiet_hours()
        self.config.save()
        if self._on_save:
            self._on_save(self.config)
        self.destroy()

    def _apply_quiet_hours(self) -> None:
        start_text = self._quiet_start_entry.get().strip()
        end_text = self._quiet_end_entry.get().strip()
        try:
            self.config.persona_quiet_hours_start = (
                time.fromisoformat(start_text).isoformat() if start_text else None
            )
        except ValueError:
            self.config.persona_quiet_hours_start = None
        try:
            self.config.persona_quiet_hours_end = (
                time.fromisoformat(end_text).isoformat() if end_text else None
            )
        except ValueError:
            self.config.persona_quiet_hours_end = None


def open_settings(on_save: Callable[[NexusConfig], None] | None = None) -> SettingsWindow:
    """Open the settings window."""
    window = SettingsWindow(on_save=on_save)
    window.mainloop()
    return window
