"""Factory helpers for plugin-augmented Nexus tool registries."""

from __future__ import annotations

from pathlib import Path

from .audit import ToolAuditLog
from .plugin_discovery import PluginManager, PluginManifest
from .registry import ToolRegistry


def create_plugin_registry(
    plugins_dir: Path | str,
    *,
    audit_path: Path | str = Path("~/.nexus/logs/tool-audit.jsonl"),
    policy=None,
    default_timeout: float = 30.0,
) -> tuple[ToolRegistry, PluginManager]:
    """Create a registry augmented with plugin-discovered tools."""
    audit_log = ToolAuditLog(audit_path)
    registry = ToolRegistry(policy=policy, audit_log=audit_log, default_timeout=default_timeout)
    manager = PluginManager(plugins_dir, registry=registry, audit_log=audit_log)
    return registry, manager


async def create_and_load_plugin_registry(
    plugins_dir: Path | str,
    *,
    audit_path: Path | str = Path("~/.nexus/logs/tool-audit.jsonl"),
    policy=None,
    default_timeout: float = 30.0,
) -> tuple[ToolRegistry, PluginManager, list[PluginManifest]]:
    """Create registry, discover, and load all enabled plugins."""
    registry, manager = create_plugin_registry(
        plugins_dir,
        audit_path=audit_path,
        policy=policy,
        default_timeout=default_timeout,
    )
    loaded = await manager.load_all_enabled()
    return registry, manager, [lp.manifest for lp in loaded]
