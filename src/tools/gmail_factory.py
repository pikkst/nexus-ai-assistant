"""Construction helper for Gmail tool registries."""

from __future__ import annotations

from pathlib import Path

from .audit import ToolAuditLog
from .gmail_tools import (
    ArchiveTool, AttachmentMetadataTool, CreateDraftTool, DeleteTool, LabelTool,
    ReadMessageTool, ReplyTool, SearchMessagesTool, SendDraftTool, ThreadSummaryTool,
    UpdateDraftTool,
)
from .gmail_provider import GmailProvider
from .models import RiskLevel
from .permissions import PermissionPolicy
from .registry import ToolRegistry


def create_gmail_registry(
    provider: GmailProvider, *, audit_path: Path | str = Path("~/.nexus/logs/gmail-audit.jsonl"),
    policy: PermissionPolicy | None = None, default_timeout: float = 30.0,
) -> ToolRegistry:
    """Create a registry with Gmail tools wired to the supplied provider."""
    audit_log = ToolAuditLog(audit_path)
    tools = [
        SearchMessagesTool(provider), ReadMessageTool(provider), ThreadSummaryTool(provider),
        AttachmentMetadataTool(provider), CreateDraftTool(provider), UpdateDraftTool(provider),
        SendDraftTool(provider), ReplyTool(provider), LabelTool(provider),
        ArchiveTool(provider), DeleteTool(provider),
    ]
    return ToolRegistry(tools, policy=policy, audit_log=audit_log, default_timeout=default_timeout)
