"""Permissioned Gmail tools for search, read, draft, send, reply, label, archive, and delete."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .audit import ToolAuditLog, redact
from .gmail_models import (
    AttachmentMetadata,
    GmailDraft,
    GmailMessage,
    GmailProvider,
    GmailThread,
    _validate_email,
    _validate_emails,
)
from .models import RiskLevel, Tool, ToolDescriptor, ToolValidationError
from .permissions import PermissionPolicy
from .registry import ToolRegistry


def _validate_message_id(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ToolValidationError(f"{field_name} must be a non-empty string")
    return value.strip()


def _validate_attachment_limits(limits: tuple[int, ...]) -> None:
    for limit in limits:
        if not isinstance(limit, int) or limit < 0:
            raise ToolValidationError("attachment_limits must be an array of non-negative integers")


def _gmail_attachment_metadata(metadata: tuple[AttachmentMetadata, ...]) -> list[dict[str, Any]]:
    return [{"filename": item.filename, "mime_type": item.mime_type, "size": item.size} for item in metadata]


def _gmail_message_dict(message: GmailMessage) -> dict[str, Any]:
    return {
        "id": message.id, "thread_id": message.thread_id, "subject": message.subject,
        "from_address": message.from_address, "to_addresses": list(message.to_addresses),
        "cc_addresses": list(message.cc_addresses), "snippet": message.snippet,
        "labels": list(message.labels), "date": message.date.isoformat(),
        "has_attachment": message.has_attachment,
        "attachment_metadata": _gmail_attachment_metadata(message.attachment_metadata),
    }


def _gmail_thread_dict(thread: GmailThread) -> dict[str, Any]:
    return {
        "id": thread.id, "snippet": thread.snippet, "labels": list(thread.labels),
        "messages": [_gmail_message_dict(msg) for msg in thread.messages],
    }


class SearchMessagesTool:
    name, description, risk = "gmail.search_messages", "Search Gmail messages matching a query.", RiskLevel.READ_ONLY
    parameters = {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 50}, "page_token": {"type": "string"}}, "required": ["query"], "additionalProperties": False}

    def __init__(self, provider: GmailProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        if not isinstance(arguments.get("query"), str) or not arguments["query"].strip():
            raise ToolValidationError("query must be a non-empty string")
        limit = arguments.get("limit", 10)
        if not isinstance(limit, int) or not 1 <= limit <= 50:
            raise ToolValidationError("limit must be between 1 and 50")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        messages, next_token = await self.provider.search_messages(
            arguments["query"], limit=arguments.get("limit", 10), page_token=arguments.get("page_token"),
        )
        return {"messages": [_gmail_message_dict(msg) for msg in messages], "next_page_token": next_token}


class ReadMessageTool:
    name, description, risk = "gmail.read_message", "Read a single Gmail message by id.", RiskLevel.READ_ONLY
    parameters = {"type": "object", "properties": {"message_id": {"type": "string"}}, "required": ["message_id"], "additionalProperties": False}

    def __init__(self, provider: GmailProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_message_id(arguments.get("message_id"), "message_id")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        message = await self.provider.read_message(arguments["message_id"])
        return _gmail_message_dict(message)


class ThreadSummaryTool:
    name, description, risk = "gmail.thread_summary", "Return a Gmail thread with all messages.", RiskLevel.READ_ONLY
    parameters = {"type": "object", "properties": {"thread_id": {"type": "string"}}, "required": ["thread_id"], "additionalProperties": False}

    def __init__(self, provider: GmailProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_message_id(arguments.get("thread_id"), "thread_id")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        thread = await self.provider.thread_summary(arguments["thread_id"])
        return _gmail_thread_dict(thread)


class AttachmentMetadataTool:
    name, description, risk = "gmail.attachment_metadata", "Return attachment metadata for a message.", RiskLevel.READ_ONLY
    parameters = {"type": "object", "properties": {"message_id": {"type": "string"}}, "required": ["message_id"], "additionalProperties": False}

    def __init__(self, provider: GmailProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_message_id(arguments.get("message_id"), "message_id")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        metadata = await self.provider.attachment_metadata(arguments["message_id"])
        return {"message_id": arguments["message_id"], "attachments": _gmail_attachment_metadata(metadata)}


class CreateDraftTool:
    name, description, risk = "gmail.create_draft", "Create a new Gmail draft without sending.", RiskLevel.LOCAL_WRITE
    parameters = {"type": "object", "properties": {"to": {"type": "array", "items": {"type": "string"}}, "subject": {"type": "string"}, "body": {"type": "string"}, "thread_id": {"type": "string"}, "cc": {"type": "array", "items": {"type": "string"}}, "attachment_limits": {"type": "array", "items": {"type": "integer"}}}, "required": ["to", "subject", "body"], "additionalProperties": False}

    def __init__(self, provider: GmailProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        to = arguments.get("to")
        if not isinstance(to, list) or not to:
            raise ToolValidationError("to must be a non-empty array of email addresses")
        try:
            _validate_emails(tuple(to), "to")
        except ValueError as exc:
            raise ToolValidationError(str(exc)) from exc
        if not isinstance(arguments.get("subject"), str) or not arguments["subject"].strip():
            raise ToolValidationError("subject must be a non-empty string")
        if not isinstance(arguments.get("body"), str) or not arguments["body"].strip():
            raise ToolValidationError("body must be a non-empty string")
        if len(arguments["subject"]) > 256:
            raise ToolValidationError("subject must be 256 characters or fewer")
        if len(arguments["body"]) > 102400:
            raise ToolValidationError("body must be 102400 characters or fewer")
        cc = arguments.get("cc", ())
        if cc:
            try:
                _validate_emails(tuple(cc), "cc")
            except ValueError as exc:
                raise ToolValidationError(str(exc)) from exc
        limits = arguments.get("attachment_limits", ())
        if limits:
            _validate_attachment_limits(tuple(limits))

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        draft = await self.provider.create_draft(
            to=tuple(arguments["to"]), subject=arguments["subject"], body=arguments["body"],
            thread_id=arguments.get("thread_id"), cc=tuple(arguments.get("cc", ())),
        )
        return {"draft_id": draft.id, "message": _gmail_message_dict(draft.message), "created_at": draft.created_at.isoformat()}


class UpdateDraftTool:
    name, description, risk = "gmail.update_draft", "Update an existing Gmail draft.", RiskLevel.LOCAL_WRITE
    parameters = {"type": "object", "properties": {"draft_id": {"type": "string"}, "to": {"type": "array", "items": {"type": "string"}}, "subject": {"type": "string"}, "body": {"type": "string"}, "thread_id": {"type": "string"}, "cc": {"type": "array", "items": {"type": "string"}}}, "required": ["draft_id"], "additionalProperties": False}

    def __init__(self, provider: GmailProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_message_id(arguments.get("draft_id"), "draft_id")
        if not any(key in arguments for key in ("to", "subject", "body", "thread_id", "cc")):
            raise ToolValidationError("at least one field must be provided for update")
        to = arguments.get("to")
        if to is not None:
            if not isinstance(to, list) or not to:
                raise ToolValidationError("to must be a non-empty array of email addresses")
            try:
                _validate_emails(tuple(to), "to")
            except ValueError as exc:
                raise ToolValidationError(str(exc)) from exc
        subject = arguments.get("subject")
        if subject is not None:
            if not isinstance(subject, str) or not subject.strip():
                raise ToolValidationError("subject must be a non-empty string")
            if len(subject) > 256:
                raise ToolValidationError("subject must be 256 characters or fewer")
        body = arguments.get("body")
        if body is not None:
            if not isinstance(body, str) or not body.strip():
                raise ToolValidationError("body must be a non-empty string")
            if len(body) > 102400:
                raise ToolValidationError("body must be 102400 characters or fewer")
        cc = arguments.get("cc")
        if cc is not None:
            try:
                _validate_emails(tuple(cc), "cc")
            except ValueError as exc:
                raise ToolValidationError(str(exc)) from exc

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        draft = await self.provider.update_draft(
            arguments["draft_id"],
            to=tuple(arguments["to"]) if "to" in arguments else None,
            subject=arguments.get("subject"), body=arguments.get("body"),
            thread_id=arguments.get("thread_id"),
            cc=tuple(arguments["cc"]) if "cc" in arguments else None,
        )
        return {"draft_id": draft.id, "message": _gmail_message_dict(draft.message), "created_at": draft.created_at.isoformat()}


class SendDraftTool:
    name, description, risk = "gmail.send_draft", "Send an existing Gmail draft.", RiskLevel.EXTERNAL
    parameters = {"type": "object", "properties": {"draft_id": {"type": "string"}}, "required": ["draft_id"], "additionalProperties": False}

    def __init__(self, provider: GmailProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_message_id(arguments.get("draft_id"), "draft_id")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        message = await self.provider.send_draft(arguments["draft_id"])
        return _gmail_message_dict(message)


class ReplyTool:
    name, description, risk = "gmail.reply", "Reply to a Gmail message.", RiskLevel.EXTERNAL
    parameters = {"type": "object", "properties": {"message_id": {"type": "string"}, "body": {"type": "string"}}, "required": ["message_id", "body"], "additionalProperties": False}

    def __init__(self, provider: GmailProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_message_id(arguments.get("message_id"), "message_id")
        if not isinstance(arguments.get("body"), str) or not arguments["body"].strip():
            raise ToolValidationError("body must be a non-empty string")
        if len(arguments["body"]) > 102400:
            raise ToolValidationError("body must be 102400 characters or fewer")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        message = await self.provider.reply(arguments["message_id"], body=arguments["body"])
        return _gmail_message_dict(message)


class LabelTool:
    name, description, risk = "gmail.label", "Add or remove labels from a Gmail message.", RiskLevel.EXTERNAL
    parameters = {"type": "object", "properties": {"message_id": {"type": "string"}, "add": {"type": "array", "items": {"type": "string"}}, "remove": {"type": "array", "items": {"type": "string"}}}, "required": ["message_id"], "additionalProperties": False}

    def __init__(self, provider: GmailProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_message_id(arguments.get("message_id"), "message_id")
        add = arguments.get("add", ())
        remove = arguments.get("remove", ())
        if not isinstance(add, (list, tuple)):
            raise ToolValidationError("add must be an array of label names")
        if not isinstance(remove, (list, tuple)):
            raise ToolValidationError("remove must be an array of label names")
        if not add and not remove:
            raise ToolValidationError("at least one label must be added or removed")
        for label in add:
            if not isinstance(label, str) or not label.strip():
                raise ToolValidationError("label names must be non-empty strings")
        for label in remove:
            if not isinstance(label, str) or not label.strip():
                raise ToolValidationError("label names must be non-empty strings")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        message = await self.provider.label(
            arguments["message_id"],
            add=tuple(arguments.get("add", ())),
            remove=tuple(arguments.get("remove", ())),
        )
        return _gmail_message_dict(message)


class ArchiveTool:
    name, description, risk = "gmail.archive", "Archive a Gmail message by removing INBOX label.", RiskLevel.EXTERNAL
    parameters = {"type": "object", "properties": {"message_id": {"type": "string"}}, "required": ["message_id"], "additionalProperties": False}

    def __init__(self, provider: GmailProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_message_id(arguments.get("message_id"), "message_id")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        message = await self.provider.archive(arguments["message_id"])
        return _gmail_message_dict(message)


class DeleteTool:
    name, description, risk = "gmail.delete", "Permanently delete a Gmail message.", RiskLevel.DESTRUCTIVE
    parameters = {"type": "object", "properties": {"message_id": {"type": "string"}}, "required": ["message_id"], "additionalProperties": False}

    def __init__(self, provider: GmailProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_message_id(arguments.get("message_id"), "message_id")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        await self.provider.delete(arguments["message_id"])
        return {"deleted": True, "message_id": arguments["message_id"]}
