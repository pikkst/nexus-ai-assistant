"""Local language model integration for Nexus."""

from .client import (
    LLMClient,
    LLMConfig,
    LLMError,
    LLMResponse,
    LLMTimeoutError,
    LLMUnavailableError,
)
from .prompts import DEFAULT_SYSTEM_PROMPT, build_messages

__all__ = [
    "DEFAULT_SYSTEM_PROMPT",
    "LLMClient",
    "LLMConfig",
    "LLMError",
    "LLMResponse",
    "LLMTimeoutError",
    "LLMUnavailableError",
    "build_messages",
]
