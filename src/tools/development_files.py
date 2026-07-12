"""Sandboxed search and recoverable editing tools."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from .filesystem import _RootedTool
from .models import RiskLevel, ToolValidationError
from .snapshots import SnapshotStore, atomic_write, content_hash


class SearchTextTool(_RootedTool):
    name = "filesystem.search_text"
    description = "Search UTF-8 project files for literal text."
    parameters = {"type": "object", "properties": {"query": {"type": "string"},
        "path": {"type": "string"}, "glob": {"type": "string"}}, "required": ["query"],
        "additionalProperties": False}

    def __init__(self, root: Path | str, *, max_results: int = 100) -> None:
        super().__init__(root); self.max_results = max_results

    def validate(self, arguments: dict[str, Any]) -> None:
        if not isinstance(arguments.get("query"), str) or not arguments["query"]:
            raise ToolValidationError("query must be a non-empty string")
        if not self._resolve(arguments.get("path", ".")).is_dir():
            raise ToolValidationError("search path must be a directory")
        glob = Path(arguments.get("glob", "*"))
        if glob.is_absolute() or ".." in glob.parts:
            raise ToolValidationError("glob must not escape the search path")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        base, query = self._resolve(arguments.get("path", ".")), arguments["query"]
        pattern = arguments.get("glob", "*")
        def search() -> list[dict[str, Any]]:
            found = []
            for path in base.rglob(pattern):
                if len(found) >= self.max_results: break
                try:
                    if not path.is_file() or self.root not in path.resolve().parents: continue
                    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                        if query in line:
                            found.append({"path": path.relative_to(self.root).as_posix(),
                                          "line": number, "text": line[:500]})
                            if len(found) >= self.max_results: break
                except (OSError, UnicodeError): pass
            return found
        matches = await asyncio.to_thread(search)
        return {"matches": matches, "count": len(matches), "truncated": len(matches) >= self.max_results}


class WriteTextTool(_RootedTool):
    name, description, risk = "filesystem.write_text", "Atomically create or replace a project text file.", RiskLevel.LOCAL_WRITE
    parameters = {"type": "object", "properties": {"path": {"type": "string"},
        "content": {"type": "string"}}, "required": ["path", "content"], "additionalProperties": False}
    def __init__(self, root: Path | str, snapshots: SnapshotStore) -> None:
        super().__init__(root); self.snapshots = snapshots
    def validate(self, arguments: dict[str, Any]) -> None:
        path = self._resolve(arguments.get("path"))
        if path == self.root or not isinstance(arguments.get("content"), str):
            raise ToolValidationError("path and content must identify a text file")
    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        path, data = self._resolve(arguments["path"]), arguments["content"].encode()
        snapshot = await asyncio.to_thread(self.snapshots.capture, path)
        await asyncio.to_thread(atomic_write, path, data)
        return {"path": path.relative_to(self.root).as_posix(), "snapshot_id": snapshot,
                "bytes": len(data), "sha256": content_hash(data)}


class ReplaceTextTool(WriteTextTool):
    name, description = "filesystem.replace_text", "Atomically replace one exact text occurrence in a project file."
    parameters = {"type": "object", "properties": {"path": {"type": "string"},
        "old": {"type": "string"}, "new": {"type": "string"}},
        "required": ["path", "old", "new"], "additionalProperties": False}
    def validate(self, arguments: dict[str, Any]) -> None:
        path = self._resolve(arguments.get("path"))
        if not path.is_file() or not isinstance(arguments.get("old"), str) or not arguments["old"]:
            raise ToolValidationError("existing file and non-empty old text are required")
        if not isinstance(arguments.get("new"), str): raise ToolValidationError("new must be a string")
    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        path = self._resolve(arguments["path"]); content = await asyncio.to_thread(path.read_text, encoding="utf-8")
        if content.count(arguments["old"]) != 1: raise ToolValidationError("old text must occur exactly once")
        data = content.replace(arguments["old"], arguments["new"]).encode()
        snapshot = await asyncio.to_thread(self.snapshots.capture, path)
        await asyncio.to_thread(atomic_write, path, data)
        return {"path": path.relative_to(self.root).as_posix(), "snapshot_id": snapshot,
                "bytes": len(data), "sha256": content_hash(data)}


class RestoreSnapshotTool(_RootedTool):
    name, description, risk = "filesystem.restore_snapshot", "Restore a file to a captured pre-change state.", RiskLevel.LOCAL_WRITE
    parameters = {"type": "object", "properties": {"snapshot_id": {"type": "string"}},
                  "required": ["snapshot_id"], "additionalProperties": False}
    def __init__(self, root: Path | str, snapshots: SnapshotStore) -> None:
        super().__init__(root); self.snapshots = snapshots
    def validate(self, arguments: dict[str, Any]) -> None:
        if not isinstance(arguments.get("snapshot_id"), str): raise ToolValidationError("snapshot_id is required")
    async def execute(self, arguments: dict[str, Any]) -> dict[str, object]:
        return await asyncio.to_thread(self.snapshots.restore, arguments["snapshot_id"])
