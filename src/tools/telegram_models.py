"""Telegram-specific typed models and provider protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Protocol, Any


_VALID_USERNAME = r"^[a-zA-Z0-9_]{5,32}$"
_VALID_CHAT_ID = r"^-?\d+$"


def _validate_username(value: str, field_name: str) -> None:
    import re
    if not re.match(_VALID_USERNAME, value):
        raise ValueError(f"{field_name} must be a valid Telegram username (5-32 chars, alphanumeric and underscores)")


def _validate_chat_id(value: str, field_name: str) -> None:
    import re
    if not re.match(_VALID_CHAT_ID, value):
        raise ValueError(f"{field_name} must be a valid Telegram chat id (integer string)")


class ChatType(Enum):
    PRIVATE = "private"
    GROUP = "group"
    SUPERGROUP = "supergroup"
    CHANNEL = "channel"


class MessageEntityType(Enum):
    MENTION = "mention"
    HASHTAG = "hashtag"
    CASHTAG = "cashtag"
    BOT_COMMAND = "bot_command"
    URL = "url"
    EMAIL = "email"
    PHONE = "phone"
    BOLD = "bold"
    ITALIC = "italic"
    CODE = "code"
    PRE = "pre"
    TEXT_LINK = "text_link"
    TEXT_MENTION = "text_mention"


@dataclass(frozen=True, slots=True)
class TelegramUser:
    id: int
    is_bot: bool
    first_name: str
    last_name: str = ""
    username: str = ""
    language_code: str = ""

    def __post_init__(self) -> None:
        if self.id <= 0:
            raise ValueError("user id must be a positive integer")
        if not self.is_bot:
            raise ValueError("this module models bot identity; use a bot user")
        if not self.first_name:
            raise ValueError("first_name is required")
        if self.username:
            _validate_username(self.username, "username")


@dataclass(frozen=True, slots=True)
class Chat:
    id: str
    type: ChatType
    title: str = ""
    username: str = ""
    first_name: str = ""
    last_name: str = ""
    is_authorized: bool = True

    def __post_init__(self) -> None:
        _validate_chat_id(self.id, "chat id")
        if not self.type:
            raise ValueError("chat type is required")
        if self.type in (ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL) and not self.title:
            raise ValueError("title is required for group, supergroup, and channel chats")
        if self.type == ChatType.PRIVATE and not self.first_name:
            raise ValueError("first_name is required for private chats")
        if self.username:
            _validate_username(self.username, "chat username")


@dataclass(frozen=True, slots=True)
class MessageEntity:
    type: MessageEntityType
    offset: int
    length: int
    url: str = ""
    user: TelegramUser | None = None


@dataclass(frozen=True, slots=True)
class Attachment:
    file_id: str
    filename: str
    mime_type: str
    size: int

    def __post_init__(self) -> None:
        if not self.file_id:
            raise ValueError("attachment file_id is required")
        if not self.filename:
            raise ValueError("attachment filename is required")
        if not self.mime_type:
            raise ValueError("attachment mime_type is required")
        if self.size < 0:
            raise ValueError("attachment size must be non-negative")


@dataclass(frozen=True, slots=True)
class Message:
    message_id: int
    chat: Chat
    date: datetime
    text: str = ""
    caption: str = ""
    from_user: TelegramUser | None = None
    entities: tuple[MessageEntity, ...] = ()
    attachment: Attachment | None = None
    reply_to_message_id: int | None = None

    def __post_init__(self) -> None:
        if self.message_id <= 0:
            raise ValueError("message_id must be a positive integer")
        if self.date.tzinfo is None:
            raise ValueError("message date must be timezone-aware")
        if not self.text and not self.caption and self.attachment is None:
            raise ValueError("message must have text, caption, or attachment")


@dataclass(frozen=True, slots=True)
class Update:
    update_id: int
    message: Message | None = None
    edited_message: Message | None = None
    channel_post: Message | None = None
    edited_channel_post: Message | None = None

    def __post_init__(self) -> None:
        if self.update_id < 0:
            raise ValueError("update_id must be non-negative")


@dataclass(frozen=True, slots=True)
class MessageDraft:
    chat_id: str
    text: str = ""
    caption: str = ""
    attachment: Attachment | None = None
    reply_to_message_id: int | None = None

    def __post_init__(self) -> None:
        _validate_chat_id(self.chat_id, "chat_id")
        if not self.text and not self.caption and self.attachment is None:
            raise ValueError("draft must have text, caption, or attachment")


class TelegramProvider(Protocol):
    async def get_me(self) -> TelegramUser: ...
    async def list_authorized_chats(self) -> tuple[list[Chat], str | None]: ...
    async def get_chat(self, chat_id: str) -> Chat: ...
    async def get_updates(self, *, offset: int | None = None, limit: int = 100) -> tuple[list[Update], int | None]: ...
    async def send_message(self, chat_id: str, text: str, *, reply_to_message_id: int | None = None) -> Message: ...
    async def send_attachment(self, chat_id: str, attachment: Attachment, *, caption: str = "", reply_to_message_id: int | None = None) -> Message: ...
