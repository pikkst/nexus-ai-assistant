"""Tests for selectable Nexus face themes."""

from __future__ import annotations

import pytest

from src.ui.face import Emotion, NexusFace
from src.ui.face_themes import FaceTheme


@pytest.mark.parametrize("theme", list(FaceTheme))
def test_every_theme_renders_every_emotion(theme: FaceTheme) -> None:
    face = NexusFace(theme=theme)

    for emotion in Emotion:
        svg = face.render(emotion)
        assert svg.startswith("<svg")
        assert f'data-theme="{theme.value}"' in svg


def test_neon_blue_is_minimal_and_glowing() -> None:
    face = NexusFace(theme="neon_blue")
    svg = face.render("idle")

    assert face.config.eye_border == "#00aaff"
    assert face.config.mouth_color == "#00aaff"
    assert face.config.bg_color == face.config.head_color
    assert 'flood-color="#00aaff"' in svg


def test_red_alert_uses_red_eyes_and_mouth() -> None:
    face = NexusFace(theme="red_alert")

    assert face.config.iris_color == "#ff2020"
    assert face.config.mouth_color == "#ff2020"


def test_pixel_theme_uses_crisp_rectangular_features() -> None:
    svg = NexusFace(theme="pixel").render("speaking")

    assert 'shape-rendering="crispEdges"' in svg
    assert "<!-- Left eye -->" not in svg
    assert svg.count("<rect") >= 8


def test_cosmic_theme_combines_cyan_purple_and_pink() -> None:
    face = NexusFace(theme="cosmic")
    svg = face.render("surprised")

    assert "#64f5ff" in svg
    assert "#9b5cff" in svg
    assert "#ff77e9" in svg


def test_theme_can_change_at_runtime_and_return_to_classic() -> None:
    face = NexusFace(theme="neon_blue")
    face.set_theme("red_alert")
    assert face.config.theme == "red_alert"
    assert face.config.mouth_color == "#ff2020"

    face.set_theme("classic")
    assert face.config.theme == "classic"
    assert face.config.mouth_color == "#4a4a62"


def test_unknown_theme_is_rejected() -> None:
    with pytest.raises(ValueError):
        NexusFace(theme="unknown")
