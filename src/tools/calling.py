"""Typed state exchanged by the bounded LLM tool-calling loop."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

from src.llm import LLMResponse, LLMToolCall

from .models import ToolRequest


class ToolRunStatus(Enum):
    COMPLETED = "completed"
    WAITING_CONFIRMATION = "waiting_confirmation"
    FAILED = "failed"


class ToolCallingModel(Protocol):
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResponse: ...


@dataclass(frozen=True, slots=True)
class PendingToolCall:
    call: LLMToolCall
    request: ToolRequest


@dataclass(frozen=True, slots=True)
class ToolAgentRun:
    """Serializable-enough snapshot of a completed, paused, or failed loop."""

    status: ToolRunStatus
    content: str
    messages: tuple[dict[str, Any], ...]
    call_count: int
    seen_calls: frozenset[str]
    pending: PendingToolCall | None = None
    error_code: str | None = None
