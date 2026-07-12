from pathlib import Path
import pytest
from src.tools.development_files import ReplaceTextTool, RestoreSnapshotTool, SearchTextTool, WriteTextTool
from src.tools.models import ToolValidationError
from src.tools.snapshots import SnapshotStore

@pytest.fixture
def file_tools(tmp_path: Path):
    root = tmp_path / "project"; root.mkdir()
    snapshots = SnapshotStore(root, root / ".snapshots")
    return root, WriteTextTool(root, snapshots), ReplaceTextTool(root, snapshots), RestoreSnapshotTool(root, snapshots)

@pytest.mark.asyncio
async def test_atomic_write_patch_and_rollback(file_tools):
    root, write, replace, restore = file_tools
    created = await write.execute({"path": "app.py", "content": "answer = 41\n"})
    changed = await replace.execute({"path": "app.py", "old": "41", "new": "42"})
    assert (root / "app.py").read_text() == "answer = 42\n"
    await restore.execute({"snapshot_id": changed["snapshot_id"]})
    assert (root / "app.py").read_text() == "answer = 41\n"
    await restore.execute({"snapshot_id": created["snapshot_id"]})
    assert not (root / "app.py").exists()

def test_traversal_and_ambiguous_patch_are_rejected(file_tools, tmp_path):
    root, write, replace, _ = file_tools
    with pytest.raises(ToolValidationError): write.validate({"path": "../escape", "content": "x"})
    (root / "a.txt").write_text("x x")
    replace.validate({"path": "a.txt", "old": "x", "new": "y"})
    with pytest.raises(ToolValidationError):
        import asyncio; asyncio.run(replace.execute({"path": "a.txt", "old": "x", "new": "y"}))

@pytest.mark.asyncio
async def test_search_is_bounded_and_skips_symlink_escape(tmp_path):
    root = tmp_path / "root"; root.mkdir(); outside = tmp_path / "secret.txt"; outside.write_text("needle")
    (root / "inside.txt").write_text("needle\nneedle")
    try: (root / "link.txt").symlink_to(outside)
    except OSError: pass
    tool = SearchTextTool(root, max_results=1); tool.validate({"query": "needle"})
    result = await tool.execute({"query": "needle"})
    assert result["count"] == 1 and result["matches"][0]["path"] == "inside.txt"
