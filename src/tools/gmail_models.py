"""Gmail-specific typed models and provider protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol, Any


_VALID_EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


def _validate_email(value: str, field_name: str) -> None:
    import re
    if not re.match(_VALID_EMAIL, value):
        raise ValueError(f"{field_name} must be a valid email address")


def _validate_emails(values: tuple[str, ...], field_name: str) -> None:
    for item in values:
        _validate_email(item, field_name)


@dataclass(frozen=True, slots=True)
class AttachmentMetadata:
    filename: str
    mime_type: str
    size: int


@dataclass(frozen=True, slots=True)
class GmailMessage:
    id: str
    thread_id: str
    subject: str
    from_address: str
    to_addresses: tuple[str, ...]
    cc_addresses: tuple[str, ...]
    snippet: str
    body: str
    labels: tuple[str, ...]
    date: datetime
    has_attachment: bool
    attachment_metadata: tuple[AttachmentMetadata, ...] = ()

    def __post_init__(self) -> None:
        if not self.id or not self.thread_id:
            raise ValueError("message id and thread_id are required")
        _validate_email(self.from_address, "from_address")
        _validate_emails(self.to_addresses, "to_addresses")
        _validate_emails(self.cc_addresses, "cc_addresses")


@dataclass(frozen=True, slots=True)
class GmailThread:
    id: str
    messages: tuple[GmailMessage, ...]
    labels: tuple[str, ...]
    snippet: str

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("thread id is required")
        for msg in self.messages:
            if msg.thread_id != self.id:
                raise ValueError("message thread_id does not match thread id")


@dataclass(frozen=True, slots=True)
class GmailDraft:
    id: str
    message: GmailMessage
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("draft id is required")


class GmailProvider(Protocol):
    async def search_messages(self, query: str, *, limit: int, page_token: str | None = None) -> tuple[list[GmailMessage], str | None]: ...
    async def read_message(self, message_id: str) -> GmailMessage: ...
    async def thread_summary(self, thread_id: str) -> GmailThread: ...
    async def attachment_metadata(self, message_id: str) -> tuple[AttachmentMetadata, ...]: ...
    async def create_draft(self, *, to: tuple[str, ...], subject: str, body: str, thread_id: str | None = None, cc: tuple[str, ...] = ()) -> GmailDraft: ...
    async def update_draft(self, draft_id: str, *, to: tuple[str, ...] | None = None, subject: str | None = None, body: str | None = None, thread_id: str | None = None, cc: tuple[str, ...] | None = None) -> GmailDraft: ...
    async def send_draft(self, draft_id: str) -> GmailMessage: ...
    async def reply(self, message_id: str, *, body: str) -> GmailMessage: ...
    async def label(self, message_id: str, *, add: tuple[str, ...] = (), remove: tuple[str, ...] = ()) -> GmailMessage: ...
    async def archive(self, message_id: str) -> GmailMessage: ...
    async def delete(self, message_id: str) -> None: ...
