"""End-to-end tests for bounded LLM tool selection and execution."""
from __future__ import annotations

import asyncio
import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from src.llm import LLMResponse, LLMToolCall
from src.tools import (
    RiskLevel,
    ToolAuditLog,
    ToolCallingAgent,
    ToolRegistry,
    ToolRunStatus,
)


class FakeModel:
    def __init__(self, responses: list[LLMResponse]) -> None:
        self.responses = responses
        self.requests: list[tuple[list[dict[str, Any]], list[dict[str, Any]]]] = []
    async def chat(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> LLMResponse:
        self.requests.append((copy.deepcopy(messages), copy.deepcopy(tools)))
        return self.responses.pop(0)


@dataclass
class EchoTool:
    risk: RiskLevel = RiskLevel.READ_ONLY
    delay: float = 0.0
    name: str = "echo"
    description: str = "Echo a value."
    parameters = {
        "type": "object",
        "properties": {"value": {"type": "string"}},
        "required": ["value"],
        "additionalProperties": False,
    }
    def validate(self, arguments: dict[str, Any]) -> None:
        if not isinstance(arguments.get("value"), str):
            raise ValueError("value must be a string")

    async def execute(self, arguments: dict[str, Any]) -> str:
        if self.delay:
            await asyncio.sleep(self.delay)
        return arguments["value"]


def response(content: str = "", call: LLMToolCall | None = None) -> LLMResponse:
    return LLMResponse(content, "fake", tool_calls=() if call is None else (call,))
def agent(tmp_path: Path, model: FakeModel, tool: EchoTool, **kwargs: Any) -> ToolCallingAgent:
    registry = ToolRegistry([tool], audit_log=ToolAuditLog(tmp_path / "audit.jsonl"))
    return ToolCallingAgent(model, registry, **kwargs)


@pytest.mark.asyncio
async def test_model_selects_tool_and_receives_result(tmp_path: Path) -> None:
    model = FakeModel([
        response(call=LLMToolCall("echo", {"value": "hello"})),
        response("The tool returned hello."),
    ])
    runner = agent(tmp_path, model, EchoTool())

    result = await runner.run("Echo hello")

    assert result.status is ToolRunStatus.COMPLETED
    assert result.call_count == 1
    assert model.requests[0][1][0]["function"]["parameters"]["required"] == ["value"]
    assert model.requests[1][0][-1]["role"] == "tool"
    assert '"output": "hello"' in model.requests[1][0][-1]["content"]


@pytest.mark.asyncio
async def test_confirmation_pauses_and_resumes(tmp_path: Path) -> None:
    model = FakeModel([
        response("I need approval", LLMToolCall("echo", {"value": "send"})),
        response("Approved action completed."),
    ])
    runner = agent(tmp_path, model, EchoTool(risk=RiskLevel.EXTERNAL))

    paused = await runner.run("Send it")
    completed = await runner.resume(paused, confirmed=True)

    assert paused.status is ToolRunStatus.WAITING_CONFIRMATION
    assert paused.pending is not None
    assert completed.status is ToolRunStatus.COMPLETED
    assert completed.call_count == 1


@pytest.mark.asyncio
async def test_user_denial_is_returned_to_model(tmp_path: Path) -> None:
    model = FakeModel([
        response(call=LLMToolCall("echo", {"value": "send"})),
        response("I did not send it."),
    ])
    runner = agent(tmp_path, model, EchoTool(risk=RiskLevel.EXTERNAL))

    paused = await runner.run("Send it")
    result = await runner.resume(paused, confirmed=False)

    assert result.status is ToolRunStatus.COMPLETED
    assert "user_denied" in model.requests[1][0][-1]["content"]


@pytest.mark.asyncio
async def test_unknown_tool_failure_can_recover(tmp_path: Path) -> None:
    model = FakeModel([
        response(call=LLMToolCall("invented", {})),
        response("That tool is unavailable."),
    ])
    runner = agent(tmp_path, model, EchoTool())

    result = await runner.run("Invent something")

    assert result.status is ToolRunStatus.COMPLETED
    assert "validation_error" in model.requests[1][0][-1]["content"]


@pytest.mark.asyncio
async def test_repeated_call_and_call_limit_stop_loop(tmp_path: Path) -> None:
    repeated = LLMToolCall("echo", {"value": "same"})
    loop_model = FakeModel([response(call=repeated), response(call=repeated)])
    limited_model = FakeModel([
        response(call=LLMToolCall("echo", {"value": "one"})),
        response(call=LLMToolCall("echo", {"value": "two"})),
    ])

    looped = await agent(tmp_path, loop_model, EchoTool()).run("Loop")
    limited = await agent(tmp_path, limited_model, EchoTool(), max_calls=1).run("Limit")

    assert looped.error_code == "tool_loop"
    assert limited.error_code == "call_limit"


@pytest.mark.asyncio
async def test_cancellation_propagates_through_registry(tmp_path: Path) -> None:
    model = FakeModel([response(call=LLMToolCall("echo", {"value": "slow"}))])
    runner = agent(tmp_path, model, EchoTool(delay=5.0))
    task = asyncio.create_task(runner.run("Slow"))
    await asyncio.sleep(0)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
