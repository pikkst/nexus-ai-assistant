"""Minimal MCP client for streaming and tool-call interactions."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import httpx

from .plugin_models import McpServerConfig
from .models import ToolDescriptor, ToolError, utc_now


class McpError(ToolError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="mcp_error")


class McpTimeoutError(McpError):
    def __init__(self, message: str = "MCP request timed out") -> None:
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class McpToolCallResult:
    content: str
    is_error: bool = False


class McpClient:
    """JSON-RPC client for a single MCP server."""

    def __init__(self, config: McpServerConfig) -> None:
        self.config = config
        self._client = httpx.AsyncClient(
            base_url=config.url.rstrip("/"),
            timeout=config.timeout,
            headers=config.headers,
        )

    async def initialize(self) -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "nexus", "version": "0.1.0"},
            },
        }
        try:
            response = await self._client.post("/", json=payload)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise McpTimeoutError() from exc
        except httpx.HTTPError as exc:
            raise McpError(f"MCP initialize failed: {exc}") from exc
        data = response.json()
        if "error" in data:
            raise McpError(f"MCP initialize error: {data['error']}")
        return data.get("result", {})

    async def list_tools(self) -> list[dict[str, Any]]:
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }
        try:
            response = await self._client.post("/", json=payload)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise McpTimeoutError() from exc
        except httpx.HTTPError as exc:
            raise McpError(f"MCP list_tools failed: {exc}") from exc
        data = response.json()
        if "error" in data:
            raise McpError(f"MCP list_tools error: {data['error']}")
        result = data.get("result", {})
        return list(result.get("tools", []))

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any], *, timeout: float | None = None
    ) -> McpToolCallResult:
        call_timeout = timeout if timeout is not None else self.config.timeout
        payload = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        try:
            response = await self._client.post(
                "/", json=payload, timeout=call_timeout
            )
            response.raise_for_status()
        except asyncio.CancelledError:
            raise
        except httpx.TimeoutException as exc:
            raise McpTimeoutError() from exc
        except httpx.HTTPError as exc:
            raise McpError(f"MCP call_tool failed: {exc}") from exc
        data = response.json()
        if "error" in data:
            raise McpError(f"MCP call_tool error: {data['error']}")
        result = data.get("result", {})
        content = result.get("content", [])
        text_parts = []
        is_error = False
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                    if item.get("type") == "error":
                        is_error = True
        return McpToolCallResult(
            content="".join(text_parts),
            is_error=is_error,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "McpClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()
