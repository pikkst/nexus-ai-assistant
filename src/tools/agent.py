"""Bounded LLM-to-registry tool-calling orchestration."""

from __future__ import annotations

import json
from typing import Any

from src.llm import LLMToolCall

from .calling import PendingToolCall, ToolAgentRun, ToolCallingModel, ToolRunStatus
from .models import ToolRequest, ToolResult
from .registry import ToolRegistry

class ToolCallingAgent:
    """Let a model select tools without bypassing registry controls."""

    def __init__(
        self,
        model: ToolCallingModel,
        registry: ToolRegistry,
        *,
        max_calls: int = 8,
        tool_timeout: float = 30.0,
    ) -> None:
        if max_calls < 1:
            raise ValueError("max_calls must be positive")
        if tool_timeout <= 0:
            raise ValueError("tool_timeout must be positive")
        self.model = model
        self.registry = registry
        self.max_calls = max_calls
        self.tool_timeout = tool_timeout

    async def run(self, prompt: str) -> ToolAgentRun:
        """Start a bounded tool-capable conversation."""
        if not prompt.strip():
            raise ValueError("prompt must not be empty")
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt.strip()}]
        return await self._continue(messages, 0, set())

    async def resume(self, run: ToolAgentRun, *, confirmed: bool) -> ToolAgentRun:
        """Resume a call paused for user confirmation."""
        if run.status is not ToolRunStatus.WAITING_CONFIRMATION or run.pending is None:
            raise ValueError("run is not waiting for confirmation")
        messages = [dict(message) for message in run.messages]
        if confirmed:
            result = await self.registry.invoke(
                run.pending.request, confirmed=True, timeout=self.tool_timeout
            )
        else:
            result = ToolResult(
                request_id=run.pending.request.id,
                tool_name=run.pending.request.tool_name,
                success=False,
                error_code="user_denied",
                error_message="User denied tool confirmation",
            )
        messages.append(self._tool_message(run.pending.call, result))
        return await self._continue(messages, run.call_count + 1, set(run.seen_calls))

    async def _continue(
        self,
        messages: list[dict[str, Any]],
        call_count: int,
        seen: set[str],
    ) -> ToolAgentRun:
        schemas = self._schemas()
        while True:
            response = await self.model.chat(messages, schemas)
            if not response.tool_calls:
                messages.append({"role": "assistant", "content": response.content})
                return self._run(ToolRunStatus.COMPLETED, response.content, messages, call_count, seen)
            if len(response.tool_calls) != 1:
                return self._run(
                    ToolRunStatus.FAILED, response.content, messages, call_count, seen,
                    error_code="parallel_calls_unsupported",
                )
            call = response.tool_calls[0]
            messages.append(self._assistant_message(response.content, call))
            if call_count >= self.max_calls:
                return self._run(
                    ToolRunStatus.FAILED, response.content, messages, call_count, seen,
                    error_code="call_limit",
                )
            fingerprint = self._fingerprint(call)
            if fingerprint in seen:
                return self._run(
                    ToolRunStatus.FAILED, response.content, messages, call_count, seen,
                    error_code="tool_loop",
                )
            seen.add(fingerprint)
            request = ToolRequest(call.name, dict(call.arguments))
            result = await self.registry.invoke(request, timeout=self.tool_timeout)
            if result.error_code == "confirmation_required":
                pending = PendingToolCall(call, request)
                return self._run(
                    ToolRunStatus.WAITING_CONFIRMATION, response.content, messages,
                    call_count, seen, pending=pending,
                )
            messages.append(self._tool_message(call, result))
            call_count += 1

    def _schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": item.name,
                    "description": item.description,
                    "parameters": item.parameters,
                },
            }
            for item in self.registry.discover()
        ]

    @staticmethod
    def _assistant_message(content: str, call: LLMToolCall) -> dict[str, Any]:
        return {
            "role": "assistant",
            "content": content,
            "tool_calls": [call.as_message_call()],
        }

    @staticmethod
    def _tool_message(call: LLMToolCall, result: ToolResult) -> dict[str, Any]:
        payload = {
            "success": result.success,
            "output": result.output,
            "error_code": result.error_code,
            "error_message": result.error_message,
        }
        return {
            "role": "tool",
            "tool_name": call.name,
            "content": json.dumps(payload, ensure_ascii=False, default=str),
        }

    @staticmethod
    def _fingerprint(call: LLMToolCall) -> str:
        return call.name + ":" + json.dumps(call.arguments, sort_keys=True, default=str)

    @staticmethod
    def _run(
        status: ToolRunStatus, content: str, messages: list[dict[str, Any]],
        call_count: int, seen: set[str], *, pending: PendingToolCall | None = None,
        error_code: str | None = None,
    ) -> ToolAgentRun:
        return ToolAgentRun(
            status, content, tuple(messages), call_count, frozenset(seen), pending, error_code
        )
