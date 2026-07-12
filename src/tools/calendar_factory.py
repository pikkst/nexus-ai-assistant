"""Construction helper for Google Calendar tool registries."""

from __future__ import annotations

from pathlib import Path

from .audit import ToolAuditLog
from .calendar_tools import (
    CreateEventDraftTool,
    CreateEventTool,
    DeleteEventTool,
    FindConflictsTool,
    FindFreeTimeTool,
    GetEventTool,
    ListCalendarsTool,
    ListEventsTool,
    UpdateEventTool,
)
from .calendar_models import CalendarProvider
from .models import RiskLevel
from .permissions import PermissionPolicy
from .registry import ToolRegistry


def create_calendar_registry(
    provider: CalendarProvider, *, audit_path: Path | str = Path("~/.nexus/logs/calendar-audit.jsonl"),
    policy: PermissionPolicy | None = None, default_timeout: float = 30.0,
) -> ToolRegistry:
    """Create a registry with Google Calendar tools wired to the supplied provider."""
    audit_log = ToolAuditLog(audit_path)
    tools = [
        ListCalendarsTool(provider), ListEventsTool(provider), GetEventTool(provider),
        FindFreeTimeTool(provider), FindConflictsTool(provider), CreateEventDraftTool(provider),
        CreateEventTool(provider), UpdateEventTool(provider), DeleteEventTool(provider),
    ]
    return ToolRegistry(tools, policy=policy, audit_log=audit_log, default_timeout=default_timeout)
