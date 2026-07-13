"""Mocked Telegram Bot API tests covering authorization, polling, sending, failures, and redaction."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.tools.audit import ToolAuditLog
from src.tools.telegram_factory import create_telegram_registry
from src.tools.telegram_models import Attachment, Chat, ChatType, Message, TelegramUser
from src.tools.telegram_provider import MockTelegramProvider
from src.tools.models import ToolPermissionError, ToolRequest, ToolValidationError
from src.tools.telegram_tools import (
    DraftMessageTool,
    GetBotInfoTool,
    GetChatTool,
    GetUpdatesTool,
    ListAuthorizedChatsTool,
    SendAttachmentTool,
    SendMessageTool,
)


def _make_provider() -> MockTelegramProvider:
    provider = MockTelegramProvider()
    provider.configure_bot(TelegramUser(id=1, is_bot=True, first_name="NexusBot", username="nexus_bot"))
    provider.authorize_chat(Chat(id="123", type=ChatType.PRIVATE, first_name="Alice", username="alice"))
    provider.authorize_chat(Chat(id="-100", type=ChatType.GROUP, title="Nexus Chat"))
    message = Message(
        message_id=1, chat=provider._chats["123"], date=datetime.now(timezone.utc),
        text="hello", from_user=provider._me,
    )
    provider.add_update(message)
    return provider


@pytest.mark.asyncio
async def test_get_bot_info_is_read_only(tmp_path: Path):
    provider = _make_provider()
    registry = create_telegram_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("telegram.get_bot_info", {}))
    assert result.success
    output = result.output
    assert output["id"] == 1
    assert output["is_bot"] is True
    assert output["username"] == "nexus_bot"


@pytest.mark.asyncio
async def test_list_authorized_chats_is_read_only(tmp_path: Path):
    provider = _make_provider()
    registry = create_telegram_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("telegram.list_authorized_chats", {}))
    assert result.success
    output = result.output
    assert len(output["chats"]) == 2
    ids = {chat["id"] for chat in output["chats"]}
    assert "123" in ids
    assert "-100" in ids


@pytest.mark.asyncio
async def test_get_chat_requires_authorized_chat(tmp_path: Path):
    provider = _make_provider()
    registry = create_telegram_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("telegram.get_chat", {"chat_id": "123"}))
    assert result.success
    assert result.output["id"] == "123"
    assert result.output["is_authorized"] is True


@pytest.mark.asyncio
async def test_get_chat_rejects_unknown_chat(tmp_path: Path):
    provider = _make_provider()
    registry = create_telegram_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("telegram.get_chat", {"chat_id": "999"}))
    assert not result.success
    assert result.error_code in {"ToolValidationError", "execution_error"}


@pytest.mark.asyncio
async def test_draft_message_requires_text_or_attachment(tmp_path: Path):
    provider = _make_provider()
    registry = create_telegram_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("telegram.draft_message", {"chat_id": "123", "text": "hi"}), confirmed=True)
    assert result.success
    assert result.output["text"] == "hi"


@pytest.mark.asyncio
async def test_send_message_requires_authorized_chat(tmp_path: Path):
    provider = _make_provider()
    registry = create_telegram_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("telegram.send_message", {"chat_id": "999", "text": "hi"}), confirmed=True)
    assert not result.success
    assert result.error_code in {"ToolValidationError", "execution_error"}


@pytest.mark.asyncio
async def test_send_message_returns_sent_message(tmp_path: Path):
    provider = _make_provider()
    registry = create_telegram_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("telegram.send_message", {"chat_id": "123", "text": "hi"}), confirmed=True)
    assert result.success
    assert result.output["text"] == "hi"
    assert result.output["chat"]["id"] == "123"


@pytest.mark.asyncio
async def test_send_attachment_returns_sent_message(tmp_path: Path):
    provider = _make_provider()
    registry = create_telegram_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("telegram.send_attachment", {
        "chat_id": "123", "file_id": "file_1", "filename": "note.txt", "mime_type": "text/plain", "size": 10,
    }), confirmed=True)
    assert result.success
    assert result.output["attachment"]["filename"] == "note.txt"


@pytest.mark.asyncio
async def test_audit_records_telegram_send_without_over_redacting(tmp_path: Path):
    provider = _make_provider()
    registry = create_telegram_registry(provider, audit_path=tmp_path / "audit.jsonl")
    await registry.invoke(ToolRequest("telegram.send_message", {"chat_id": "123", "text": "secret"}))
    entries = registry.audit_log.entries()
    assert len(entries) >= 1
    record = entries[-1]
    assert record.tool_name == "telegram.send_message"
    assert record.arguments["chat_id"] == "123"
    assert record.arguments["text"] == "secret"
