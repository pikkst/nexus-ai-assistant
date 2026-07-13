"""LinkedIn-specific typed models and provider protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol, Any


class LinkedInScope(str, Enum):
    PROFILE = "r_liteprofile"
    EMAIL = "r_emailaddress"
    POSTS = "w_member_social"
    MESSAGING = "w_messaging"
    ORGANIZATION = "r_organization_social"


@dataclass(frozen=True, slots=True)
class LinkedInProfile:
    id: str
    first_name: str = ""
    last_name: str = ""
    headline: str = ""
    summary: str = ""
    industry: str = ""
    profile_url: str = ""
    skills: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("profile id is required")


@dataclass(frozen=True, slots=True)
class LinkedInPost:
    id: str
    content: str
    author_id: str
    created_at: datetime
    visibility: str = "PUBLIC"
    engagement: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("post id is required")
        if not self.content.strip():
            raise ValueError("post content is required")
        if not self.author_id:
            raise ValueError("author_id is required")
        if self.created_at.tzinfo is None:
            raise ValueError("post created_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class LinkedInMessage:
    id: str
    from_uri: str
    to_uri: str
    content: str
    sent_at: datetime

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("message id is required")
        if not self.from_uri:
            raise ValueError("from_uri is required")
        if not self.to_uri:
            raise ValueError("to_uri is required")
        if not self.content.strip():
            raise ValueError("message content is required")
        if self.sent_at.tzinfo is None:
            raise ValueError("message sent_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class LinkedInCompany:
    id: str
    name: str
    industry: str = ""
    size: str = ""
    description: str = ""
    website: str = ""
    logo_url: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("company id is required")
        if not self.name:
            raise ValueError("company name is required")


@dataclass(frozen=True, slots=True)
class LinkedInDraft:
    id: str = ""
    draft_type: str = "post"
    content: str = ""
    target_uri: str = ""
    company_id: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.draft_type not in {"post", "message", "profile_update", "company_post"}:
            raise ValueError("draft_type must be post, message, profile_update, or company_post")
        if self.draft_type == "message" and not self.target_uri:
            raise ValueError("message draft requires target_uri")
        if self.draft_type == "company_post" and not self.company_id:
            raise ValueError("company_post draft requires company_id")
        if not self.content.strip():
            raise ValueError("draft content is required")


class LinkedInProvider(Protocol):
    """Official LinkedIn API provider protocol."""

    @property
    def scopes(self) -> tuple[LinkedInScope, ...]: ...

    async def get_profile(self, profile_id: str) -> LinkedInProfile: ...
    async def get_post(self, post_id: str) -> LinkedInPost: ...
    async def create_post_draft(self, draft: LinkedInDraft) -> LinkedInDraft: ...
    async def create_message_draft(self, draft: LinkedInDraft) -> LinkedInDraft: ...
    async def publish_post(self, draft_id: str) -> LinkedInPost: ...
    async def send_message(self, message: LinkedInMessage) -> LinkedInMessage: ...
    async def get_company(self, company_id: str) -> LinkedInCompany: ...
