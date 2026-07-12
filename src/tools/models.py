"""Typed contracts shared by all Nexus tools."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RiskLevel(Enum):
    """User-impact class of a tool invocation."""

    READ_ONLY = "read_only"
    LOCAL_WRITE = "local_write"
    EXTERNAL = "external"
    DESTRUCTIVE = "destructive"


class ToolError(RuntimeError):
    """Base error with a stable machine-readable code."""

    def __init__(self, message: str, *, code: str = "tool_error") -> None:
        super().__init__(message)
        self.code = code


class ToolValidationError(ToolError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="validation_error")


class ToolPermissionError(ToolError):
    def __init__(self, message: str, *, confirmation_required: bool = False) -> None:
        code = "confirmation_required" if confirmation_required else "permission_denied"
        super().__init__(message, code=code)
        self.confirmation_required = confirmation_required


@dataclass(frozen=True, slots=True)
class ToolRequest:
    """One immutable request to invoke a registered tool."""

    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Structured outcome returned for successful and failed invocations."""

    request_id: str
    tool_name: str
    success: bool
    output: Any = None
    error_code: str | None = None
    error_message: str | None = None
    started_at: datetime = field(default_factory=utc_now)
    finished_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class ToolDescriptor:
    name: str
    description: str
    risk: RiskLevel


class Tool(Protocol):
    """Contract implemented by every Nexus tool."""

    name: str
    description: str
    risk: RiskLevel

    def validate(self, arguments: dict[str, Any]) -> None: ...
    async def execute(self, arguments: dict[str, Any]) -> Any: ...
