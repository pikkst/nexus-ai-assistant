"""Configuration-driven construction of the Nexus runtime."""

from __future__ import annotations

from pathlib import Path

from src.audio import AudioCapture, AudioCaptureConfig, AudioPlayback, AudioPlaybackConfig
from src.config import NexusConfig
from src.llm import LLMClient, LLMConfig
from src.memory import MemoryStore
from src.stt import STTConfig, STTEngine
from src.tts import TTSConfig, TTSEngine

from .runtime import NexusRuntime, RuntimeServices


def create_runtime(config: NexusConfig | None = None) -> NexusRuntime:
    """Build a Nexus runtime from persisted application configuration."""
    settings = config or NexusConfig.load()
    llm = LLMClient(
        LLMConfig(
            base_url=settings.ollama_url,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            timeout=settings.llm_timeout,
            system_prompt=settings.llm_system_prompt,
        )
    )
    memory = None
    if settings.enable_memory:
        memory = MemoryStore(
            settings.memory_path,
            storage_format=settings.memory_storage_format,
            max_entries=settings.memory_max_entries,
            max_age_days=settings.memory_max_age_days,
        )
    capture = None
    stt = None
    if settings.enable_audio_input:
        capture = AudioCapture(
            AudioCaptureConfig(
                sample_rate=settings.sample_rate,
                device_index=settings.mic_device_index,
            )
        )
        stt = STTEngine(
            STTConfig(model_size=settings.stt_model_size, language=settings.stt_language)
        )
    playback = None
    tts = None
    if settings.enable_audio_output:
        playback = AudioPlayback(
            AudioPlaybackConfig(device_index=settings.speaker_device_index)
        )
        tts = TTSEngine(
            TTSConfig(
                voice=settings.tts_voice,
                speed=settings.tts_speed,
                language=settings.language,
                model_dir=Path("~/.nexus/voices"),
            )
        )
    return NexusRuntime(
        RuntimeServices(
            llm=llm,
            memory=memory,
            capture=capture,
            playback=playback,
            stt=stt,
            tts=tts,
        ),
        system_prompt=settings.llm_system_prompt,
    )
