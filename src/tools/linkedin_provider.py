"""Mock LinkedIn provider for testing and offline development."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from .linkedin_models import (
    LinkedInCompany,
    LinkedInDraft,
    LinkedInMessage,
    LinkedInPost,
    LinkedInProfile,
    LinkedInScope,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MockLinkedInProvider:
    """In-memory LinkedIn API simulator with authorization and draft support."""

    def __init__(self) -> None:
        self._profiles: dict[str, LinkedInProfile] = {}
        self._posts: dict[str, LinkedInPost] = {}
        self._messages: dict[str, LinkedInMessage] = {}
        self._companies: dict[str, LinkedInCompany] = {}
        self._drafts: dict[str, LinkedInDraft] = {}
        self._counter = 0
        self._scopes: tuple[LinkedInScope, ...] = ()

    def _next_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{uuid.uuid4().hex[:8]}_{self._counter}"

    def configure_scopes(self, scopes: tuple[LinkedInScope, ...]) -> None:
        self._scopes = scopes

    @property
    def scopes(self) -> tuple[LinkedInScope, ...]:
        return self._scopes

    def add_profile(self, profile: LinkedInProfile) -> None:
        self._profiles[profile.id] = profile

    def add_post(self, post: LinkedInPost) -> None:
        self._posts[post.id] = post

    def add_company(self, company: LinkedInCompany) -> None:
        self._companies[company.id] = company

    async def get_profile(self, profile_id: str) -> LinkedInProfile:
        profile = self._profiles.get(profile_id)
        if profile is None:
            raise ValueError(f"profile {profile_id} not found")
        return profile

    async def get_post(self, post_id: str) -> LinkedInPost:
        post = self._posts.get(post_id)
        if post is None:
            raise ValueError(f"post {post_id} not found")
        return post

    async def get_company(self, company_id: str) -> LinkedInCompany:
        company = self._companies.get(company_id)
        if company is None:
            raise ValueError(f"company {company_id} not found")
        return company

    async def create_post_draft(self, draft: LinkedInDraft) -> LinkedInDraft:
        if draft.draft_type != "post":
            raise ValueError("create_post_draft only accepts post drafts")
        draft_id = self._next_id("draft_post")
        saved = LinkedInDraft(
            id=draft_id, draft_type=draft.draft_type, content=draft.content,
            created_at=_now(),
        )
        self._drafts[draft_id] = saved
        return saved

    async def create_message_draft(self, draft: LinkedInDraft) -> LinkedInDraft:
        if draft.draft_type != "message":
            raise ValueError("create_message_draft only accepts message drafts")
        draft_id = self._next_id("draft_msg")
        saved = LinkedInDraft(
            id=draft_id, draft_type=draft.draft_type, content=draft.content,
            target_uri=draft.target_uri, created_at=_now(),
        )
        self._drafts[draft_id] = saved
        return saved

    async def publish_post(self, draft_id: str) -> LinkedInPost:
        draft = self._drafts.get(draft_id)
        if draft is None:
            raise ValueError(f"draft {draft_id} not found")
        post_id = self._next_id("post")
        post = LinkedInPost(
            id=post_id, content=draft.content, author_id="current_user",
            created_at=_now(),
        )
        self._posts[post_id] = post
        return post

    async def send_message(self, message: LinkedInMessage) -> LinkedInMessage:
        message_id = self._next_id("msg")
        sent = LinkedInMessage(
            id=message_id, from_uri=message.from_uri, to_uri=message.to_uri,
            content=message.content, sent_at=_now(),
        )
        self._messages[message_id] = sent
        return sent
