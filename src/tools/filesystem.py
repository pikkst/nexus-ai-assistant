"""Sandboxed read-only filesystem and project-inspection tools."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from .models import RiskLevel, ToolValidationError


class _RootedTool:
    risk = RiskLevel.READ_ONLY

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).expanduser().resolve()

    def _resolve(self, value: Any) -> Path:
        if not isinstance(value, str):
            raise ToolValidationError("path must be a string")
        candidate = (self.root / value).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ToolValidationError("path escapes the configured project root")
        return candidate


class ListDirectoryTool(_RootedTool):
    name = "filesystem.list_directory"
    description = "List files and directories within the configured project root."
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Relative directory path"}},
        "additionalProperties": False,
    }

    def validate(self, arguments: dict[str, Any]) -> None:
        path = self._resolve(arguments.get("path", "."))
        if not path.is_dir():
            raise ToolValidationError("directory does not exist")

    async def execute(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        path = self._resolve(arguments.get("path", "."))

        def list_entries() -> list[dict[str, Any]]:
            return [
                {
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                }
                for item in sorted(path.iterdir(), key=lambda entry: entry.name.casefold())
            ]

        return await asyncio.to_thread(list_entries)


class ReadTextFileTool(_RootedTool):
    name = "filesystem.read_text"
    description = "Read a UTF-8 text file within the configured project root."
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Relative file path"}},
        "required": ["path"],
        "additionalProperties": False,
    }

    def __init__(self, root: Path | str, *, max_bytes: int = 262_144) -> None:
        super().__init__(root)
        if max_bytes < 1:
            raise ValueError("max_bytes must be positive")
        self.max_bytes = max_bytes

    def validate(self, arguments: dict[str, Any]) -> None:
        path = self._resolve(arguments.get("path"))
        if not path.is_file():
            raise ToolValidationError("file does not exist")
        if path.stat().st_size > self.max_bytes:
            raise ToolValidationError(f"file exceeds {self.max_bytes} byte limit")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        path = self._resolve(arguments.get("path"))
        content = await asyncio.to_thread(path.read_text, encoding="utf-8")
        return {
            "path": path.relative_to(self.root).as_posix(),
            "content": content,
            "characters": len(content),
        }


class InspectProjectTool(_RootedTool):
    name = "project.inspect"
    description = "Summarize the configured local Python project without modifying it."
    parameters = {"type": "object", "properties": {}, "additionalProperties": False}

    def validate(self, arguments: dict[str, Any]) -> None:
        if arguments:
            raise ToolValidationError("project.inspect does not accept arguments")
        if not self.root.is_dir():
            raise ToolValidationError("project root does not exist")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        def inspect() -> dict[str, Any]:
            source_files = list((self.root / "src").rglob("*.py"))
            test_files = list((self.root / "tests").rglob("test_*.py"))
            return {
                "name": self.root.name,
                "has_pyproject": (self.root / "pyproject.toml").is_file(),
                "has_git": (self.root / ".git").exists(),
                "source_file_count": len(source_files),
                "test_file_count": len(test_files),
                "top_level": sorted(item.name for item in self.root.iterdir()),
            }

        return await asyncio.to_thread(inspect)
