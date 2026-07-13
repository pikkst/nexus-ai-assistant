"""Permissioned Telegram tools for chat listing, update polling, drafting, and sending."""

from __future__ import annotations

from typing import Any

from .audit import ToolAuditLog, redact
from .telegram_models import (
    Attachment,
    Chat,
    ChatType,
    Message,
    MessageDraft,
    MessageEntity,
    MessageEntityType,
    TelegramProvider,
    TelegramUser,
    Update,
    _validate_chat_id,
)
from .models import RiskLevel, Tool, ToolDescriptor, ToolValidationError
from .permissions import PermissionPolicy
from .registry import ToolRegistry


def _validate_limit(value: Any, field_name: str, *, minimum: int = 1, maximum: int = 100) -> int:
    if not isinstance(value, int) or not minimum <= value <= maximum:
        raise ToolValidationError(f"{field_name} must be an integer between {minimum} and {maximum}")
    return value


def _validate_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ToolValidationError(f"{field_name} must be a non-empty string")
    return value.strip()


def _chat_to_dict(chat: Chat) -> dict[str, Any]:
    return {
        "id": chat.id, "type": chat.type.value, "title": chat.title,
        "username": chat.username, "first_name": chat.first_name,
        "last_name": chat.last_name, "is_authorized": chat.is_authorized,
    }


def _message_to_dict(message: Message) -> dict[str, Any]:
    return {
        "message_id": message.message_id, "chat": _chat_to_dict(message.chat),
        "date": message.date.isoformat(), "text": message.text,
        "caption": message.caption, "from_user": _user_to_dict(message.from_user) if message.from_user else None,
        "reply_to_message_id": message.reply_to_message_id,
        "attachment": _attachment_to_dict(message.attachment) if message.attachment else None,
    }


def _user_to_dict(user: TelegramUser) -> dict[str, Any]:
    return {
        "id": user.id, "is_bot": user.is_bot, "first_name": user.first_name,
        "last_name": user.last_name, "username": user.username, "language_code": user.language_code,
    }


def _attachment_to_dict(attachment: Attachment) -> dict[str, Any]:
    return {
        "file_id": attachment.file_id, "filename": attachment.filename,
        "mime_type": attachment.mime_type, "size": attachment.size,
    }


def _update_to_dict(update: Update) -> dict[str, Any]:
    return {
        "update_id": update.update_id,
        "message": _message_to_dict(update.message) if update.message else None,
        "edited_message": _message_to_dict(update.edited_message) if update.edited_message else None,
    }


class GetBotInfoTool:
    name, description, risk = "telegram.get_bot_info", "Get the current Telegram bot identity.", RiskLevel.READ_ONLY
    parameters = {"type": "object", "properties": {}, "additionalProperties": False}

    def __init__(self, provider: TelegramProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        if arguments:
            raise ToolValidationError("no arguments are accepted")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        user = await self.provider.get_me()
        return _user_to_dict(user)


class ListAuthorizedChatsTool:
    name, description, risk = "telegram.list_authorized_chats", "List authorized Telegram chats.", RiskLevel.READ_ONLY
    parameters = {"type": "object", "properties": {}, "additionalProperties": False}

    def __init__(self, provider: TelegramProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        if arguments:
            raise ToolValidationError("no arguments are accepted")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        chats, _ = await self.provider.list_authorized_chats()
        return {"chats": [_chat_to_dict(chat) for chat in chats]}


class GetChatTool:
    name, description, risk = "telegram.get_chat", "Get a single authorized Telegram chat by id.", RiskLevel.READ_ONLY
    parameters = {"type": "object", "properties": {"chat_id": {"type": "string"}}, "required": ["chat_id"], "additionalProperties": False}

    def __init__(self, provider: TelegramProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_chat_id(arguments.get("chat_id"), "chat_id")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        chat = await self.provider.get_chat(arguments["chat_id"])
        return _chat_to_dict(chat)


class GetUpdatesTool:
    name, description, risk = "telegram.get_updates", "Get pending Telegram bot updates.", RiskLevel.READ_ONLY
    parameters = {"type": "object", "properties": {"offset": {"type": "integer"}, "limit": {"type": "integer", "minimum": 1, "maximum": 100}}, "required": [], "additionalProperties": False}

    def __init__(self, provider: TelegramProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        limit = arguments.get("limit", 100)
        _validate_limit(limit, "limit")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        updates, next_offset = await self.provider.get_updates(
            offset=arguments.get("offset"), limit=arguments.get("limit", 100),
        )
        return {"updates": [_update_to_dict(update) for update in updates], "next_offset": next_offset}


class DraftMessageTool:
    name, description, risk = "telegram.draft_message", "Create a Telegram message draft without sending.", RiskLevel.LOCAL_WRITE
    parameters = {"type": "object", "properties": {"chat_id": {"type": "string"}, "text": {"type": "string"}, "caption": {"type": "string"}, "reply_to_message_id": {"type": "integer"}}, "required": ["chat_id"], "additionalProperties": False}

    def __init__(self, provider: TelegramProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_chat_id(arguments.get("chat_id"), "chat_id")
        text = arguments.get("text")
        caption = arguments.get("caption")
        attachment = arguments.get("attachment")
        if not text and not caption and not attachment:
            raise ToolValidationError("draft must have text, caption, or attachment")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        draft = MessageDraft(
            chat_id=arguments["chat_id"], text=arguments.get("text", ""),
            caption=arguments.get("caption", ""), reply_to_message_id=arguments.get("reply_to_message_id"),
        )
        return {
            "chat_id": draft.chat_id, "text": draft.text, "caption": draft.caption,
            "reply_to_message_id": draft.reply_to_message_id,
        }


class SendMessageTool:
    name, description, risk = "telegram.send_message", "Send a Telegram text message to an authorized chat.", RiskLevel.EXTERNAL
    parameters = {"type": "object", "properties": {"chat_id": {"type": "string"}, "text": {"type": "string"}, "reply_to_message_id": {"type": "integer"}}, "required": ["chat_id", "text"], "additionalProperties": False}

    def __init__(self, provider: TelegramProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_chat_id(arguments.get("chat_id"), "chat_id")
        _validate_text(arguments.get("text"), "text")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        message = await self.provider.send_message(
            arguments["chat_id"], arguments["text"], reply_to_message_id=arguments.get("reply_to_message_id"),
        )
        return _message_to_dict(message)


class SendAttachmentTool:
    name, description, risk = "telegram.send_attachment", "Send an attachment to an authorized Telegram chat.", RiskLevel.EXTERNAL
    parameters = {"type": "object", "properties": {"chat_id": {"type": "string"}, "file_id": {"type": "string"}, "filename": {"type": "string"}, "mime_type": {"type": "string"}, "size": {"type": "integer", "minimum": 0}, "caption": {"type": "string"}, "reply_to_message_id": {"type": "integer"}}, "required": ["chat_id", "file_id", "filename", "mime_type"], "additionalProperties": False}

    def __init__(self, provider: TelegramProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_chat_id(arguments.get("chat_id"), "chat_id")
        if not isinstance(arguments.get("file_id"), str) or not arguments["file_id"].strip():
            raise ToolValidationError("file_id must be a non-empty string")
        if not isinstance(arguments.get("filename"), str) or not arguments["filename"].strip():
            raise ToolValidationError("filename must be a non-empty string")
        if not isinstance(arguments.get("mime_type"), str) or not arguments["mime_type"].strip():
            raise ToolValidationError("mime_type must be a non-empty string")
        size = arguments.get("size", 0)
        if not isinstance(size, int) or size < 0:
            raise ToolValidationError("size must be a non-negative integer")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        attachment = Attachment(
            file_id=arguments["file_id"], filename=arguments["filename"],
            mime_type=arguments["mime_type"], size=arguments.get("size", 0),
        )
        message = await self.provider.send_attachment(
            arguments["chat_id"], attachment, caption=arguments.get("caption", ""),
            reply_to_message_id=arguments.get("reply_to_message_id"),
        )
        return _message_to_dict(message)
