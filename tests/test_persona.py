"""Tests for Nexus persona and interaction modes."""

from __future__ import annotations

from datetime import datetime, time
from pathlib import Path

import pytest

from src.persona import PersonaManager, PersonaMode, PersonaResponseMetadata, PersonaSettings
from src.config.settings import NexusConfig
from src.llm.prompts import apply_persona


class TestPersonaSettings:
    def test_defaults(self) -> None:
        settings = PersonaSettings()
        assert settings.mode == PersonaMode.BALANCED
        assert settings.playfulness == 0.5
        assert settings.proactivity == 0.5
        assert settings.response_detail == 0.5
        assert settings.unsolicited_suggestions is True
        assert settings.quiet_hours_start is None
        assert settings.quiet_hours_end is None

    def test_invalid_playfulness_raises(self) -> None:
        with pytest.raises(ValueError):
            PersonaSettings(playfulness=1.5)
        with pytest.raises(ValueError):
            PersonaSettings(playfulness=-0.1)

    def test_invalid_proactivity_raises(self) -> None:
        with pytest.raises(ValueError):
            PersonaSettings(proactivity=2.0)

    def test_invalid_response_detail_raises(self) -> None:
        with pytest.raises(ValueError):
            PersonaSettings(response_detail=-1.0)


class TestPersonaModes:
    def test_companion_mode(self) -> None:
        manager = PersonaManager(PersonaSettings(mode=PersonaMode.COMPANION, playfulness=0.9))
        metadata = manager.response_metadata(confidence=0.95)
        assert metadata.emotion == "happy"
        assert metadata.voice_energy > 0.7

    def test_focused_mode(self) -> None:
        manager = PersonaManager(
            PersonaSettings(mode=PersonaMode.FOCUSED, response_detail=0.2)
        )
        metadata = manager.response_metadata()
        assert metadata.voice_energy < 0.5

    def test_balanced_mode(self) -> None:
        manager = PersonaManager(PersonaSettings(mode=PersonaMode.BALANCED))
        metadata = manager.response_metadata()
        assert metadata.detail_level in {"concise", "normal", "detailed"}


class TestPersonaResponseMetadata:
    def test_metadata_bounds(self) -> None:
        manager = PersonaManager(PersonaSettings(playfulness=1.0, response_detail=1.0))
        metadata = manager.response_metadata(confidence=1.0)
        assert 0.0 <= metadata.voice_energy <= 1.0
        assert 0.0 <= metadata.confidence <= 1.0
        assert metadata.detail_level == "detailed"

    def test_invalid_metadata_raises(self) -> None:
        with pytest.raises(ValueError):
            PersonaResponseMetadata(voice_energy=2.0)
        with pytest.raises(ValueError):
            PersonaResponseMetadata(confidence=-0.5)


class TestPersonaManager:
    def test_update_settings(self) -> None:
        manager = PersonaManager()
        updated = manager.update(playfulness=0.8, mode=PersonaMode.COMPANION)
        assert updated.playfulness == 0.8
        assert updated.mode == PersonaMode.COMPANION

    def test_set_mode_by_string(self) -> None:
        manager = PersonaManager()
        updated = manager.set_mode("focused")
        assert updated.mode == PersonaMode.FOCUSED

    def test_quiet_hours_disabled_by_default(self) -> None:
        manager = PersonaManager()
        assert manager.is_quiet_hours() is False

    def test_quiet_hours_active(self) -> None:
        now = datetime(2024, 1, 1, 14, 0)
        manager = PersonaManager(
            PersonaSettings(
                quiet_hours_start=time(13, 0),
                quiet_hours_end=time(15, 0),
            )
        )
        assert manager.is_quiet_hours(now=now) is True

    def test_quiet_hours_overnight(self) -> None:
        manager = PersonaManager(
            PersonaSettings(
                quiet_hours_start=time(22, 0),
                quiet_hours_end=time(6, 0),
            )
        )
        assert manager.is_quiet_hours(now=datetime(2024, 1, 1, 23, 0)) is True

    def test_proactive_rate_limited(self) -> None:
        manager = PersonaManager(
            PersonaSettings(proactivity=0.5, unsolicited_suggestions=True)
        )
        manager.mark_proactive_sent(now=datetime(2024, 1, 1, 12, 0, 0))
        assert manager.can_send_proactive(now=datetime(2024, 1, 1, 12, 0, 30)) is False

    def test_proactive_disabled_by_setting(self) -> None:
        manager = PersonaManager(PersonaSettings(unsolicited_suggestions=False))
        assert manager.can_send_proactive() is False

    def test_proactive_disabled_in_quiet_hours(self) -> None:
        manager = PersonaManager(
            PersonaSettings(
                unsolicited_suggestions=True,
                quiet_hours_start=time(0, 0),
                quiet_hours_end=time(23, 59),
            )
        )
        assert manager.can_send_proactive(now=datetime(2024, 1, 1, 12, 0)) is False

    def test_apply_persona_includes_mode_and_guidance(self) -> None:
        manager = PersonaManager(
            PersonaSettings(mode=PersonaMode.COMPANION, playfulness=0.8, response_detail=0.6)
        )
        result = manager.apply_persona("You are Nexus.")
        assert "companion" in result.lower()
        assert "factual accuracy" in result.lower()


class TestPersonaPersistence:
    def test_save_and_load(self, tmp_path: Path) -> None:
        manager = PersonaManager(
            PersonaSettings(
                mode=PersonaMode.FOCUSED,
                playfulness=0.2,
                proactivity=0.1,
                response_detail=0.3,
                unsolicited_suggestions=False,
                quiet_hours_start=time(22, 0),
                quiet_hours_end=time(6, 0),
            ),
            path=tmp_path / "persona.json",
        )
        manager.save()
        loaded = PersonaManager.load(tmp_path / "persona.json")
        assert loaded.settings.mode == PersonaMode.FOCUSED
        assert loaded.settings.playfulness == 0.2
        assert loaded.settings.proactivity == 0.1
        assert loaded.settings.response_detail == 0.3
        assert loaded.settings.unsolicited_suggestions is False
        assert loaded.settings.quiet_hours_start == time(22, 0)
        assert loaded.settings.quiet_hours_end == time(6, 0)
        assert loaded.is_quiet_hours(now=datetime(2024, 1, 1, 23, 0)) is True

    def test_load_missing_returns_defaults(self, tmp_path: Path) -> None:
        manager = PersonaManager.load(tmp_path / "missing.json")
        assert manager.settings.mode == PersonaMode.BALANCED

    def test_load_corrupt_returns_defaults(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{invalid", encoding="utf-8")
        manager = PersonaManager.load(bad)
        assert manager.settings.playfulness == 0.5


class TestPersonaConfigIntegration:
    def test_default_config_has_persona_fields(self) -> None:
        config = NexusConfig()
        assert config.persona_mode == "balanced"
        assert config.persona_playfulness == 0.5
        assert config.persona_proactivity == 0.5
        assert config.persona_response_detail == 0.5
        assert config.persona_unsolicited_suggestions is True
        assert config.persona_quiet_hours_start is None
        assert config.persona_quiet_hours_end is None

    def test_config_persona_roundtrip(self, tmp_path: Path) -> None:
        config = NexusConfig(
            persona_mode="companion",
            persona_playfulness=0.9,
            persona_proactivity=0.8,
            persona_response_detail=0.7,
            persona_unsolicited_suggestions=False,
            persona_quiet_hours_start="22:00:00",
            persona_quiet_hours_end="06:00:00",
        )
        out = tmp_path / "config.json"
        config.save(out)
        loaded = NexusConfig.load(out)
        assert loaded.persona_mode == "companion"
        assert loaded.persona_playfulness == 0.9
        assert loaded.persona_proactivity == 0.8
        assert loaded.persona_response_detail == 0.7
        assert loaded.persona_unsolicited_suggestions is False
        assert loaded.persona_quiet_hours_start == "22:00:00"
        assert loaded.persona_quiet_hours_end == "06:00:00"


class TestPersonaPromptIntegration:
    def test_apply_persona_high_playfulness(self) -> None:
        result = apply_persona("You are Nexus.", playfulness=0.9, mode="companion")
        assert "companion" in result.lower()
        assert "warm" in result.lower()

    def test_apply_persona_low_playfulness(self) -> None:
        result = apply_persona("You are Nexus.", playfulness=0.1, mode="focused")
        assert "focused" in result.lower()
        assert "factual" in result.lower()

    def test_apply_persona_high_detail(self) -> None:
        result = apply_persona("You are Nexus.", response_detail=0.9)
        assert "thorough" in result.lower()

    def test_apply_persona_low_detail(self) -> None:
        result = apply_persona("You are Nexus.", response_detail=0.1)
        assert "short" in result.lower() or "focused" in result.lower()
