from pathlib import Path
import pytest
from src.tools.factory import create_development_tool_registry
from src.tools.models import ToolRequest

@pytest.mark.asyncio
async def test_write_requires_confirmation_and_evidence_is_structured(tmp_path: Path):
    root = tmp_path / "project"; root.mkdir()
    registry = create_development_tool_registry(
        root, audit_path=root / "audit.jsonl", snapshot_path=root / ".snapshots",
        allowed_commands=set(),
    )
    request = ToolRequest("filesystem.write_text", {"path": "hello.txt", "content": "hello"})
    denied = await registry.invoke(request)
    assert not denied.success and denied.error_code == "confirmation_required"
    written = await registry.invoke(request, confirmed=True)
    assert written.success and (root / "hello.txt").read_text() == "hello"
    descriptors = {item.name: item for item in registry.discover()}
    assert "development.test" in descriptors and "git.diff" in descriptors

def test_snapshot_storage_cannot_escape_workspace(tmp_path: Path):
    root = tmp_path / "project"; root.mkdir()
    with pytest.raises(ValueError, match="inside"):
        create_development_tool_registry(
            root, audit_path=root / "audit", snapshot_path=tmp_path / "outside",
        )
