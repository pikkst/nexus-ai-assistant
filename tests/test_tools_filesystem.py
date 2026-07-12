"""Tests for sandboxed read-only project tools."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.tools import (
    InspectProjectTool,
    ListDirectoryTool,
    ReadTextFileTool,
    ToolAuditLog,
    ToolRegistry,
    ToolRequest,
    create_project_tool_registry,
)


def make_registry(root: Path, audit_path: Path) -> ToolRegistry:
    return ToolRegistry(
        [ListDirectoryTool(root), ReadTextFileTool(root), InspectProjectTool(root)],
        audit_log=ToolAuditLog(audit_path),
    )


@pytest.mark.asyncio
async def test_list_and_read_are_confined_to_root(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "note.txt").write_text("Nexus local file", encoding="utf-8")
    tools = make_registry(project, tmp_path / "audit.jsonl")

    listing = await tools.invoke(ToolRequest("filesystem.list_directory", {"path": "."}))
    content = await tools.invoke(ToolRequest("filesystem.read_text", {"path": "note.txt"}))
    escaped = await tools.invoke(ToolRequest("filesystem.read_text", {"path": "../secret"}))

    assert listing.success
    assert listing.output[0]["name"] == "note.txt"
    assert content.output["content"] == "Nexus local file"
    assert escaped.error_code == "validation_error"


@pytest.mark.asyncio
async def test_large_and_missing_files_are_rejected(tmp_path: Path) -> None:
    (tmp_path / "large.txt").write_text("too large", encoding="utf-8")
    tool = ReadTextFileTool(tmp_path, max_bytes=3)
    tools = ToolRegistry([tool], audit_log=ToolAuditLog(tmp_path / "audit.jsonl"))

    large = await tools.invoke(ToolRequest(tool.name, {"path": "large.txt"}))
    missing = await tools.invoke(ToolRequest(tool.name, {"path": "missing.txt"}))

    assert large.error_code == "validation_error"
    assert missing.error_code == "validation_error"


@pytest.mark.asyncio
async def test_project_inspection_is_structured_and_read_only(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "app.py").write_text("", encoding="utf-8")
    (tmp_path / "tests" / "test_app.py").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]", encoding="utf-8")
    tools = make_registry(tmp_path, tmp_path / "audit.jsonl")

    result = await tools.invoke(ToolRequest("project.inspect"))

    assert result.success
    assert result.output["has_pyproject"]
    assert result.output["source_file_count"] == 1
    assert result.output["test_file_count"] == 1


def test_default_project_registry_discovers_all_builtin_tools(tmp_path: Path) -> None:
    tools = create_project_tool_registry(
        tmp_path, audit_path=tmp_path / "audit.jsonl"
    )

    assert [item.name for item in tools.discover()] == [
        "filesystem.list_directory",
        "filesystem.read_text",
        "project.inspect",
    ]
