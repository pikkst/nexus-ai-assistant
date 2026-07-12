"""Permission, lifecycle, and audit tests for Nexus tools."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from src.tools import (
    PermissionPolicy,
    RiskLevel,
    ToolAuditLog,
    ToolRegistry,
    ToolRequest,
    ToolValidationError,
)


@dataclass
class FakeTool:
    name: str = "fake.echo"
    description: str = "Echo one value."
    risk: RiskLevel = RiskLevel.READ_ONLY
    delay: float = 0.0
    parameters: dict[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {"value": {}},
                "required": ["value"],
            }

    def validate(self, arguments: dict[str, Any]) -> None:
        if "value" not in arguments:
            raise ToolValidationError("value is required")

    async def execute(self, arguments: dict[str, Any]) -> Any:
        if self.delay:
            await asyncio.sleep(self.delay)
        return arguments["value"]


def registry(tmp_path: Path, tool: FakeTool, **kwargs: Any) -> ToolRegistry:
    return ToolRegistry(
        [tool], audit_log=ToolAuditLog(tmp_path / "audit.jsonl"), **kwargs
    )


@pytest.mark.asyncio
async def test_discovery_and_successful_invocation(tmp_path: Path) -> None:
    tools = registry(tmp_path, FakeTool())
    descriptor = tools.discover()[0]

    result = await tools.invoke(ToolRequest("fake.echo", {"value": "hello"}))

    assert descriptor.name == "fake.echo"
    assert descriptor.risk is RiskLevel.READ_ONLY
    descriptor.parameters["required"] = []
    assert tools.discover()[0].parameters["required"] == ["value"]
    assert result.success
    assert result.output == "hello"
    assert tools.audit_log.entries()[0].status == "succeeded"


@pytest.mark.parametrize(
    "risk",
    [RiskLevel.LOCAL_WRITE, RiskLevel.EXTERNAL, RiskLevel.DESTRUCTIVE],
)
@pytest.mark.asyncio
async def test_risky_tools_require_confirmation(tmp_path: Path, risk: RiskLevel) -> None:
    tools = registry(tmp_path, FakeTool(risk=risk))
    request = ToolRequest("fake.echo", {"value": "ok"})

    rejected = await tools.invoke(request)
    allowed = await tools.invoke(request, confirmed=True)

    assert rejected.error_code == "confirmation_required"
    assert allowed.success


@pytest.mark.asyncio
async def test_policy_can_deny_risk_even_when_confirmed(tmp_path: Path) -> None:
    policy = PermissionPolicy(denied_levels=frozenset({RiskLevel.EXTERNAL}))
    tools = registry(tmp_path, FakeTool(risk=RiskLevel.EXTERNAL), policy=policy)

    result = await tools.invoke(
        ToolRequest("fake.echo", {"value": "ok"}), confirmed=True
    )

    assert result.error_code == "permission_denied"


@pytest.mark.asyncio
async def test_validation_unknown_and_timeout_are_structured(tmp_path: Path) -> None:
    tools = registry(tmp_path, FakeTool(delay=0.1), default_timeout=0.01)

    invalid = await tools.invoke(ToolRequest("fake.echo"))
    missing = await tools.invoke(ToolRequest("missing.tool"))
    timed_out = await tools.invoke(ToolRequest("fake.echo", {"value": "slow"}))

    assert invalid.error_code == "validation_error"
    assert missing.error_code == "validation_error"
    assert timed_out.error_code == "timeout"
    assert len(tools.audit_log.entries()) == 3


@pytest.mark.asyncio
async def test_cancellation_is_audited_and_propagated(tmp_path: Path) -> None:
    tools = registry(tmp_path, FakeTool(delay=5.0))
    task = asyncio.create_task(
        tools.invoke(ToolRequest("fake.echo", {"value": "cancel"}))
    )
    await asyncio.sleep(0)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert tools.audit_log.entries()[0].status == "cancelled"


@pytest.mark.asyncio
async def test_audit_redacts_secrets_and_never_stores_output(tmp_path: Path) -> None:
    tools = registry(tmp_path, FakeTool())
    secret = "do-not-log-me"
    request = ToolRequest("fake.echo", {"value": "ordinary", "api_token": secret})

    await tools.invoke(request)
    raw_log = (tmp_path / "audit.jsonl").read_text(encoding="utf-8")
    payload = json.loads(raw_log)

    assert payload["arguments"]["api_token"] == "[REDACTED]"
    assert "output" not in payload
    assert secret not in raw_log
