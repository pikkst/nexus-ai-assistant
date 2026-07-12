"""Integration smoke tests for the central Nexus runtime."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from src.app import NexusRuntime, RuntimeServices, RuntimeState


class FakeLLM:
    def __init__(self) -> None:
        self.requests: list[tuple[str, dict[str, Any]]] = []
        self.closed = False
    async def generate(self, prompt: str, **kwargs: Any) -> SimpleNamespace:
        self.requests.append((prompt, kwargs))
        return SimpleNamespace(content="Tere! Olen valmis aitama.")

    async def close(self) -> None:
        self.closed = True


class FakeMemory:
    def __init__(self) -> None:
        self.items: list[tuple[str, dict[str, Any]]] = []
    def add(self, text: str, **kwargs: Any) -> None:
        self.items.append((text, kwargs.get("metadata", {})))

    def search(self, query: str, *, limit: int = 5) -> list[Any]:
        entry = SimpleNamespace(text="Kasutaja eelistab eesti keelt.")
        return [SimpleNamespace(entry=entry)]


class FakeLifecycle:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False
    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True


@dataclass
class FakeTranscript:
    text: str


class FakeSTT:
    def __init__(self) -> None:
        self.loaded = False

    async def load_model(self) -> None:
        self.loaded = True

    async def unload_model(self) -> None:
        self.loaded = False

    async def transcribe(self, audio: np.ndarray, **kwargs: Any) -> FakeTranscript:
        return FakeTranscript("Tere Nexus")


@pytest.mark.asyncio
async def test_text_request_runs_end_to_end() -> None:
    llm = FakeLLM()
    memory = FakeMemory()
    events = []
    runtime = NexusRuntime(RuntimeServices(llm=llm, memory=memory), system_prompt="Nexus")
    runtime.subscribe(events.append)

    await runtime.start()
    answer = await runtime.handle_text("  Tere  ")
    await runtime.stop()

    assert answer == "Tere! Olen valmis aitama."
    assert [item[0] for item in memory.items] == ["Tere", answer]
    assert "Relevant local memory" in llm.requests[0][1]["system_prompt"]
    assert [event.state for event in events] == [
        RuntimeState.IDLE,
        RuntimeState.PLANNING,
        RuntimeState.VERIFYING,
        RuntimeState.IDLE,
        RuntimeState.STOPPED,
    ]
    assert llm.closed


@pytest.mark.asyncio
async def test_audio_request_uses_stt_and_lifecycle() -> None:
    llm = FakeLLM()
    stt = FakeSTT()
    playback = FakeLifecycle()
    runtime = NexusRuntime(
        RuntimeServices(llm=llm, stt=stt, playback=playback), system_prompt="Nexus"
    )

    await runtime.start()
    answer = await runtime.handle_audio(np.zeros(160, dtype=np.float32))
    await runtime.stop()

    assert answer.startswith("Tere!")
    assert llm.requests[0][0] == "Tere Nexus"
    assert playback.started and playback.stopped
    assert not stt.loaded


@pytest.mark.asyncio
async def test_optional_service_start_failure_does_not_stop_runtime() -> None:
    class BrokenPlayback(FakeLifecycle):
        async def start(self) -> None:
            raise RuntimeError("no speakers")

    runtime = NexusRuntime(
        RuntimeServices(llm=FakeLLM(), playback=BrokenPlayback()), system_prompt="Nexus"
    )

    await runtime.start()

    assert runtime.state is RuntimeState.IDLE
    await runtime.stop()


@pytest.mark.asyncio
async def test_failed_tts_is_disabled_and_text_still_works() -> None:
    class BrokenTTS:
        async def load_model(self) -> None:
            raise RuntimeError("voice missing")

        async def unload_model(self) -> None:
            return None

        async def speak(self, text: str, playback: Any) -> None:
            raise AssertionError("disabled TTS must not be called")

    runtime = NexusRuntime(
        RuntimeServices(llm=FakeLLM(), playback=FakeLifecycle(), tts=BrokenTTS()),
        system_prompt="Nexus",
    )

    await runtime.start()
    answer = await runtime.handle_text("Tere")

    assert answer.startswith("Tere!")
    assert runtime.services.tts is None
    await runtime.stop()
