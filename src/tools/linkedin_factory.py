"""Construction helper for LinkedIn tool registries."""

from __future__ import annotations

from pathlib import Path

from .audit import ToolAuditLog
from .linkedin_tools import (
    AnalyzePostTool,
    AnalyzeProfileTool,
    CreateMessageDraftTool,
    CreatePostDraftTool,
    DetectOfficialApiCapabilitiesTool,
    ImproveProfileTool,
    ImportCompanyTool,
    ImportPostTool,
    ImportProfileTool,
    PublishPostTool,
    SendMessageTool,
)
from .linkedin_models import LinkedInProvider
from .linkedin_provider import MockLinkedInProvider
from .permissions import PermissionPolicy
from .registry import ToolRegistry


def create_linkedin_registry(
    provider: LinkedInProvider, *, audit_path: Path | str = Path("~/.nexus/logs/linkedin-audit.jsonl"),
    policy: PermissionPolicy | None = None, default_timeout: float = 30.0,
) -> ToolRegistry:
    """Create a registry with LinkedIn tools wired to the supplied provider."""
    audit_log = ToolAuditLog(audit_path)
    tools = [
        DetectOfficialApiCapabilitiesTool(provider),
        AnalyzeProfileTool(provider),
        AnalyzePostTool(provider),
        ImportProfileTool(provider),
        ImportPostTool(provider),
        ImportCompanyTool(provider),
        CreatePostDraftTool(provider),
        CreateMessageDraftTool(provider),
        ImproveProfileTool(provider),
        PublishPostTool(provider),
        SendMessageTool(provider),
    ]
    return ToolRegistry(tools, policy=policy, audit_log=audit_log, default_timeout=default_timeout)
