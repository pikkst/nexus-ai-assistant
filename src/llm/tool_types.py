"""Structured Ollama function-call response types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class LLMToolCall:
    """One function invocation requested by a local model."""

    name: str
    arguments: dict[str, Any]
    index: int = 0

    def as_message_call(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "index": self.index,
                "name": self.name,
                "arguments": dict(self.arguments),
            },
        }
