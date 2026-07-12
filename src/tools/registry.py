"""Discovery and safe invocation of registered Nexus tools."""

from __future__ import annotations

import asyncio
import copy
from collections.abc import Iterable
from datetime import datetime

from .audit import ToolAuditLog
from .models import (
    RiskLevel,
    Tool,
    ToolDescriptor,
    ToolError,
    ToolPermissionError,
    ToolRequest,
    ToolResult,
    ToolValidationError,
    utc_now,
)
from .permissions import PermissionDecision, PermissionPolicy


class ToolRegistry:
    """Register, discover, authorize, execute, and audit tools."""

    def __init__(
        self,
        tools: Iterable[Tool] = (),
        *,
        policy: PermissionPolicy | None = None,
        audit_log: ToolAuditLog,
        default_timeout: float = 30.0,
    ) -> None:
        if default_timeout <= 0:
            raise ValueError("default_timeout must be greater than zero")
        self._tools: dict[str, Tool] = {}
        self.policy = policy or PermissionPolicy()
        self.audit_log = audit_log
        self.default_timeout = default_timeout
        for tool in tools:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        name = tool.name.strip()
        if not name:
            raise ToolValidationError("Tool name must not be empty")
        if name in self._tools:
            raise ToolValidationError(f"Tool is already registered: {name}")
        self._tools[name] = tool

    def discover(self) -> tuple[ToolDescriptor, ...]:
        return tuple(
            ToolDescriptor(tool.name, tool.description, tool.risk, copy.deepcopy(tool.parameters))
            for tool in sorted(self._tools.values(), key=lambda item: item.name)
        )

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolValidationError(f"Unknown tool: {name}") from exc

    async def invoke(
        self,
        request: ToolRequest,
        *,
        confirmed: bool = False,
        timeout: float | None = None,
    ) -> ToolResult:
        started_at = utc_now()
        try:
            tool = self.get(request.tool_name)
        except ToolError as exc:
            self.audit_log.record(
                request, RiskLevel.READ_ONLY, status="rejected", started_at=started_at,
                error_code=exc.code,
            )
            return self._failure(request, started_at, exc)

        decision = self.policy.decide(tool.risk, confirmed=confirmed)
        if decision is not PermissionDecision.ALLOW:
            required = decision is PermissionDecision.CONFIRM
            message = "User confirmation required" if required else "Tool risk is denied by policy"
            error = ToolPermissionError(message, confirmation_required=required)
            self.audit_log.record(
                request, tool.risk, status="rejected", started_at=started_at,
                error_code=error.code,
            )
            return self._failure(request, started_at, error)

        try:
            tool.validate(dict(request.arguments))
            limit = self.default_timeout if timeout is None else timeout
            if limit <= 0:
                raise ToolValidationError("timeout must be greater than zero")
            output = await asyncio.wait_for(tool.execute(dict(request.arguments)), timeout=limit)
        except asyncio.CancelledError:
            self.audit_log.record(
                request, tool.risk, status="cancelled", started_at=started_at,
                error_code="cancelled",
            )
            raise
        except TimeoutError:
            error = ToolError("Tool invocation timed out", code="timeout")
            self.audit_log.record(
                request, tool.risk, status="failed", started_at=started_at,
                error_code=error.code,
            )
            return self._failure(request, started_at, error)
        except ToolError as exc:
            self.audit_log.record(
                request, tool.risk, status="failed", started_at=started_at,
                error_code=exc.code,
            )
            return self._failure(request, started_at, exc)
        except Exception as exc:
            error = ToolError(str(exc), code="execution_error")
            self.audit_log.record(
                request, tool.risk, status="failed", started_at=started_at,
                error_code=error.code,
            )
            return self._failure(request, started_at, error)

        finished_at = utc_now()
        self.audit_log.record(request, tool.risk, status="succeeded", started_at=started_at)
        return ToolResult(
            request_id=request.id,
            tool_name=request.tool_name,
            success=True,
            output=output,
            started_at=started_at,
            finished_at=finished_at,
        )

    @staticmethod
    def _failure(request: ToolRequest, started_at: datetime, error: ToolError) -> ToolResult:
        return ToolResult(
            request_id=request.id,
            tool_name=request.tool_name,
            success=False,
            error_code=error.code,
            error_message=str(error),
            started_at=started_at,
            finished_at=utc_now(),
        )
