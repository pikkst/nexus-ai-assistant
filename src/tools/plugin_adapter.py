"""Adapter that wraps plugin and MCP tools into the Nexus Tool protocol."""

from __future__ import annotations

import logging
from typing import Any, Callable

from .models import (
    RiskLevel,
    Tool,
    ToolDescriptor,
    ToolError,
    ToolValidationError,
    utc_now,
)
from .plugin_models import PluginToolSchema

logger = logging.getLogger(__name__)


class PluginTool(Tool):
    """Wraps a PluginToolSchema plus an executor callable."""

    name: str
    description: str
    risk: RiskLevel
    parameters: dict[str, Any]

    def __init__(
        self,
        schema: PluginToolSchema,
        executor: Callable[[dict[str, Any]], Any],
    ) -> None:
        self.name = schema.name
        self.description = schema.description
        self.risk = schema.risk
        self.parameters = schema.parameters
        self._executor = executor

    def validate(self, arguments: dict[str, Any]) -> None:
        required = self.parameters.get("required", [])
        if not isinstance(required, list):
            raise ToolValidationError("Tool parameters.required must be a list")
        missing = [key for key in required if key not in arguments]
        if missing:
            raise ToolValidationError(f"Missing required arguments: {missing}")
        properties = self.parameters.get("properties", {})
        if not isinstance(properties, dict):
            raise ToolValidationError("Tool parameters.properties must be a dict")
        for key, value in arguments.items():
            if key not in properties:
                raise ToolValidationError(f"Unexpected argument: {key}")

    async def execute(self, arguments: dict[str, Any]) -> Any:
        return await self._executor(arguments)


class McpTool(Tool):
    """Wraps an MCP tool descriptor and a live MCP client."""

    name: str
    description: str
    risk: RiskLevel
    parameters: dict[str, Any]

    def __init__(
        self,
        descriptor: dict[str, Any],
        risk: RiskLevel,
        client_factory: Callable[[], Any],
    ) -> None:
        raw_name = descriptor.get("name", "")
        if not raw_name or not isinstance(raw_name, str):
            raise ToolValidationError("MCP tool descriptor must have a string name")
        self.name = raw_name.strip()
        self.description = str(descriptor.get("description", ""))
        self.risk = risk
        self.parameters = descriptor.get("inputSchema", {}) or {}
        self._client_factory = client_factory

    def validate(self, arguments: dict[str, Any]) -> None:
        required = self.parameters.get("required", [])
        if not isinstance(required, list):
            raise ToolValidationError("MCP tool inputSchema.required must be a list")
        missing = [key for key in required if key not in arguments]
        if missing:
            raise ToolValidationError(f"Missing required arguments: {missing}")

    async def execute(self, arguments: dict[str, Any]) -> Any:
        client = self._client_factory()
        try:
            result = await client.call_tool(self.name, dict(arguments))
        finally:
            close = getattr(client, "close", None)
            if close is not None:
                maybe = close()
                if hasattr(maybe, "__await__"):
                    await maybe
        if result.is_error:
            raise ToolError(f"MCP tool {self.name} returned an error: {result.content}")
        return result.content
