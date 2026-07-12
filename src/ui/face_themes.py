"""Built-in visual themes for the animated Nexus face."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FaceTheme(Enum):
    """Selectable face appearances."""

    CLASSIC = "classic"
    NEON_BLUE = "neon_blue"
    PIXEL = "pixel"
    RED_ALERT = "red_alert"
    COSMIC = "cosmic"


@dataclass(frozen=True, slots=True)
class ThemeSpec:
    """Colors and rendering behavior applied to ``FaceConfig``."""

    colors: dict[str, str]
    render_style: str = "smooth"
    glow_color: str = "transparent"


_THEMES: dict[FaceTheme, ThemeSpec] = {
    FaceTheme.CLASSIC: ThemeSpec(colors={}),
    FaceTheme.NEON_BLUE: ThemeSpec(
        colors={
            "bg_color": "#02050c",
            "head_color": "#02050c",
            "head_border": "#02050c",
            "eye_white": "#02050c",
            "eye_border": "#00aaff",
            "iris_color": "#00aaff",
            "iris_light": "#8be9ff",
            "iris_dark": "#0066ff",
            "pupil_color": "#00d9ff",
            "pupil_light": "#b8f7ff",
            "highlight_color": "#ffffff",
            "brow_color": "#02050c",
            "mouth_color": "#00aaff",
            "blush_color": "#02050c",
            "label_color": "#02050c",
            "label_sub_color": "#02050c",
        },
        glow_color="#00aaff",
    ),
    FaceTheme.PIXEL: ThemeSpec(
        colors={
            "bg_color": "#0b1020",
            "head_color": "#121a2e",
            "head_border": "#243354",
            "eye_white": "#73ffcc",
            "eye_border": "#73ffcc",
            "iris_color": "#0b1020",
            "iris_light": "#ffffff",
            "iris_dark": "#0b1020",
            "pupil_color": "#0b1020",
            "pupil_light": "#0b1020",
            "highlight_color": "#ffffff",
            "brow_color": "#73ffcc",
            "mouth_color": "#73ffcc",
            "blush_color": "#ff77aa",
            "label_color": "#73ffcc",
            "label_sub_color": "#526b7a",
        },
        render_style="pixel",
    ),
    FaceTheme.RED_ALERT: ThemeSpec(
        colors={
            "bg_color": "#080000",
            "head_color": "#080000",
            "head_border": "#210000",
            "eye_white": "#080000",
            "eye_border": "#ff2020",
            "iris_color": "#ff2020",
            "iris_light": "#ff8a70",
            "iris_dark": "#8f0000",
            "pupil_color": "#ff0000",
            "pupil_light": "#ffd0c8",
            "highlight_color": "#ffffff",
            "brow_color": "#080000",
            "mouth_color": "#ff2020",
            "blush_color": "#080000",
            "label_color": "#3a0000",
            "label_sub_color": "#3a0000",
        },
        glow_color="#ff2020",
    ),
    FaceTheme.COSMIC: ThemeSpec(
        colors={
            "bg_color": "#09031c",
            "head_color": "#21104a",
            "head_border": "#7038d0",
            "eye_white": "#eafcff",
            "eye_border": "#64f5ff",
            "iris_color": "#9b5cff",
            "iris_light": "#64f5ff",
            "iris_dark": "#ff4fd8",
            "pupil_color": "#14052f",
            "pupil_light": "#6630a8",
            "highlight_color": "#ffffff",
            "brow_color": "#64f5ff",
            "mouth_color": "#ff77e9",
            "blush_color": "#a95cff",
            "label_color": "#64f5ff",
            "label_sub_color": "#b38cff",
        },
        glow_color="#a95cff",
    ),
}


def theme_spec(theme: FaceTheme | str) -> ThemeSpec:
    """Return a validated immutable theme specification."""
    selected = FaceTheme(theme) if isinstance(theme, str) else theme
    return _THEMES[selected]
