"""Plugin and MCP manifest models for Nexus tool discovery."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .models import RiskLevel

_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _validate_semver(value: str, field_name: str) -> None:
    if not _SEMVER_RE.match(value):
        raise ValueError(f"{field_name} must be semver, got {value!r}")


def _validate_name(value: str, field_name: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$", value.strip()):
        raise ValueError(
            f"{field_name} must start with alphanumeric and contain only letters, digits, dots, hyphens, and underscores"
        )


@dataclass(frozen=True, slots=True)
class McpServerConfig:
    """Connection details for an MCP server."""

    url: str
    transport: str = "streamable_http"
    timeout: float = 30.0
    headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.url or not self.url.strip():
            raise ValueError("McpServerConfig.url must not be empty")
        if self.transport not in {"streamable_http", "sse", "stdio"}:
            raise ValueError(f"Unsupported MCP transport: {self.transport}")
        if self.timeout <= 0:
            raise ValueError("McpServerConfig.timeout must be greater than zero")


@dataclass(frozen=True, slots=True)
class PluginToolSchema:
    """Declared tool surface for one plugin-provided capability."""

    name: str
    description: str
    risk: RiskLevel
    parameters: dict[str, Any]

    def __post_init__(self) -> None:
        _validate_name(self.name, "PluginToolSchema.name")
        if not isinstance(self.parameters, dict):
            raise ValueError("PluginToolSchema.parameters must be a dict")


@dataclass(frozen=True, slots=True)
class PluginManifest:
    """Stable identity and capability description for one installed plugin."""

    name: str
    version: str
    description: str
    enabled: bool = True
    entry_point: str | None = None
    tools: tuple[PluginToolSchema, ...] = ()
    mcp_server: McpServerConfig | None = None

    def __post_init__(self) -> None:
        _validate_name(self.name, "PluginManifest.name")
        _validate_semver(self.version, "PluginManifest.version")
        if self.entry_point is not None:
            _validate_name(self.entry_point, "PluginManifest.entry_point")
        if self.mcp_server is not None and self.entry_point is not None:
            raise ValueError(
                f"Plugin {self.name} cannot declare both entry_point and mcp_server"
            )
        if self.mcp_server is None and self.entry_point is None:
            raise ValueError(
                f"Plugin {self.name} must declare either entry_point or mcp_server"
            )
