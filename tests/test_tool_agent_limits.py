"""Timeout and response-shape limits for the tool-calling agent."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.llm import LLMToolCall
from src.tools import ToolRunStatus
from tests.test_tool_agent import EchoTool, FakeModel, agent, response


@pytest.mark.asyncio
async def test_tool_timeout_is_returned_to_model_for_recovery(tmp_path: Path) -> None:
    model = FakeModel([
        response(call=LLMToolCall("echo", {"value": "slow"})),
        response("The local tool timed out."),
    ])
    runner = agent(tmp_path, model, EchoTool(delay=0.1), tool_timeout=0.01)

    result = await runner.run("Run slowly")

    assert result.status is ToolRunStatus.COMPLETED
    assert '"error_code": "timeout"' in model.requests[1][0][-1]["content"]


@pytest.mark.asyncio
async def test_parallel_calls_fail_without_partial_execution(tmp_path: Path) -> None:
    first = LLMToolCall("echo", {"value": "one"}, index=0)
    second = LLMToolCall("echo", {"value": "two"}, index=1)
    parallel = response()
    parallel = type(parallel)(parallel.content, parallel.model, tool_calls=(first, second))
    runner = agent(tmp_path, FakeModel([parallel]), EchoTool())

    result = await runner.run("Call twice")

    assert result.status is ToolRunStatus.FAILED
    assert result.error_code == "parallel_calls_unsupported"
    assert runner.registry.audit_log.entries() == []
