"""Construction helper for web research tools."""

from pathlib import Path

from .audit import ToolAuditLog
from .permissions import PermissionPolicy
from .registry import ToolRegistry
from .snapshots import SnapshotStore
from .web_models import PageProvider, SearchProvider
from .web_tools import CompareSourcesTool, OpenPageTool, SaveResearchNoteTool, WebSearchTool


def create_web_research_registry(
    search_provider: SearchProvider, page_provider: PageProvider, *, notes_root: Path | str,
    audit_path: Path | str, policy: PermissionPolicy | None = None,
) -> ToolRegistry:
    root = Path(notes_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    snapshots = SnapshotStore(root, root / ".snapshots")
    return ToolRegistry(
        [WebSearchTool(search_provider), OpenPageTool(page_provider), CompareSourcesTool(),
         SaveResearchNoteTool(root, snapshots)],
        policy=policy, audit_log=ToolAuditLog(audit_path), default_timeout=30,
    )
