"""Construction helpers for Nexus's built-in local tools."""

from __future__ import annotations

from pathlib import Path

from .audit import ToolAuditLog
from .filesystem import InspectProjectTool, ListDirectoryTool, ReadTextFileTool
from .permissions import PermissionPolicy
from .registry import ToolRegistry


def create_project_tool_registry(
    project_root: Path | str,
    *,
    audit_path: Path | str = Path("~/.nexus/logs/tool-audit.jsonl"),
    policy: PermissionPolicy | None = None,
    default_timeout: float = 30.0,
) -> ToolRegistry:
    """Create a registry with the built-in read-only project tools."""
    root = Path(project_root).expanduser().resolve()
    return ToolRegistry(
        [ListDirectoryTool(root), ReadTextFileTool(root), InspectProjectTool(root)],
        policy=policy,
        audit_log=ToolAuditLog(audit_path),
        default_timeout=default_timeout,
    )
