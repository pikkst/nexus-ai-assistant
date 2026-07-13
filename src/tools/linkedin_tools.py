"""Permissioned LinkedIn tools for profile analysis, drafting, and reviewed handoff."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .audit import ToolAuditLog, redact
from .linkedin_models import (
    LinkedInCompany,
    LinkedInDraft,
    LinkedInMessage,
    LinkedInPost,
    LinkedInProfile,
    LinkedInProvider,
    LinkedInScope,
)
from .models import RiskLevel, Tool, ToolDescriptor, ToolPermissionError, ToolValidationError
from .permissions import PermissionPolicy
from .registry import ToolRegistry


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _validate_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ToolValidationError(f"{field_name} must be a non-empty string")
    return value.strip()


def _validate_id(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ToolValidationError(f"{field_name} must be a non-empty string")
    return value.strip()


def _validate_skills(value: Any, field_name: str) -> tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)
    raise ToolValidationError(f"{field_name} must be an array of strings")


class DetectOfficialApiCapabilitiesTool:
    name, description, risk = "linkedin.detect_official_api_capabilities", "Detect official LinkedIn API capabilities and granted scopes.", RiskLevel.READ_ONLY
    parameters = {"type": "object", "properties": {}, "additionalProperties": False}

    def __init__(self, provider: LinkedInProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        if arguments:
            raise ToolValidationError("no arguments are accepted")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        scopes = self.provider.scopes
        has_profile = LinkedInScope.PROFILE in scopes
        has_email = LinkedInScope.EMAIL in scopes
        has_posts = LinkedInScope.POSTS in scopes
        has_messaging = LinkedInScope.MESSAGING in scopes
        has_organization = LinkedInScope.ORGANIZATION in scopes
        capabilities = {
            "scopes": [scope.value for scope in scopes],
            "can_read_profile": has_profile or has_email,
            "can_publish_posts": has_posts,
            "can_send_messages": has_messaging,
            "can_manage_organization": has_organization,
        }
        return capabilities


class AnalyzeProfileTool:
    name, description, risk = "linkedin.analyze_profile", "Analyze a LinkedIn profile locally for improvement suggestions.", RiskLevel.READ_ONLY
    parameters = {
        "type": "object",
        "properties": {
            "profile_id": {"type": "string"},
            "headline": {"type": "string"},
            "summary": {"type": "string"},
            "skills": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["profile_id"],
        "additionalProperties": False,
    }

    def __init__(self, provider: LinkedInProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_id(arguments.get("profile_id"), "profile_id")
        headline = arguments.get("headline", "")
        if headline and len(headline) > 220:
            raise ToolValidationError("headline must be 220 characters or fewer")
        summary = arguments.get("summary", "")
        if summary and len(summary) > 2000:
            raise ToolValidationError("summary must be 2000 characters or fewer")
        _validate_skills(arguments.get("skills", ()), "skills")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        profile_id = arguments["profile_id"]
        try:
            profile = await self.provider.get_profile(profile_id)
        except ValueError:
            profile = LinkedInProfile(
                id=profile_id,
                first_name="",
                last_name="",
                headline=arguments.get("headline", ""),
                summary=arguments.get("summary", ""),
                skills=tuple(arguments.get("skills", [])),
            )
        suggestions: list[str] = []
        if not profile.headline.strip():
            suggestions.append("Add a professional headline that summarizes your expertise.")
        elif len(profile.headline) < 50:
            suggestions.append("Expand the headline to better describe your value proposition.")
        if not profile.summary.strip():
            suggestions.append("Add a summary that highlights key achievements and goals.")
        elif len(profile.summary) < 100:
            suggestions.append("Expand the summary with more detail about your experience and goals.")
        if len(profile.skills) < 3:
            suggestions.append("Add at least 3 relevant skills to improve profile discoverability.")
        return {
            "profile_id": profile.id,
            "name": f"{profile.first_name} {profile.last_name}".strip(),
            "headline": profile.headline,
            "summary": profile.summary,
            "skills": list(profile.skills),
            "suggestions": suggestions,
        }


class AnalyzePostTool:
    name, description, risk = "linkedin.analyze_post", "Analyze a LinkedIn post locally for tone, length, and engagement suggestions.", RiskLevel.READ_ONLY
    parameters = {
        "type": "object",
        "properties": {
            "post_id": {"type": "string"},
            "content": {"type": "string"},
            "visibility": {"type": "string"},
        },
        "required": ["post_id"],
        "additionalProperties": False,
    }

    def __init__(self, provider: LinkedInProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_id(arguments.get("post_id"), "post_id")
        content = arguments.get("content", "")
        if content and len(content) > 3000:
            raise ToolValidationError("content must be 3000 characters or fewer")
        visibility = arguments.get("visibility", "PUBLIC")
        if visibility not in {"PUBLIC", "CONNECTIONS_ONLY"}:
            raise ToolValidationError("visibility must be PUBLIC or CONNECTIONS_ONLY")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        post_id = arguments["post_id"]
        try:
            post = await self.provider.get_post(post_id)
            content = post.content
            visibility = post.visibility
        except ValueError:
            content = arguments.get("content", "")
            visibility = arguments.get("visibility", "PUBLIC")
        suggestions: list[str] = []
        word_count = len(content.split())
        if word_count < 10:
            suggestions.append("Consider expanding the post to provide more context or insight.")
        if word_count > 500:
            suggestions.append("The post is quite long; consider breaking it into a series for better engagement.")
        if not content.startswith(("#", "I ", "We ", "My ", "Our ")):
            suggestions.append("Start with a hook or question to increase engagement.")
        if visibility == "PUBLIC":
            suggestions.append("Public posts reach a wider audience; ensure the content is appropriate for a broad professional audience.")
        return {
            "post_id": post_id,
            "content": content,
            "word_count": word_count,
            "visibility": visibility,
            "suggestions": suggestions,
        }


class ImportProfileTool:
    name, description, risk = "linkedin.import_profile", "Import or enter LinkedIn profile content for local analysis.", RiskLevel.LOCAL_WRITE
    parameters = {
        "type": "object",
        "properties": {
            "profile_id": {"type": "string"},
            "headline": {"type": "string"},
            "summary": {"type": "string"},
            "skills": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["profile_id"],
        "additionalProperties": False,
    }

    def __init__(self, provider: LinkedInProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_id(arguments.get("profile_id"), "profile_id")
        headline = arguments.get("headline", "")
        if headline and len(headline) > 220:
            raise ToolValidationError("headline must be 220 characters or fewer")
        summary = arguments.get("summary", "")
        if summary and len(summary) > 2000:
            raise ToolValidationError("summary must be 2000 characters or fewer")
        _validate_skills(arguments.get("skills", ()), "skills")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        profile = LinkedInProfile(
            id=arguments["profile_id"],
            first_name="",
            last_name="",
            headline=arguments.get("headline", ""),
            summary=arguments.get("summary", ""),
            skills=tuple(arguments.get("skills", [])),
        )
        return {
            "profile_id": profile.id,
            "headline": profile.headline,
            "summary": profile.summary,
            "skills": list(profile.skills),
            "imported": True,
        }


class ImportPostTool:
    name, description, risk = "linkedin.import_post", "Import or enter LinkedIn post content for local analysis.", RiskLevel.LOCAL_WRITE
    parameters = {
        "type": "object",
        "properties": {
            "post_id": {"type": "string"},
            "content": {"type": "string"},
            "visibility": {"type": "string"},
        },
        "required": ["post_id", "content"],
        "additionalProperties": False,
    }

    def __init__(self, provider: LinkedInProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_id(arguments.get("post_id"), "post_id")
        _validate_text(arguments.get("content"), "content")
        if len(arguments["content"]) > 3000:
            raise ToolValidationError("content must be 3000 characters or fewer")
        visibility = arguments.get("visibility", "PUBLIC")
        if visibility not in {"PUBLIC", "CONNECTIONS_ONLY"}:
            raise ToolValidationError("visibility must be PUBLIC or CONNECTIONS_ONLY")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return {
            "post_id": arguments["post_id"],
            "content": arguments["content"],
            "visibility": arguments.get("visibility", "PUBLIC"),
            "imported": True,
        }


class ImportCompanyTool:
    name, description, risk = "linkedin.import_company", "Import or enter LinkedIn company content for local analysis.", RiskLevel.LOCAL_WRITE
    parameters = {
        "type": "object",
        "properties": {
            "company_id": {"type": "string"},
            "name": {"type": "string"},
            "industry": {"type": "string"},
            "size": {"type": "string"},
            "description": {"type": "string"},
        },
        "required": ["company_id", "name"],
        "additionalProperties": False,
    }

    def __init__(self, provider: LinkedInProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_id(arguments.get("company_id"), "company_id")
        _validate_text(arguments.get("name"), "name")
        description = arguments.get("description", "")
        if description and len(description) > 2000:
            raise ToolValidationError("description must be 2000 characters or fewer")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return {
            "company_id": arguments["company_id"],
            "name": arguments["name"],
            "industry": arguments.get("industry", ""),
            "size": arguments.get("size", ""),
            "description": arguments.get("description", ""),
            "imported": True,
        }


class CreatePostDraftTool:
    name, description, risk = "linkedin.create_post_draft", "Create an editable LinkedIn post draft without publishing.", RiskLevel.LOCAL_WRITE
    parameters = {
        "type": "object",
        "properties": {
            "content": {"type": "string"},
            "visibility": {"type": "string"},
        },
        "required": ["content"],
        "additionalProperties": False,
    }

    def __init__(self, provider: LinkedInProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_text(arguments.get("content"), "content")
        if len(arguments["content"]) > 3000:
            raise ToolValidationError("content must be 3000 characters or fewer")
        visibility = arguments.get("visibility", "PUBLIC")
        if visibility not in {"PUBLIC", "CONNECTIONS_ONLY"}:
            raise ToolValidationError("visibility must be PUBLIC or CONNECTIONS_ONLY")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        draft = LinkedInDraft(
            id="", draft_type="post", content=arguments["content"],
            created_at=_now(),
        )
        saved = await self.provider.create_post_draft(draft)
        return {
            "draft_id": saved.id,
            "draft_type": saved.draft_type,
            "content": saved.content,
            "created_at": saved.created_at.isoformat(),
            "status": "draft",
        }


class CreateMessageDraftTool:
    name, description, risk = "linkedin.create_message_draft", "Create an editable LinkedIn message draft without sending.", RiskLevel.LOCAL_WRITE
    parameters = {
        "type": "object",
        "properties": {
            "target_uri": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["target_uri", "content"],
        "additionalProperties": False,
    }

    def __init__(self, provider: LinkedInProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_id(arguments.get("target_uri"), "target_uri")
        _validate_text(arguments.get("content"), "content")
        if len(arguments["content"]) > 1500:
            raise ToolValidationError("content must be 1500 characters or fewer")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        draft = LinkedInDraft(
            id="", draft_type="message", content=arguments["content"],
            target_uri=arguments["target_uri"], created_at=_now(),
        )
        saved = await self.provider.create_message_draft(draft)
        return {
            "draft_id": saved.id,
            "draft_type": saved.draft_type,
            "target_uri": saved.target_uri,
            "content": saved.content,
            "created_at": saved.created_at.isoformat(),
            "status": "draft",
        }


class ImproveProfileTool:
    name, description, risk = "linkedin.improve_profile", "Generate improved profile content suggestions for local review.", RiskLevel.LOCAL_WRITE
    parameters = {
        "type": "object",
        "properties": {
            "profile_id": {"type": "string"},
            "headline": {"type": "string"},
            "summary": {"type": "string"},
            "skills": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["profile_id"],
        "additionalProperties": False,
    }

    def __init__(self, provider: LinkedInProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_id(arguments.get("profile_id"), "profile_id")
        headline = arguments.get("headline", "")
        if headline and len(headline) > 220:
            raise ToolValidationError("headline must be 220 characters or fewer")
        summary = arguments.get("summary", "")
        if summary and len(summary) > 2000:
            raise ToolValidationError("summary must be 2000 characters or fewer")
        _validate_skills(arguments.get("skills", ()), "skills")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        profile_id = arguments["profile_id"]
        try:
            profile = await self.provider.get_profile(profile_id)
            headline = profile.headline
            summary = profile.summary
            skills = list(profile.skills)
        except ValueError:
            headline = arguments.get("headline", "")
            summary = arguments.get("summary", "")
            skills = list(arguments.get("skills", []))
        improved_headline = headline if headline.strip() else "Experienced professional specializing in key areas."
        if not summary.strip():
            improved_summary = (
                "Results-driven professional with a track record of delivering value. "
                "Passionate about continuous improvement and collaboration."
            )
        else:
            improved_summary = summary
        suggested_skills = skills if len(skills) >= 3 else skills + ["Leadership", "Communication", "Problem Solving"]
        return {
            "profile_id": profile_id,
            "improved_headline": improved_headline,
            "improved_summary": improved_summary,
            "suggested_skills": list(dict.fromkeys(suggested_skills)),
            "requires_review": True,
        }


class PublishPostTool:
    name, description, risk = "linkedin.publish_post", "Publish a LinkedIn post through the official API. Requires explicit confirmation and authorized scopes.", RiskLevel.EXTERNAL
    parameters = {
        "type": "object",
        "properties": {
            "draft_id": {"type": "string"},
            "preview": {"type": "string"},
        },
        "required": ["draft_id"],
        "additionalProperties": False,
    }

    def __init__(self, provider: LinkedInProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_id(arguments.get("draft_id"), "draft_id")
        preview = arguments.get("preview", "")
        if preview and len(preview) > 3000:
            raise ToolValidationError("preview must be 3000 characters or fewer")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        scopes = self.provider.scopes
        if LinkedInScope.POSTS not in scopes:
            raise ToolPermissionError("LinkedIn publish permission is not granted. Authorize w_member_social scope to publish posts.")
        post = await self.provider.publish_post(arguments["draft_id"])
        return {
            "post_id": post.id,
            "content": post.content,
            "published_at": post.created_at.isoformat(),
            "status": "published",
        }


class SendMessageTool:
    name, description, risk = "linkedin.send_message", "Send a LinkedIn message through the official API. Requires explicit confirmation and authorized scopes.", RiskLevel.EXTERNAL
    parameters = {
        "type": "object",
        "properties": {
            "target_uri": {"type": "string"},
            "content": {"type": "string"},
            "preview": {"type": "string"},
        },
        "required": ["target_uri", "content"],
        "additionalProperties": False,
    }

    def __init__(self, provider: LinkedInProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_id(arguments.get("target_uri"), "target_uri")
        _validate_text(arguments.get("content"), "content")
        if len(arguments["content"]) > 1500:
            raise ToolValidationError("content must be 1500 characters or fewer")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        scopes = self.provider.scopes
        if LinkedInScope.MESSAGING not in scopes:
            raise ToolPermissionError("LinkedIn messaging permission is not granted. Authorize w_messaging scope to send messages.")
        message = LinkedInMessage(
            id="", from_uri="urn:li:person:current_user", to_uri=arguments["target_uri"],
            content=arguments["content"], sent_at=_now(),
        )
        sent = await self.provider.send_message(message)
        return {
            "message_id": sent.id,
            "to_uri": sent.to_uri,
            "content": sent.content,
            "sent_at": sent.sent_at.isoformat(),
            "status": "sent",
        }
