"""Event-driven orchestration for the Nexus assistant."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass

import numpy as np

from .contracts import (
    CaptureService,
    LLMService,
    MemoryService,
    PlaybackService,
    STTService,
    TTSService,
)
from .events import RuntimeEvent, RuntimeState
from .lifecycle import start_optional, stop_optional
from .state_machine import RuntimeStateMachine
from src.persona import PersonaManager, PersonaResponseMetadata

logger = logging.getLogger(__name__)

@dataclass(slots=True)
class RuntimeServices:
    """Services wired into one Nexus runtime."""

    llm: LLMService
    memory: MemoryService | None = None
    capture: CaptureService | None = None
    playback: PlaybackService | None = None
    stt: STTService | None = None
    tts: TTSService | None = None

class NexusRuntime:
    """Coordinate text, speech, memory, model, and playback services."""

    def __init__(
        self,
        services: RuntimeServices,
        *,
        system_prompt: str,
        persona: PersonaManager | None = None,
    ) -> None:
        self.services = services
        self.system_prompt = system_prompt
        self.persona = persona or PersonaManager()
        self.state_machine = RuntimeStateMachine()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._started = False
    def subscribe(self, callback: Callable[[RuntimeEvent], None]) -> None:
        """Subscribe to observable runtime events."""
        self.state_machine.subscribe(callback)
    @property
    def state(self) -> RuntimeState:
        return self.state_machine.state
    def interrupt(self, message: str = "Interrupted") -> RuntimeEvent:
        """Interrupt current work and return to idle."""
        return self.state_machine.interrupt(message)
    async def start(self) -> None:
        """Start configured services, degrading gracefully when optional ones fail."""
        if self._started:
            logger.debug("NexusRuntime already started")
            return
        self._loop = asyncio.get_running_loop()
        logger.info("NexusRuntime starting services...")
        await start_optional("playback", self.services.playback, "start")
        stt_ready = await start_optional("STT", self.services.stt, "load_model")
        tts_ready = await start_optional("TTS", self.services.tts, "load_model")
        if not stt_ready:
            logger.warning("STT service failed to start; disabling audio input")
            self.services.stt = None
        if not tts_ready:
            logger.warning("TTS service failed to start; disabling audio output")
            self.services.tts = None
        if self.services.capture and self.services.stt:
            self.services.capture.on_speech_start = self._on_speech_start
            self.services.capture.on_speech_end = self._on_speech_end
            await start_optional("audio capture", self.services.capture, "start")
        self._started = True
        logger.info("NexusRuntime started successfully")
        self._emit(RuntimeState.IDLE, "Nexus is ready")
    async def stop(self) -> None:
        """Stop services in reverse order and release local resources."""
        if not self._started:
            logger.debug("NexusRuntime.stop skipped; not started")
            return
        logger.info("NexusRuntime stopping...")
        await stop_optional("audio capture", self.services.capture, "stop")
        await stop_optional("TTS", self.services.tts, "unload_model")
        await stop_optional("STT", self.services.stt, "unload_model")
        await stop_optional("playback", self.services.playback, "stop")
        await stop_optional("LLM", self.services.llm, "close")
        self._started = False
        logger.info("NexusRuntime stopped")
        self._emit(RuntimeState.STOPPED, "Nexus stopped")
    async def handle_text(self, text: str) -> str:
        """Process one text request through memory, LLM, and optional speech output."""
        prompt = text.strip()
        if not prompt:
            raise ValueError("text must not be empty")
        logger.info("NexusRuntime.handle_text: prompt=%r", prompt[:200])
        self._emit(RuntimeState.PLANNING, "Generating response", {"input": prompt})
        try:
            context = self._memory_context(prompt)
            persona_prompt = self.persona.apply_persona(self.system_prompt + context)
            logger.debug("NexusRuntime LLM prompt length=%d", len(persona_prompt))
            response = await self.services.llm.generate(
                prompt, system_prompt=persona_prompt
            )
            answer = str(response.content).strip()
            if not answer:
                raise RuntimeError("LLM returned an empty response")
            logger.info("NexusRuntime LLM response length=%d: %r", len(answer), answer[:200])
            self._emit(RuntimeState.VERIFYING, "Response validated")
            self._remember(prompt, answer)
            await self._speak(answer)
            metadata = self.persona.response_metadata(confidence=0.9)
            self._emit(
                RuntimeState.IDLE,
                "Response complete",
                {
                    "response": answer,
                    "persona": asdict(metadata),
                    "transcript": [
                        {"role": "Kasutaja", "text": prompt},
                        {"role": "Nexus", "text": answer},
                    ],
                },
            )
            return answer
        except Exception as exc:
            logger.exception("NexusRuntime handle_text failed")
            self._emit(RuntimeState.ERROR, str(exc))
            raise
    async def handle_audio(self, audio: np.ndarray) -> str:
        """Transcribe captured audio and run the resulting text request."""
        if self.services.stt is None:
            raise RuntimeError("Speech-to-text is disabled")
        logger.info("NexusRuntime.handle_audio: samples=%d", len(audio))
        self._emit(RuntimeState.UNDERSTANDING, "Transcribing speech")
        result = await self.services.stt.transcribe(audio)
        text = str(result.text).strip()
        logger.info("NexusRuntime STT result: text=%r language=%s", text[:200], result.language)
        if not text:
            self._emit(RuntimeState.IDLE, "No speech detected")
            return ""
        self._emit(RuntimeState.UNDERSTANDING, "Speech recognized", {"transcript": [{"role": "Kasutaja", "text": text}]})
        return await self.handle_text(text)
    async def _speak(self, answer: str) -> None:
        if self.services.tts is None or self.services.playback is None:
            logger.debug("NexusRuntime._speak skipped; tts=%s playback=%s", self.services.tts is not None, self.services.playback is not None)
            return
        logger.debug("NexusRuntime._speak: text_length=%d", len(answer))
        self._emit(RuntimeState.SPEAKING, "Speaking response")
        await self.services.tts.speak(answer, self.services.playback)
        logger.debug("NexusRuntime._speak complete")
    def _memory_context(self, prompt: str) -> str:
        if self.services.memory is None:
            return ""
        hits = self.services.memory.search(prompt, limit=3)
        texts = [str(hit.entry.text) for hit in hits]
        return "" if not texts else "\nRelevant local memory:\n- " + "\n- ".join(texts)
    def _remember(self, prompt: str, answer: str) -> None:
        if self.services.memory is None:
            return
        self.services.memory.add(prompt, metadata={"role": "user"})
        self.services.memory.add(answer, metadata={"role": "assistant"})
    def _on_speech_start(self) -> None:
        def _emit() -> None:
            self._emit(RuntimeState.LISTENING, "Speech detected")

        if self._loop is None:
            _emit()
            return
        if self._loop.is_running():
            self._loop.call_soon_threadsafe(_emit)
        else:
            _emit()

    def _on_speech_end(self) -> None:
        if self._loop is None or self.services.capture is None:
            return

        def _process() -> None:
            audio = self.services.capture.get_speech_buffer()
            if audio is not None:
                asyncio.create_task(self._process_captured_audio(audio))

        if self._loop.is_running():
            self._loop.call_soon_threadsafe(_process)
        else:
            _process()
    async def _process_captured_audio(self, audio: np.ndarray) -> None:
        try:
            await self.handle_audio(audio)
        except Exception as exc:
            logger.exception("Captured speech processing failed")
            self._emit(RuntimeState.ERROR, str(exc))
    def get_persona_metadata(self, confidence: float = 0.8) -> PersonaResponseMetadata:
        return self.persona.response_metadata(confidence=confidence)

    def _emit(self, state: RuntimeState, message: str, data: dict[str, object] | None = None) -> None:
        self.state_machine.transition(state, message, data)
