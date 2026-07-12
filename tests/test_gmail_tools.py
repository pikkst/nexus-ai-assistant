"""Mocked Gmail API tests covering pagination, drafts, confirmation, failures, and duplicate sends."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.tools.audit import ToolAuditLog
from src.tools.gmail_factory import create_gmail_registry
from src.tools.gmail_models import GmailDraft, GmailMessage, GmailThread, AttachmentMetadata
from src.tools.gmail_provider import MockGmailProvider
from src.tools.models import ToolPermissionError, ToolRequest, ToolValidationError
from src.tools.gmail_tools import SearchMessagesTool, ReadMessageTool, ThreadSummaryTool, AttachmentMetadataTool, CreateDraftTool, UpdateDraftTool, SendDraftTool, ReplyTool, LabelTool, ArchiveTool, DeleteTool


def _make_provider() -> MockGmailProvider:
    provider = MockGmailProvider()
    message = GmailMessage(
        id="msg_1", thread_id="thread_1", subject="Hello", from_address="alice@example.test",
        to_addresses=("bob@example.test",), cc_addresses=(), snippet="Hi Bob", body="Hi Bob",
        labels=("INBOX",), date=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        has_attachment=False,
    )
    provider.add_message(message)
    return provider


@pytest.mark.asyncio
async def test_read_tools_are_read_only_and_do_not_require_confirmation(tmp_path: Path):
    provider = _make_provider()
    registry = create_gmail_registry(provider, audit_path=tmp_path / "audit.jsonl")
    search = await registry.invoke(ToolRequest("gmail.search_messages", {"query": "hello"}))
    assert search.success and search.error_code is None
    read = await registry.invoke(ToolRequest("gmail.read_message", {"message_id": "msg_1"}))
    assert read.success and read.error_code is None
    thread = await registry.invoke(ToolRequest("gmail.thread_summary", {"thread_id": "thread_1"}))
    assert thread.success and thread.error_code is None
    attach = await registry.invoke(ToolRequest("gmail.attachment_metadata", {"message_id": "msg_1"}))
    assert attach.success and attach.error_code is None


@pytest.mark.asyncio
async def test_search_pagination(tmp_path: Path):
    provider = MockGmailProvider()
    for i in range(5):
        msg = GmailMessage(
            id=f"msg_{i}", thread_id=f"thread_{i}", subject=f"Subject {i}", from_address="a@b.test",
            to_addresses=("c@d.test",), cc_addresses=(), snippet=f"Snippet {i}", body=f"Body {i}",
            labels=("INBOX",), date=__import__("datetime").datetime.now(__import__("datetime").timezone.utc), has_attachment=False,
        )
        provider.add_message(msg)
    registry = create_gmail_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("gmail.search_messages", {"query": "Subject", "limit": 3}))
    assert result.success
    output = result.output
    assert len(output["messages"]) == 3
    assert output["next_page_token"] == "3"


def test_create_draft_requires_validation():
    with pytest.raises(ToolValidationError):
        CreateDraftTool(None).validate({"to": [], "subject": "", "body": ""})
    with pytest.raises(ToolValidationError):
        CreateDraftTool(None).validate({"to": ["bad"], "subject": "Hi", "body": "Body"})


@pytest.mark.asyncio
async def test_create_and_update_draft(tmp_path: Path):
    provider = _make_provider()
    registry = create_gmail_registry(provider, audit_path=tmp_path / "audit.jsonl")
    created = await registry.invoke(ToolRequest("gmail.create_draft", {"to": ["alice@example.test"], "subject": "Draft", "body": "Body", "cc": ["cc@example.test"]}), confirmed=True)
    assert created.success and created.output["draft_id"]
    updated = await registry.invoke(ToolRequest("gmail.update_draft", {"draft_id": created.output["draft_id"], "subject": "Updated"}), confirmed=True)
    assert updated.success and updated.output["message"]["subject"] == "Updated"


@pytest.mark.asyncio
async def test_send_draft_requires_confirmation_and_prevents_duplicate(tmp_path: Path):
    provider = _make_provider()
    registry = create_gmail_registry(provider, audit_path=tmp_path / "audit.jsonl")
    created = await registry.invoke(ToolRequest("gmail.create_draft", {"to": ["alice@example.test"], "subject": "Send me", "body": "Body"}), confirmed=True)
    draft_id = created.output["draft_id"]
    first = await registry.invoke(ToolRequest("gmail.send_draft", {"draft_id": draft_id}))
    assert first.error_code == "confirmation_required"
    sent = await registry.invoke(ToolRequest("gmail.send_draft", {"draft_id": draft_id}), confirmed=True)
    assert sent.success
    duplicate = await registry.invoke(ToolRequest("gmail.send_draft", {"draft_id": draft_id}), confirmed=True)
    assert duplicate.success is False and "already sent" in (duplicate.error_message or "")


@pytest.mark.asyncio
async def test_reply_label_archive_require_confirmation(tmp_path: Path):
    provider = _make_provider()
    registry = create_gmail_registry(provider, audit_path=tmp_path / "audit.jsonl")
    reply = await registry.invoke(ToolRequest("gmail.reply", {"message_id": "msg_1", "body": "Thanks"}))
    assert reply.error_code == "confirmation_required"
    label = await registry.invoke(ToolRequest("gmail.label", {"message_id": "msg_1", "add": ("IMPORTANT",)}))
    assert label.error_code == "confirmation_required"
    archive = await registry.invoke(ToolRequest("gmail.archive", {"message_id": "msg_1"}))
    assert archive.error_code == "confirmation_required"


@pytest.mark.asyncio
async def test_delete_requires_confirmation_and_is_destructive(tmp_path: Path):
    provider = _make_provider()
    registry = create_gmail_registry(provider, audit_path=tmp_path / "audit.jsonl")
    delete_req = ToolRequest("gmail.delete", {"message_id": "msg_1"})
    result = await registry.invoke(delete_req)
    assert result.error_code == "confirmation_required"
    confirmed = await registry.invoke(delete_req, confirmed=True)
    assert confirmed.success


@pytest.mark.asyncio
async def test_audit_redacts_body_and_addresses(tmp_path: Path):
    provider = _make_provider()
    audit_path = tmp_path / "audit.jsonl"
    registry = create_gmail_registry(provider, audit_path=audit_path)
    await registry.invoke(ToolRequest("gmail.create_draft", {"to": ["alice@example.test"], "subject": "Secret", "body": "Body"}), confirmed=True)
    entries = registry.audit_log.entries()
    assert entries
    raw = entries[0].arguments
    assert "alice@example.test" not in str(raw)
    assert "Secret" not in str(raw)
    assert "Body" not in str(raw)


def test_validation_rejects_invalid_message_ids_and_empty_fields():
    with pytest.raises(ToolValidationError):
        SearchMessagesTool(None).validate({"query": ""})
    with pytest.raises(ToolValidationError):
        ReadMessageTool(None).validate({"message_id": ""})
    with pytest.raises(ToolValidationError):
        CreateDraftTool(None).validate({"to": ["a@b.test"], "subject": "Hi", "body": ""})
    with pytest.raises(ToolValidationError):
        ReplyTool(None).validate({"message_id": "msg_1", "body": "   "})


def test_tool_descriptors_expose_expected_risk_levels():
    provider = _make_provider()
    registry = create_gmail_registry(provider)
    risks = {item.name: item.risk.value for item in registry.discover()}
    assert risks["gmail.search_messages"] == "read_only"
    assert risks["gmail.read_message"] == "read_only"
    assert risks["gmail.thread_summary"] == "read_only"
    assert risks["gmail.attachment_metadata"] == "read_only"
    assert risks["gmail.create_draft"] == "local_write"
    assert risks["gmail.update_draft"] == "local_write"
    assert risks["gmail.send_draft"] == "external"
    assert risks["gmail.reply"] == "external"
    assert risks["gmail.label"] == "external"
    assert risks["gmail.archive"] == "external"
    assert risks["gmail.delete"] == "destructive"
