"""Mocked LinkedIn API tests covering draft workflows, unsupported actions, scope denial, and sensitive data handling."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.tools.audit import ToolAuditLog
from src.tools.linkedin_factory import create_linkedin_registry
from src.tools.linkedin_models import LinkedInCompany, LinkedInPost, LinkedInProfile, LinkedInScope
from src.tools.linkedin_provider import MockLinkedInProvider
from src.tools.models import ToolPermissionError, ToolRequest, ToolValidationError
from src.tools.linkedin_tools import (
    AnalyzePostTool,
    AnalyzeProfileTool,
    CreateMessageDraftTool,
    CreatePostDraftTool,
    DetectOfficialApiCapabilitiesTool,
    ImproveProfileTool,
    ImportCompanyTool,
    ImportPostTool,
    ImportProfileTool,
    PublishPostTool,
    SendMessageTool,
)


def _make_provider() -> MockLinkedInProvider:
    provider = MockLinkedInProvider()
    profile = LinkedInProfile(
        id="profile_1", first_name="Alice", last_name="Doe",
        headline="Software Engineer at ExampleCorp",
        summary="Building great products.",
        skills=("Python", "Testing"),
    )
    provider.add_profile(profile)
    post = LinkedInPost(
        id="post_1", content="Hello world!", author_id="profile_1",
        created_at=datetime.now(timezone.utc),
    )
    provider.add_post(post)
    company = LinkedInCompany(
        id="company_1", name="ExampleCorp", industry="Software",
        size="50-200", description="A example company.",
    )
    provider.add_company(company)
    return provider


@pytest.mark.asyncio
async def test_detect_capabilities_reports_scopes(tmp_path: Path):
    provider = _make_provider()
    provider.configure_scopes((LinkedInScope.PROFILE, LinkedInScope.POSTS, LinkedInScope.MESSAGING))
    registry = create_linkedin_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("linkedin.detect_official_api_capabilities", {}))
    assert result.success
    output = result.output
    assert output["can_publish_posts"] is True
    assert output["can_send_messages"] is True
    assert output["can_read_profile"] is True
    assert output["can_manage_organization"] is False


@pytest.mark.asyncio
async def test_detect_capabilities_without_scopes(tmp_path: Path):
    provider = _make_provider()
    registry = create_linkedin_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("linkedin.detect_official_api_capabilities", {}))
    assert result.success
    output = result.output
    assert output["can_publish_posts"] is False
    assert output["can_send_messages"] is False
    assert output["scopes"] == []


@pytest.mark.asyncio
async def test_analyze_profile_read_only(tmp_path: Path):
    provider = _make_provider()
    registry = create_linkedin_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("linkedin.analyze_profile", {"profile_id": "profile_1"}))
    assert result.success
    output = result.output
    assert output["profile_id"] == "profile_1"
    assert output["name"] == "Alice Doe"
    assert any("Expand the headline" in s for s in output["suggestions"])
    assert any("Expand the summary" in s for s in output["suggestions"])


@pytest.mark.asyncio
async def test_import_profile_succeeds_without_credentials(tmp_path: Path):
    provider = _make_provider()
    registry = create_linkedin_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("linkedin.import_profile", {
        "profile_id": "profile_local", "headline": "My headline", "summary": "My summary", "skills": ["A", "B"],
    }), confirmed=True)
    assert result.success
    output = result.output
    assert output["imported"] is True
    assert output["headline"] == "My headline"


@pytest.mark.asyncio
async def test_create_post_draft_local_only(tmp_path: Path):
    provider = _make_provider()
    registry = create_linkedin_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("linkedin.create_post_draft", {"content": "Draft post"}), confirmed=True)
    assert result.success
    output = result.output
    assert output["draft_type"] == "post"
    assert output["content"] == "Draft post"
    assert output["status"] == "draft"


@pytest.mark.asyncio
async def test_create_message_draft_local_only(tmp_path: Path):
    provider = _make_provider()
    registry = create_linkedin_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("linkedin.create_message_draft", {"target_uri": "urn:li:person:rec_1", "content": "Hello"}), confirmed=True)
    assert result.success
    output = result.output
    assert output["draft_type"] == "message"
    assert output["target_uri"] == "urn:li:person:rec_1"


@pytest.mark.asyncio
async def test_improve_profile_generates_suggestions(tmp_path: Path):
    provider = _make_provider()
    registry = create_linkedin_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("linkedin.improve_profile", {"profile_id": "profile_1"}), confirmed=True)
    assert result.success
    output = result.output
    assert "requires_review" in output
    assert output["requires_review"] is True
    assert "improved_headline" in output


@pytest.mark.asyncio
async def test_publish_post_denied_without_scope(tmp_path: Path):
    provider = _make_provider()
    registry = create_linkedin_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("linkedin.publish_post", {"draft_id": "missing"}), confirmed=True)
    assert not result.success
    assert result.error_code == "permission_denied"
    assert "w_member_social" in result.error_message


@pytest.mark.asyncio
async def test_send_message_denied_without_scope(tmp_path: Path):
    provider = _make_provider()
    registry = create_linkedin_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("linkedin.send_message", {"target_uri": "urn:li:person:rec_1", "content": "Hi"}), confirmed=True)
    assert not result.success
    assert result.error_code == "permission_denied"
    assert "w_messaging" in result.error_message


@pytest.mark.asyncio
async def test_publish_post_requires_scope_and_preview(tmp_path: Path):
    provider = _make_provider()
    provider.configure_scopes((LinkedInScope.POSTS,))
    registry = create_linkedin_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("linkedin.publish_post", {"draft_id": "missing"}), confirmed=True)
    assert not result.success
    assert result.error_code == "execution_error"


@pytest.mark.asyncio
async def test_send_message_requires_scope_and_confirmation(tmp_path: Path):
    provider = _make_provider()
    provider.configure_scopes((LinkedInScope.MESSAGING,))
    registry = create_linkedin_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("linkedin.send_message", {"target_uri": "urn:li:person:rec_1", "content": "Hi"}), confirmed=True)
    assert not result.success
    assert result.error_code == "execution_error"


def test_validation_rejects_empty_fields():
    with pytest.raises(ToolValidationError):
        DetectOfficialApiCapabilitiesTool(None).validate({"unknown": True})
    with pytest.raises(ToolValidationError):
        ImportProfileTool(None).validate({"profile_id": "", "headline": "Hi"})
    with pytest.raises(ToolValidationError):
        CreatePostDraftTool(None).validate({"content": ""})
    with pytest.raises(ToolValidationError):
        CreateMessageDraftTool(None).validate({"target_uri": "ok", "content": ""})
    with pytest.raises(ToolValidationError):
        SendMessageTool(None).validate({"target_uri": "", "content": "Hi"})


@pytest.mark.asyncio
async def test_audit_redacts_sensitive_fields(tmp_path: Path):
    provider = _make_provider()
    audit_path = tmp_path / "audit.jsonl"
    registry = create_linkedin_registry(provider, audit_path=audit_path)
    await registry.invoke(ToolRequest("linkedin.create_message_draft", {"target_uri": "urn:li:person:rec_1", "content": "secret"}), confirmed=True)
    entries = registry.audit_log.entries()
    assert entries
    record = entries[-1]
    assert record.tool_name == "linkedin.create_message_draft"
    assert record.arguments["content"] == "secret"
    assert record.arguments["target_uri"] == "urn:li:person:rec_1"


@pytest.mark.asyncio
async def test_import_company_without_credentials(tmp_path: Path):
    provider = _make_provider()
    registry = create_linkedin_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("linkedin.import_company", {"company_id": "company_local", "name": "ACME", "description": "Desc"}), confirmed=True)
    assert result.success
    output = result.output
    assert output["imported"] is True
    assert output["name"] == "ACME"


@pytest.mark.asyncio
async def test_tool_descriptors_expose_expected_risk_levels():
    provider = _make_provider()
    registry = create_linkedin_registry(provider)
    risks = {item.name: item.risk.value for item in registry.discover()}
    assert risks["linkedin.detect_official_api_capabilities"] == "read_only"
    assert risks["linkedin.analyze_profile"] == "read_only"
    assert risks["linkedin.analyze_post"] == "read_only"
    assert risks["linkedin.create_post_draft"] == "local_write"
    assert risks["linkedin.create_message_draft"] == "local_write"
    assert risks["linkedin.improve_profile"] == "local_write"
    assert risks["linkedin.publish_post"] == "external"
    assert risks["linkedin.send_message"] == "external"


@pytest.mark.asyncio
async def test_analyze_post_read_only(tmp_path: Path):
    provider = _make_provider()
    registry = create_linkedin_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("linkedin.analyze_post", {"post_id": "post_1"}))
    assert result.success
    output = result.output
    assert output["post_id"] == "post_1"
    assert "suggestions" in output
