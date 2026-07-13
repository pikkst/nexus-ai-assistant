"""Discovery, enable/disable, isolation, collisions, failures, and uninstall tests."""

from __future__ import annotations

import asyncio
import json
import sys
import types
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.tools import (
    McpClient,
    McpError,
    McpServerConfig,
    McpTimeoutError,
    PluginDuplicateNameError,
    PluginLoadError,
    PluginManager,
    PluginManifest,
    PluginSchemaError,
    PluginTool,
    PluginToolSchema,
    PluginVersionConflictError,
    RiskLevel,
    ToolAuditLog,
    ToolRegistry,
    ToolRequest,
    ToolValidationError,
)


def _run(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            asyncio.set_event_loop(None)
    else:
        # Already in an event loop (e.g. pytest-asyncio async test)
        return loop.run_until_complete(coro)


def _write_manifest(path: Path, data: dict[str, Any]) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    manifest = path / "manifest.json"
    manifest.write_text(json.dumps(data), encoding="utf-8")
    return manifest


def _registry(tmp_path: Path) -> ToolRegistry:
    return ToolRegistry(audit_log=ToolAuditLog(tmp_path / "audit.jsonl"))


def _manager(tmp_path: Path, plugins_dir: Path) -> PluginManager:
    return PluginManager(plugins_dir, registry=_registry(tmp_path))


def _fake_local_tool(name: str = "sample.echo") -> PluginTool:
    schema = PluginToolSchema(
        name=name,
        description="Echo a value.",
        risk=RiskLevel.READ_ONLY,
        parameters={
            "type": "object",
            "properties": {"value": {}},
            "required": ["value"],
        },
    )

    async def execute(arguments: dict[str, Any]) -> Any:
        return arguments.get("value")

    return PluginTool(schema, execute)


class TestPluginDiscovery:
    def test_discover_empty_when_missing_dir(self, tmp_path: Path) -> None:
        manager = _manager(tmp_path, tmp_path / "missing")
        assert manager.discover() == ()

    def test_discover_skips_malformed_manifest(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        bad = plugin_dir / "bad_plugin"
        bad.mkdir()
        (bad / "manifest.json").write_text("not-json", encoding="utf-8")
        assert _manager(tmp_path, plugin_dir).discover() == ()

    def test_discover_loads_valid_manifest(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        _write_manifest(
            plugin_dir / "hello",
            {
                "name": "hello",
                "version": "1.0.0",
                "description": "Hello plugin",
                "enabled": True,
                "entry_point": "fake_plugin_module",
                "tools": [
                    {
                        "name": "hello.greet",
                        "description": "Say hello.",
                        "risk": "read_only",
                        "parameters": {
                            "type": "object",
                            "properties": {"name": {"type": "string"}},
                            "required": ["name"],
                        },
                    }
                ],
            },
        )
        manifests = _manager(tmp_path, plugin_dir).discover()
        assert len(manifests) == 1
        assert manifests[0].name == "hello"
        assert len(manifests[0].tools) == 1

    def test_discover_skips_disabled_manifest(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        _write_manifest(
            plugin_dir / "disabled_plugin",
            {
                "name": "disabled_plugin",
                "version": "1.0.0",
                "description": "Disabled",
                "enabled": False,
                "entry_point": "fake_plugin_module",
                "tools": [],
            },
        )
        manifests = _manager(tmp_path, plugin_dir).discover()
        assert len(manifests) == 1
        assert manifests[0].enabled is False

    def test_discover_rejects_invalid_name(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        _write_manifest(
            plugin_dir / "bad!name",
            {"name": "bad!name", "version": "1.0.0", "entry_point": "m", "tools": []},
        )
        assert _manager(tmp_path, plugin_dir).discover() == ()

    def test_discover_rejects_invalid_version(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        _write_manifest(
            plugin_dir / "badver",
            {"name": "badver", "version": "v1.0", "entry_point": "m", "tools": []},
        )
        assert _manager(tmp_path, plugin_dir).discover() == ()


class TestPluginLoad:
    def test_load_registers_tools(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        _write_manifest(
            plugin_dir / "hello",
            {
                "name": "hello",
                "version": "1.0.0",
                "description": "Hello",
                "enabled": True,
                "entry_point": "fake_plugin_module",
                "tools": [],
            },
        )
        registry = _registry(tmp_path)
        manager = PluginManager(plugin_dir, registry=registry)
        tool = _fake_local_tool("hello.greet")
        import sys
        import types
        fake_module = types.ModuleType("fake_plugin_module")
        fake_module.create_tools = lambda: [tool]
        sys.modules["fake_plugin_module"] = fake_module
        try:
            manifest = manager.discover()[0]
            loaded = _run(manager.load(manifest))
            assert "hello.greet" in registry._tools
            assert loaded.tool_names == frozenset({"hello.greet"})
        finally:
            sys.modules.pop("fake_plugin_module", None)

    def test_load_raises_on_version_conflict(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        _write_manifest(
            plugin_dir / "hello",
            {
                "name": "hello",
                "version": "1.0.0",
                "description": "Hello",
                "enabled": True,
                "entry_point": "fake_plugin_module",
                "tools": [],
            },
        )
        registry = _registry(tmp_path)
        manager = PluginManager(plugin_dir, registry=registry)
        import sys, types
        fake_module = types.ModuleType("fake_plugin_module")
        fake_module.create_tools = lambda: [_fake_local_tool()]
        sys.modules["fake_plugin_module"] = fake_module
        try:
            manifest = manager.discover()[0]
            _run(manager.load(manifest))
            conflict = PluginManifest(
                name="hello", version="2.0.0", description="Hello v2",
                enabled=True, entry_point="fake_plugin_module", tools=(),
            )
            with pytest.raises(PluginVersionConflictError):
                _run(manager.load(conflict))
        finally:
            sys.modules.pop("fake_plugin_module", None)

    def test_load_raises_on_duplicate_tool_name(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        _write_manifest(
            plugin_dir / "hello",
            {
                "name": "hello",
                "version": "1.0.0",
                "description": "Hello",
                "enabled": True,
                "entry_point": "fake_plugin_module",
                "tools": [],
            },
        )
        registry = _registry(tmp_path)
        registry.register(_fake_local_tool("existing.tool"))
        manager = PluginManager(plugin_dir, registry=registry)
        import sys, types
        fake_module = types.ModuleType("fake_plugin_module")
        fake_module.create_tools = lambda: [_fake_local_tool("existing.tool")]
        sys.modules["fake_plugin_module"] = fake_module
        try:
            manifest = manager.discover()[0]
            with pytest.raises(PluginDuplicateNameError):
                _run(manager.load(manifest))
        finally:
            sys.modules.pop("fake_plugin_module", None)

    def test_load_raises_on_duplicate_between_plugins(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        _write_manifest(
            plugin_dir / "alpha",
            {
                "name": "alpha",
                "version": "1.0.0",
                "description": "Alpha",
                "enabled": True,
                "entry_point": "alpha_module",
                "tools": [],
            },
        )
        _write_manifest(
            plugin_dir / "beta",
            {
                "name": "beta",
                "version": "1.0.0",
                "description": "Beta",
                "enabled": True,
                "entry_point": "beta_module",
                "tools": [],
            },
        )
        registry = _registry(tmp_path)
        manager = PluginManager(plugin_dir, registry=registry)
        import sys, types
        alpha = types.ModuleType("alpha_module")
        alpha.create_tools = lambda: [_fake_local_tool("shared.tool")]
        beta = types.ModuleType("beta_module")
        beta.create_tools = lambda: [_fake_local_tool("shared.tool")]
        sys.modules.update({"alpha_module": alpha, "beta_module": beta})
        try:
            manifests = manager.discover()
            _run(manager.load(manifests[0]))
            with pytest.raises(PluginDuplicateNameError):
                _run(manager.load(manifests[1]))
        finally:
            sys.modules.pop("alpha_module", None)
            sys.modules.pop("beta_module", None)


class TestPluginEnableDisable:
    def test_disable_removes_tools(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        _write_manifest(
            plugin_dir / "hello",
            {
                "name": "hello",
                "version": "1.0.0",
                "description": "Hello",
                "enabled": True,
                "entry_point": "fake_plugin_module",
                "tools": [],
            },
        )
        registry = _registry(tmp_path)
        manager = PluginManager(plugin_dir, registry=registry)
        import sys, types
        fake_module = types.ModuleType("fake_plugin_module")
        fake_module.create_tools = lambda: [_fake_local_tool("hello.greet")]
        sys.modules["fake_plugin_module"] = fake_module
        try:
            manifest = manager.discover()[0]
            _run(manager.load(manifest))
            assert "hello.greet" in registry._tools
            manager.disable("hello")
            assert "hello.greet" not in registry._tools
        finally:
            sys.modules.pop("fake_plugin_module", None)

    def test_enable_reloads_tools(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        _write_manifest(
            plugin_dir / "hello",
            {
                "name": "hello",
                "version": "1.0.0",
                "description": "Hello",
                "enabled": True,
                "entry_point": "fake_plugin_module",
                "tools": [],
            },
        )
        registry = _registry(tmp_path)
        manager = PluginManager(plugin_dir, registry=registry)
        import sys, types
        fake_module = types.ModuleType("fake_plugin_module")
        fake_module.create_tools = lambda: [_fake_local_tool("hello.greet")]
        sys.modules["fake_plugin_module"] = fake_module
        try:
            manifest = manager.discover()[0]
            _run(manager.load(manifest))
            manager.disable("hello")
            _run(manager.enable("hello"))
            assert "hello.greet" in registry._tools
        finally:
            sys.modules.pop("fake_plugin_module", None)

    def test_disable_does_not_affect_core_tools(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        _write_manifest(
            plugin_dir / "hello",
            {
                "name": "hello",
                "version": "1.0.0",
                "description": "Hello",
                "enabled": True,
                "entry_point": "fake_plugin_module",
                "tools": [],
            },
        )
        core_tool = _fake_local_tool("core.tool")
        registry = ToolRegistry([core_tool], audit_log=ToolAuditLog(tmp_path / "audit.jsonl"))
        manager = PluginManager(plugin_dir, registry=registry)
        import sys, types
        fake_module = types.ModuleType("fake_plugin_module")
        fake_module.create_tools = lambda: [_fake_local_tool()]
        sys.modules["fake_plugin_module"] = fake_module
        try:
            manifest = manager.discover()[0]
            _run(manager.load(manifest))
            manager.disable("hello")
            assert "core.tool" in registry._tools
            assert "hello.greet" not in registry._tools
        finally:
            sys.modules.pop("fake_plugin_module", None)


class TestPluginFailures:
    def test_load_raises_on_missing_entry_point(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        _write_manifest(
            plugin_dir / "hello",
            {
                "name": "hello",
                "version": "1.0.0",
                "description": "Hello",
                "enabled": True,
                "entry_point": "nonexistent_module_xyz",
                "tools": [],
            },
        )
        manager = _manager(tmp_path, plugin_dir)
        manifest = manager.discover()[0]
        with pytest.raises(PluginLoadError, match="Cannot import plugin entry point"):
            _run(manager.load(manifest))

    def test_load_raises_when_entry_point_missing_create_tools(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        _write_manifest(
            plugin_dir / "hello",
            {
                "name": "hello",
                "version": "1.0.0",
                "description": "Hello",
                "enabled": True,
                "entry_point": "fake_no_create",
                "tools": [],
            },
        )
        import sys, types
        fake_module = types.ModuleType("fake_no_create")
        sys.modules["fake_no_create"] = fake_module
        try:
            manager = _manager(tmp_path, plugin_dir)
            manifest = manager.discover()[0]
            with pytest.raises(PluginLoadError, match="does not expose create_tools"):
                _run(manager.load(manifest))
        finally:
            sys.modules.pop("fake_no_create", None)

    def test_load_raises_on_disabled_manifest(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        _write_manifest(
            plugin_dir / "hello",
            {
                "name": "hello",
                "version": "1.0.0",
                "description": "Hello",
                "enabled": False,
                "entry_point": "m",
                "tools": [],
            },
        )
        manager = _manager(tmp_path, plugin_dir)
        manifest = manager.discover()[0]
        with pytest.raises(PluginLoadError, match="disabled"):
            _run(manager.load(manifest))

    def test_load_all_enabled_skips_broken_plugins(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        _write_manifest(
            plugin_dir / "good",
            {
                "name": "good",
                "version": "1.0.0",
                "description": "Good",
                "enabled": True,
                "entry_point": "fake_plugin_module",
                "tools": [],
            },
        )
        _write_manifest(
            plugin_dir / "bad",
            {
                "name": "bad",
                "version": "1.0.0",
                "description": "Bad",
                "enabled": True,
                "entry_point": "nonexistent_xyz",
                "tools": [],
            },
        )
        import sys, types
        fake_module = types.ModuleType("fake_plugin_module")
        fake_module.create_tools = lambda: [_fake_local_tool()]
        sys.modules["fake_plugin_module"] = fake_module
        try:
            manager = _manager(tmp_path, plugin_dir)
            loaded = _run(manager.load_all_enabled())
            assert len(loaded) == 1
            assert loaded[0].manifest.name == "good"
        finally:
            sys.modules.pop("fake_plugin_module", None)

    def test_load_skips_malformed_mcp_tools_safely(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        _write_manifest(
            plugin_dir / "mcp_bad",
            {
                "name": "mcp_bad",
                "version": "1.0.0",
                "description": "MCP bad",
                "enabled": True,
                "mcp_server": {
                    "url": "http://localhost:9999",
                    "transport": "streamable_http",
                },
            },
        )
        manager = _manager(tmp_path, plugin_dir)
        manifest = manager.discover()[0]

        mock_client = MagicMock()
        mock_client.initialize = AsyncMock()
        mock_client.list_tools = AsyncMock(return_value=[{"description": "no name"}])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        from src.tools import plugin_discovery
        original = plugin_discovery.McpClient
        plugin_discovery.McpClient = lambda config: mock_client
        try:
            loaded = _run(manager.load(manifest))
            assert loaded.tools == ()
        finally:
            plugin_discovery.McpClient = original

    def test_load_raises_on_unavailable_mcp_server(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        _write_manifest(
            plugin_dir / "mcp_down",
            {
                "name": "mcp_down",
                "version": "1.0.0",
                "description": "MCP down",
                "enabled": True,
                "mcp_server": {
                    "url": "http://localhost:1",
                    "transport": "streamable_http",
                },
            },
        )
        manager = _manager(tmp_path, plugin_dir)
        manifest = manager.discover()[0]
        with pytest.raises(PluginLoadError, match="unavailable"):
            _run(manager.load(manifest))


class TestPluginUninstall:
    def test_unload_removes_all_tools(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        _write_manifest(
            plugin_dir / "hello",
            {
                "name": "hello",
                "version": "1.0.0",
                "description": "Hello",
                "enabled": True,
                "entry_point": "fake_plugin_module",
                "tools": [],
            },
        )
        registry = _registry(tmp_path)
        manager = PluginManager(plugin_dir, registry=registry)
        import sys, types
        fake_module = types.ModuleType("fake_plugin_module")
        fake_module.create_tools = lambda: [
            _fake_local_tool("hello.greet"),
            _fake_local_tool("hello.farewell"),
        ]
        sys.modules["fake_plugin_module"] = fake_module
        try:
            manifest = manager.discover()[0]
            _run(manager.load(manifest))
            assert "hello.greet" in registry._tools
            assert "hello.farewell" in registry._tools
            manager.unload("hello")
            assert "hello.greet" not in registry._tools
            assert "hello.farewell" not in registry._tools
        finally:
            sys.modules.pop("fake_plugin_module", None)

    def test_unload_is_idempotent(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        _write_manifest(
            plugin_dir / "hello",
            {
                "name": "hello",
                "version": "1.0.0",
                "description": "Hello",
                "enabled": True,
                "entry_point": "fake_plugin_module",
                "tools": [],
            },
        )
        manager = _manager(tmp_path, plugin_dir)
        manager.unload("nonexistent")
        manager.unload("hello")


class TestPluginToolAdapter:
    def test_plugin_tool_validates_arguments(self) -> None:
        schema = PluginToolSchema(
            name="sample.echo",
            description="Echo.",
            risk=RiskLevel.READ_ONLY,
            parameters={
                "type": "object",
                "properties": {"value": {}},
                "required": ["value"],
            },
        )

        async def execute(arguments: dict[str, Any]) -> Any:
            return arguments["value"]

        tool = PluginTool(schema, execute)
        with pytest.raises(ToolValidationError, match="Missing required arguments"):
            tool.validate({})

    def test_plugin_tool_rejects_unexpected_argument(self) -> None:
        schema = PluginToolSchema(
            name="sample.echo",
            description="Echo.",
            risk=RiskLevel.READ_ONLY,
            parameters={
                "type": "object",
                "properties": {"value": {}},
                "required": ["value"],
            },
        )

        async def execute(arguments: dict[str, Any]) -> Any:
            return arguments["value"]

        tool = PluginTool(schema, execute)
        with pytest.raises(ToolValidationError, match="Unexpected argument"):
            tool.validate({"value": "ok", "extra": 1})

    @pytest.mark.asyncio
    async def test_plugin_tool_execute_roundtrip(self) -> None:
        schema = PluginToolSchema(
            name="sample.echo",
            description="Echo.",
            risk=RiskLevel.READ_ONLY,
            parameters={
                "type": "object",
                "properties": {"value": {}},
                "required": ["value"],
            },
        )

        async def execute(arguments: dict[str, Any]) -> Any:
            return arguments["value"]

        tool = PluginTool(schema, execute)
        result = await tool.execute({"value": "hello"})
        assert result == "hello"
