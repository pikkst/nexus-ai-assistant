"""Construction helper for Telegram tool registries."""

from __future__ import annotations

from pathlib import Path

from .audit import ToolAuditLog
from .telegram_tools import (
    DraftMessageTool,
    GetBotInfoTool,
    GetChatTool,
    GetUpdatesTool,
    SendAttachmentTool,
    SendMessageTool,
    ListAuthorizedChatsTool,
)
from .telegram_models import TelegramProvider
from .telegram_provider import MockTelegramProvider
from .permissions import PermissionPolicy
from .registry import ToolRegistry


def create_telegram_registry(
    provider: TelegramProvider, *, audit_path: Path | str = Path("~/.nexus/logs/telegram-audit.jsonl"),
    policy: PermissionPolicy | None = None, default_timeout: float = 30.0,
) -> ToolRegistry:
    """Create a registry with Telegram tools wired to the supplied provider."""
    audit_log = ToolAuditLog(audit_path)
    tools = [
        GetBotInfoTool(provider),
        ListAuthorizedChatsTool(provider),
        GetChatTool(provider),
        GetUpdatesTool(provider),
        DraftMessageTool(provider),
        SendMessageTool(provider),
        SendAttachmentTool(provider),
    ]
    return ToolRegistry(tools, policy=policy, audit_log=audit_log, default_timeout=default_timeout)
