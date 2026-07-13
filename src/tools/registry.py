"""Discovery and safe invocation of registered Nexus tools."""

from __future__ import annotations

import asyncio
import copy
import logging
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


logger = logging.getLogger(__name__)


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
        logger.info(
            "ToolRegistry.invoke start: tool=%s confirmed=%s timeout=%s",
            request.tool_name,
            confirmed,
            timeout,
        )
        try:
            tool = self.get(request.tool_name)
        except ToolError as exc:
            logger.warning("ToolRegistry.invoke rejected: tool=%s error=%s", request.tool_name, exc)
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
            logger.warning("ToolRegistry.invoke blocked: tool=%s decision=%s message=%s", request.tool_name, decision.value, message)
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
            logger.debug("ToolRegistry.invoke executing: tool=%s args=%s", request.tool_name, request.arguments)
            output = await asyncio.wait_for(tool.execute(dict(request.arguments)), timeout=limit)
        except asyncio.CancelledError:
            logger.warning("ToolRegistry.invoke cancelled: tool=%s", request.tool_name)
            self.audit_log.record(
                request, tool.risk, status="cancelled", started_at=started_at,
                error_code="cancelled",
            )
            raise
        except TimeoutError:
            error = ToolError("Tool invocation timed out", code="timeout")
            logger.error("ToolRegistry.invoke timeout: tool=%s limit=%s", request.tool_name, limit)
            self.audit_log.record(
                request, tool.risk, status="failed", started_at=started_at,
                error_code=error.code,
            )
            return self._failure(request, started_at, error)
        except ToolError as exc:
            logger.error("ToolRegistry.invoke tool error: tool=%s error=%s", request.tool_name, exc)
            self.audit_log.record(
                request, tool.risk, status="failed", started_at=started_at,
                error_code=exc.code,
            )
            return self._failure(request, started_at, exc)
        except Exception as exc:
            error = ToolError(str(exc), code="execution_error")
            logger.error("ToolRegistry.invoke execution error: tool=%s error=%s", request.tool_name, exc, exc_info=True)
            self.audit_log.record(
                request, tool.risk, status="failed", started_at=started_at,
                error_code=error.code,
            )
            return self._failure(request, started_at, error)

        finished_at = utc_now()
        logger.info("ToolRegistry.invoke success: tool=%s duration=%.3fs output=%r", request.tool_name, (finished_at - started_at).total_seconds(), str(output)[:200])
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
