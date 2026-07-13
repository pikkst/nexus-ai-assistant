"""Discovery, loading, enable/disable, and uninstall of Nexus plugins."""

from __future__ import annotations

import importlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .audit import ToolAuditLog
from .mcp_client import McpClient, McpError, McpTimeoutError
from .models import RiskLevel, Tool, ToolValidationError
from .plugin_adapter import McpTool, PluginTool
from .plugin_models import McpServerConfig, PluginManifest, PluginToolSchema
from .registry import ToolRegistry

logger = logging.getLogger(__name__)


class PluginLoadError(RuntimeError):
    """Raised when a plugin cannot be loaded."""


class PluginVersionConflictError(PluginLoadError):
    """Raised when a plugin version conflicts with an already-loaded plugin."""


class PluginDuplicateNameError(PluginLoadError):
    """Raised when a plugin declares a tool name that is already registered."""


class PluginSchemaError(PluginLoadError):
    """Raised when a plugin manifest or tool schema is malformed."""


@dataclass(slots=True)
class LoadedPlugin:
    manifest: PluginManifest
    tools: tuple[Tool, ...]
    tool_names: frozenset[str] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "tool_names", frozenset(tool.name for tool in self.tools))


class PluginManager:
    """Discover, load, enable, disable, and unload Nexus plugins."""

    def __init__(
        self,
        plugins_dir: Path | str,
        registry: ToolRegistry,
        audit_log: ToolAuditLog | None = None,
    ) -> None:
        self.plugins_dir = Path(plugins_dir).expanduser().resolve()
        self.registry = registry
        self.audit_log = audit_log
        self._loaded: dict[str, LoadedPlugin] = {}

    def discover(self) -> tuple[PluginManifest, ...]:
        """Return all manifests found in the plugins directory."""
        if not self.plugins_dir.exists() or not self.plugins_dir.is_dir():
            return ()
        manifests = []
        for path in sorted(self.plugins_dir.iterdir()):
            manifest_path = path / "manifest.json"
            if not manifest_path.is_file():
                continue
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest = PluginManifest(
                    name=data["name"],
                    version=data["version"],
                    description=data.get("description", ""),
                    enabled=data.get("enabled", True),
                    entry_point=data.get("entry_point"),
                    tools=tuple(
                        PluginToolSchema(
                            name=t["name"],
                            description=t.get("description", ""),
                            risk=RiskLevel(t.get("risk", "read_only")),
                            parameters=t.get("parameters", {}),
                        )
                        for t in data.get("tools", [])
                    ),
                    mcp_server=(
                        McpServerConfig(
                            url=s["url"],
                            transport=s.get("transport", "streamable_http"),
                            timeout=s.get("timeout", 30.0),
                            headers=s.get("headers", {}),
                        )
                        if (s := data.get("mcp_server"))
                        else None
                    ),
                )
                manifests.append(manifest)
            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                logger.warning("Skipping malformed manifest at %s: %s", manifest_path, exc)
        return tuple(manifests)

    async def load(self, manifest: PluginManifest) -> LoadedPlugin:
        """Load an enabled plugin and register its tools."""
        if manifest.name in self._loaded:
            existing = self._loaded[manifest.name]
            if existing.manifest.version != manifest.version:
                raise PluginVersionConflictError(
                    f"Plugin {manifest.name} is already loaded in version {existing.manifest.version}, "
                    f"cannot load {manifest.version}"
                )
            return existing
        if not manifest.enabled:
            raise PluginLoadError(f"Plugin {manifest.name} is disabled")
        tools = await self._build_tools(manifest)
        self._check_collisions(manifest, tools)
        for tool in tools:
            self.registry.register(tool)
        loaded = LoadedPlugin(manifest=manifest, tools=tuple(tools))
        self._loaded[manifest.name] = loaded
        return loaded

    def unload(self, name: str) -> None:
        """Remove all tools registered by the named plugin."""
        loaded = self._loaded.pop(name, None)
        if loaded is None:
            return
        for tool_name in loaded.tool_names:
            try:
                del self.registry._tools[tool_name]
            except KeyError:
                pass

    async def enable(self, name: str) -> LoadedPlugin | None:
        """Enable and load a previously disabled plugin."""
        manifest = self._find_manifest(name)
        if manifest is None:
            raise PluginLoadError(f"Plugin manifest not found: {name}")
        manifest = PluginManifest(
            name=manifest.name,
            version=manifest.version,
            description=manifest.description,
            enabled=True,
            entry_point=manifest.entry_point,
            tools=manifest.tools,
            mcp_server=manifest.mcp_server,
        )
        return await self.load(manifest)

    def disable(self, name: str) -> None:
        """Unload a plugin without removing its manifest."""
        self.unload(name)

    async def load_all_enabled(self) -> tuple[LoadedPlugin, ...]:
        """Discover and load every enabled plugin."""
        loaded = []
        for manifest in self.discover():
            if not manifest.enabled:
                continue
            try:
                loaded.append(await self.load(manifest))
            except PluginLoadError as exc:
                logger.warning("Failed to load plugin %s: %s", manifest.name, exc)
        return tuple(loaded)

    async def _build_tools(self, manifest: PluginManifest) -> list[Tool]:
        tools = []
        if manifest.mcp_server is not None:
            tools.extend(await self._build_mcp_tools(manifest))
        elif manifest.entry_point is not None:
            tools.extend(self._build_local_tools(manifest))
        else:
            raise PluginSchemaError(
                f"Plugin {manifest.name} has no entry_point or mcp_server"
            )
        return tools

    def _build_local_tools(self, manifest: PluginManifest) -> list[Tool]:
        module_path = manifest.entry_point
        try:
            module = importlib.import_module(module_path)
        except ImportError as exc:
            raise PluginLoadError(
                f"Cannot import plugin entry point {module_path}: {exc}"
            ) from exc
        create_fn = getattr(module, "create_tools", None)
        if create_fn is None:
            raise PluginLoadError(
                f"Plugin entry point {module_path} does not expose create_tools()"
            )
        try:
            raw_tools = create_fn()
        except Exception as exc:
            raise PluginLoadError(
                f"Plugin {manifest.name} create_tools() failed: {exc}"
            ) from exc
        if not isinstance(raw_tools, list):
            raise PluginLoadError(
                f"Plugin {manifest.name} create_tools() must return a list of Tool objects"
            )
        tools = []
        for raw in raw_tools:
            if hasattr(raw, "name") and hasattr(raw, "execute") and hasattr(raw, "validate"):
                tools.append(raw)
            else:
                raise PluginLoadError(
                    f"Plugin {manifest.name} returned unsupported tool type: {type(raw).__name__}"
                )
        return tools

    async def _build_mcp_tools(self, manifest: PluginManifest) -> list[Tool]:
        if manifest.mcp_server is None:
            return []
        config = manifest.mcp_server

        def make_client() -> McpClient:
            return McpClient(config)

        try:
            async with McpClient(config) as client:
                await client.initialize()
                mcp_tools = await client.list_tools()
        except (McpError, McpTimeoutError, Exception) as exc:
            raise PluginLoadError(
                f"MCP server for plugin {manifest.name} is unavailable: {exc}"
            ) from exc

        tools = []
        for mcp_tool in mcp_tools:
            try:
                tool = McpTool(
                    descriptor=mcp_tool,
                    risk=RiskLevel.EXTERNAL,
                    client_factory=make_client,
                )
                tools.append(tool)
            except (ToolValidationError, ValueError) as exc:
                logger.warning(
                    "Skipping malformed MCP tool %s from %s: %s",
                    mcp_tool.get("name", "?"),
                    manifest.name,
                    exc,
                )
        return tools

    def _check_collisions(self, manifest: PluginManifest, tools: list[Tool]) -> None:
        existing = set(self.registry._tools.keys())
        for tool in tools:
            if tool.name in existing:
                raise PluginDuplicateNameError(
                    f"Tool {tool.name} from plugin {manifest.name} conflicts with an existing tool"
                )
        for other_name, other in self._loaded.items():
            if other_name == manifest.name:
                continue
            for tool in tools:
                if tool.name in other.tool_names:
                    raise PluginDuplicateNameError(
                        f"Tool {tool.name} from plugin {manifest.name} conflicts with plugin {other_name}"
                    )

    def _find_manifest(self, name: str) -> PluginManifest | None:
        for manifest in self.discover():
            if manifest.name == name:
                return manifest
        return None

    @property
    def loaded_plugins(self) -> dict[str, LoadedPlugin]:
        return dict(self._loaded)
