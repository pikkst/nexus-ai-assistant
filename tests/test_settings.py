"""Tests for Nexus configuration management."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.config.settings import NexusConfig


class TestNexusConfigDefaults:
    def test_default_values(self) -> None:
        config = NexusConfig()
        assert config.sample_rate == 16000
        assert config.playback_volume == 0.8
        assert config.tts_voice == "en_US-lessac-medium"
        assert config.tts_speed == 1.0
        assert config.stt_language == "et"
        assert config.language == "et"
        assert config.theme == "dark"
        assert config.camera_index == 0
        assert config.ollama_url == "http://localhost:11434"
        assert config.llm_model == "llama3.1"
        assert config.llm_timeout == 60.0
        assert config.memory_storage_format == "json"
        assert config.memory_max_entries == 1000
        assert config.memory_max_age_days == 90


class TestNexusConfigPersistence:
    def test_save_creates_file(self, tmp_path: Path) -> None:
        config = NexusConfig()
        out = tmp_path / "config.json"
        config.save(out)
        assert out.exists()

    def test_roundtrip(self, tmp_path: Path) -> None:
        config = NexusConfig(
            sample_rate=24000,
            playback_volume=0.5,
            tts_voice="et_EE-harri-medium",
            language="en",
            llm_model="mistral",
            ollama_url="http://127.0.0.1:11434",
            memory_path="data/memory.json",
            memory_max_entries=250,
            enable_audio_input=False,
            enable_audio_output=False,
            enable_memory=False,
        )
        out = tmp_path / "config.json"
        config.save(out)
        loaded = NexusConfig.load(out)
        assert loaded.sample_rate == 24000
        assert loaded.playback_volume == 0.5
        assert loaded.tts_voice == "et_EE-harri-medium"
        assert loaded.language == "en"
        assert loaded.llm_model == "mistral"
        assert loaded.ollama_url == "http://127.0.0.1:11434"
        assert loaded.memory_path == "data/memory.json"
        assert loaded.memory_max_entries == 250
        assert not loaded.enable_audio_input
        assert not loaded.enable_audio_output
        assert not loaded.enable_memory
        assert loaded.camera_resolution == (640, 480)

    def test_load_missing_returns_defaults(self, tmp_path: Path) -> None:
        loaded = NexusConfig.load(tmp_path / "missing.json")
        assert loaded.sample_rate == 16000
        assert loaded.playback_volume == 0.8

    def test_load_corrupt_returns_defaults(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{invalid json", encoding="utf-8")
        loaded = NexusConfig.load(bad)
        assert loaded.language == "et"


class TestNexusConfigAudioFields:
    def test_audio_device_fields(self) -> None:
        config = NexusConfig(mic_device_index=1, speaker_device_index=2)
        assert config.mic_device_index == 1
        assert config.speaker_device_index == 2

    def test_volume_bounds(self) -> None:
        config = NexusConfig(playback_volume=0.0)
        assert config.playback_volume == 0.0
        config = NexusConfig(playback_volume=1.0)
        assert config.playback_volume == 1.0
