"""Construction helpers for Nexus's built-in local tools."""

from __future__ import annotations

from pathlib import Path

from .audit import ToolAuditLog
from .commands import EvidenceCommandTool, RunCommandTool
from .development_files import ReplaceTextTool, RestoreSnapshotTool, SearchTextTool, WriteTextTool
from .filesystem import InspectProjectTool, ListDirectoryTool, ReadTextFileTool
from .models import RiskLevel
from .permissions import PermissionPolicy
from .registry import ToolRegistry
from .snapshots import SnapshotStore


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


def create_development_tool_registry(
    project_root: Path | str, *, audit_path: Path | str, snapshot_path: Path | str,
    policy: PermissionPolicy | None = None, allowed_commands: set[str] | None = None,
) -> ToolRegistry:
    """Create the bounded local software-development toolset."""
    root = Path(project_root).expanduser().resolve()
    snapshots = SnapshotStore(root, snapshot_path)
    commands = (
        {"python", "python.exe", "git", "git.exe", "ruff", "ruff.exe"}
        if allowed_commands is None else allowed_commands
    )
    tools = [ListDirectoryTool(root), ReadTextFileTool(root), InspectProjectTool(root), SearchTextTool(root),
        WriteTextTool(root, snapshots), ReplaceTextTool(root, snapshots), RestoreSnapshotTool(root, snapshots),
        RunCommandTool(root, commands),
        EvidenceCommandTool(root, "development.test", "Run project tests.", ["python", "-m", "pytest"], RiskLevel.LOCAL_WRITE),
        EvidenceCommandTool(root, "development.lint", "Run Ruff lint checks.", ["ruff", "check", "."], RiskLevel.READ_ONLY),
        EvidenceCommandTool(root, "development.build", "Build the project.", ["python", "-m", "build"], RiskLevel.LOCAL_WRITE),
        EvidenceCommandTool(root, "git.status", "Return Git working-tree status.", ["git", "status", "--short"], RiskLevel.READ_ONLY),
        EvidenceCommandTool(root, "git.diff", "Return the current Git diff.", ["git", "diff", "--no-ext-diff"], RiskLevel.READ_ONLY)]
    return ToolRegistry(tools, policy=policy, audit_log=ToolAuditLog(audit_path), default_timeout=65)
