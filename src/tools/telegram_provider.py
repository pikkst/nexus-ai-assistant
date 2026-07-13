"""Mock Telegram Bot API provider for testing and offline development."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from .telegram_models import (
    Attachment,
    Chat,
    ChatType,
    Message,
    MessageDraft,
    TelegramUser,
    Update,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MockTelegramProvider:
    """In-memory Telegram Bot API simulator with authorization, polling, and send support."""

    def __init__(self) -> None:
        self._me: TelegramUser | None = None
        self._chats: dict[str, Chat] = {}
        self._messages: dict[str, dict[str, Message]] = {}
        self._updates: list[Update] = []
        self._update_offset = 0
        self._counter = 0
        self._authorized_chat_ids: set[str] = set()

    def _next_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{uuid.uuid4().hex[:8]}_{self._counter}"

    def configure_bot(self, user: TelegramUser) -> None:
        self._me = user

    def authorize_chat(self, chat: Chat) -> Chat:
        chat_id = chat.id
        if chat_id not in self._chats:
            object.__setattr__(chat, "is_authorized", True)
            self._chats[chat_id] = chat
        else:
            existing = self._chats[chat_id]
            object.__setattr__(existing, "is_authorized", True)
        self._authorized_chat_ids.add(chat_id)
        return self._chats[chat_id]

    def add_update(self, message: Message) -> Update:
        update_id = self._update_offset
        self._update_offset += 1
        update = Update(update_id=update_id, message=message)
        self._updates.append(update)
        return update

    async def get_me(self) -> TelegramUser:
        if self._me is None:
            self._me = TelegramUser(id=1, is_bot=True, first_name="NexusBot", username="nexus_bot")
        return self._me

    async def list_authorized_chats(self) -> tuple[list[Chat], str | None]:
        return [chat for chat in self._chats.values() if chat.is_authorized], None

    async def get_chat(self, chat_id: str) -> Chat:
        chat = self._chats.get(chat_id)
        if chat is None:
            raise ValueError(f"chat {chat_id} not found")
        if not chat.is_authorized:
            raise ValueError(f"chat {chat_id} is not authorized")
        return chat

    async def get_updates(self, *, offset: int | None = None, limit: int = 100) -> tuple[list[Update], int | None]:
        if offset is not None:
            pending = [update for update in self._updates if update.update_id >= offset]
        else:
            pending = list(self._updates)
        pending = pending[: max(1, min(limit, 100))]
        next_offset = (pending[-1].update_id + 1) if pending else offset
        return pending, next_offset

    async def send_message(self, chat_id: str, text: str, *, reply_to_message_id: int | None = None) -> Message:
        chat = await self.get_chat(chat_id)
        message_id = self._next_id("msg")
        from_user = await self.get_me()
        message = Message(
            message_id=int(message_id.split("_")[-1]), chat=chat, date=_now(),
            text=text, from_user=from_user, reply_to_message_id=reply_to_message_id,
        )
        self._messages.setdefault(chat_id, {})[message_id] = message
        return message

    async def send_attachment(self, chat_id: str, attachment: Attachment, *, caption: str = "", reply_to_message_id: int | None = None) -> Message:
        chat = await self.get_chat(chat_id)
        message_id = self._next_id("msg")
        from_user = await self.get_me()
        message = Message(
            message_id=int(message_id.split("_")[-1]), chat=chat, date=_now(),
            caption=caption, from_user=from_user, attachment=attachment,
            reply_to_message_id=reply_to_message_id,
        )
        self._messages.setdefault(chat_id, {})[message_id] = message
        return message
