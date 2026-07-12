"""Mock Gmail provider for testing and offline development."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from .gmail_models import AttachmentMetadata, GmailDraft, GmailMessage, GmailThread, GmailProvider


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MockGmailProvider:
    """In-memory Gmail API simulator with pagination and duplicate-send protection."""

    def __init__(self) -> None:
        self._messages: dict[str, GmailMessage] = {}
        self._threads: dict[str, GmailThread] = {}
        self._drafts: dict[str, GmailDraft] = {}
        self._sent_draft_ids: set[str] = set()
        self._counter = 0

    def _next_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}"

    def _make_message(self, subject: str, body: str, from_address: str, to_addresses: tuple[str, ...], thread_id: str | None = None, labels: tuple[str, ...] = ("INBOX",), cc_addresses: tuple[str, ...] = ()) -> GmailMessage:
        message_id = self._next_id("msg")
        thread_id = thread_id or message_id
        return GmailMessage(
            id=message_id, thread_id=thread_id, subject=subject,
            from_address=from_address, to_addresses=to_addresses, cc_addresses=cc_addresses,
            snippet=body[:120], body=body, labels=labels, date=_now(),
            has_attachment=False, attachment_metadata=(),
        )

    def add_message(self, message: GmailMessage) -> GmailMessage:
        self._messages[message.id] = message
        if message.thread_id not in self._threads:
            self._threads[message.thread_id] = GmailThread(
                id=message.thread_id, messages=(message,), labels=message.labels, snippet=message.snippet,
            )
        else:
            thread = self._threads[message.thread_id]
            self._threads[message.thread_id] = GmailThread(
                id=thread.id, messages=thread.messages + (message,), labels=thread.labels, snippet=thread.snippet,
            )
        return message

    def _sync_thread_message(self, message: GmailMessage) -> None:
        thread = self._threads.get(message.thread_id)
        if thread is None:
            return
        new_messages = tuple(msg if msg.id != message.id else message for msg in thread.messages)
        if any(msg.id == message.id for msg in thread.messages):
            self._threads[message.thread_id] = GmailThread(
                id=thread.id, messages=new_messages, labels=thread.labels, snippet=thread.snippet,
            )

    async def label(self, message_id: str, *, add: tuple[str, ...] = (), remove: tuple[str, ...] = ()) -> GmailMessage:
        message = await self.read_message(message_id)
        labels = tuple(label for label in message.labels if label not in remove)
        labels = labels + tuple(label for label in add if label not in labels)
        new_message = GmailMessage(
            id=message.id, thread_id=message.thread_id, subject=message.subject,
            from_address=message.from_address, to_addresses=message.to_addresses,
            cc_addresses=message.cc_addresses, snippet=message.snippet, body=message.body,
            labels=labels, date=message.date, has_attachment=message.has_attachment,
            attachment_metadata=message.attachment_metadata,
        )
        self._messages[message.id] = new_message
        self._sync_thread_message(new_message)
        return new_message

    async def archive(self, message_id: str) -> GmailMessage:
        return await self.label(message_id, remove=("INBOX",))

    async def delete(self, message_id: str) -> None:
        self._messages.pop(message_id, None)
        for thread in self._threads.values():
            if any(msg.id == message_id for msg in thread.messages):
                new_messages = tuple(msg for msg in thread.messages if msg.id != message_id)
                self._threads[thread.id] = GmailThread(
                    id=thread.id, messages=new_messages, labels=thread.labels, snippet=thread.snippet,
                )

    async def search_messages(self, query: str, *, limit: int, page_token: str | None = None) -> tuple[list[GmailMessage], str | None]:
        del query, page_token
        results = list(self._messages.values())[:max(limit, 1)]
        next_token = str(len(results)) if len(results) >= limit else None
        return results, next_token

    async def read_message(self, message_id: str) -> GmailMessage:
        try:
            return self._messages[message_id]
        except KeyError as exc:
            raise ValueError(f"message not found: {message_id}") from exc

    async def thread_summary(self, thread_id: str) -> GmailThread:
        try:
            return self._threads[thread_id]
        except KeyError as exc:
            raise ValueError(f"thread not found: {thread_id}") from exc

    async def attachment_metadata(self, message_id: str) -> tuple[AttachmentMetadata, ...]:
        message = await self.read_message(message_id)
        return message.attachment_metadata

    async def create_draft(self, *, to: tuple[str, ...], subject: str, body: str, thread_id: str | None = None, cc: tuple[str, ...] = ()) -> GmailDraft:
        message = self._make_message(subject, body, "me@example.test", to, thread_id=thread_id, labels=("DRAFT",), cc_addresses=cc)
        draft_id = self._next_id("draft")
        draft = GmailDraft(id=draft_id, message=message, created_at=_now())
        self._drafts[draft_id] = draft
        return draft

    async def update_draft(self, draft_id: str, *, to: tuple[str, ...] | None = None, subject: str | None = None, body: str | None = None, thread_id: str | None = None, cc: tuple[str, ...] | None = None) -> GmailDraft:
        try:
            draft = self._drafts[draft_id]
        except KeyError as exc:
            raise ValueError(f"draft not found: {draft_id}") from exc
        message = draft.message
        new_message = GmailMessage(
            id=message.id, thread_id=thread_id or message.thread_id,
            subject=subject or message.subject, from_address=message.from_address,
            to_addresses=to or message.to_addresses, cc_addresses=cc or message.cc_addresses,
            snippet=message.snippet, body=body or message.body, labels=message.labels, date=message.date,
            has_attachment=message.has_attachment, attachment_metadata=message.attachment_metadata,
        )
        new_draft = GmailDraft(id=draft.id, message=new_message, created_at=draft.created_at)
        self._drafts[draft_id] = new_draft
        return new_draft

    async def send_draft(self, draft_id: str) -> GmailMessage:
        if draft_id in self._sent_draft_ids:
            raise ValueError(f"draft already sent: {draft_id}")
        try:
            draft = self._drafts.pop(draft_id)
        except KeyError as exc:
            raise ValueError(f"draft not found: {draft_id}") from exc
        self._sent_draft_ids.add(draft_id)
        message = draft.message
        sent_message = GmailMessage(
            id=message.id, thread_id=message.thread_id, subject=message.subject,
            from_address=message.from_address, to_addresses=message.to_addresses,
            cc_addresses=message.cc_addresses, snippet=message.snippet, body=message.body,
            labels=("SENT",), date=_now(), has_attachment=message.has_attachment,
            attachment_metadata=message.attachment_metadata,
        )
        self._messages[message.id] = sent_message
        if message.thread_id not in self._threads:
            self._threads[message.thread_id] = GmailThread(
                id=message.thread_id, messages=(sent_message,), labels=("SENT",), snippet=sent_message.snippet,
            )
        else:
            thread = self._threads[message.thread_id]
            self._threads[message.thread_id] = GmailThread(
                id=thread.id, messages=thread.messages + (sent_message,), labels=thread.labels, snippet=thread.snippet,
            )
        return sent_message

    async def reply(self, message_id: str, *, body: str) -> GmailMessage:
        original = await self.read_message(message_id)
        reply_message = self._make_message(
            f"Re: {original.subject}", body, "me@example.test", (original.from_address,),
            thread_id=original.thread_id, labels=("SENT",),
        )
        self.add_message(reply_message)
        return reply_message
