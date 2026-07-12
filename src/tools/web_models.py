"""Provider-neutral provenance models for web research."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol


class SourceType(Enum):
    WEB_PAGE = "web_page"
    NEWS = "news"
    DOCUMENT = "document"


@dataclass(frozen=True, slots=True)
class WebSource:
    url: str
    title: str
    retrieved_at: datetime
    source_type: SourceType = SourceType.WEB_PAGE
    published_at: datetime | None = None
    excerpt: str = ""

    @classmethod
    def retrieved(
        cls, url: str, title: str, *, source_type: SourceType = SourceType.WEB_PAGE,
        published_at: datetime | None = None, excerpt: str = "",
    ) -> WebSource:
        return cls(url, title, datetime.now(timezone.utc), source_type, published_at, excerpt)


class SearchProvider(Protocol):
    """Adapter boundary implemented by web-search providers."""

    async def search(self, query: str, *, limit: int) -> list[WebSource]: ...


@dataclass(frozen=True, slots=True)
class WebPage:
    source: WebSource
    content: str
    content_type: str
    bytes_read: int


class PageProvider(Protocol):
    """Adapter boundary implemented by bounded page retrievers."""

    async def open(self, url: str) -> WebPage: ...


def unique_sources(sources: list[WebSource]) -> list[WebSource]:
    """Keep first-seen provenance and remove duplicate normalized URLs."""
    seen: set[str] = set()
    result: list[WebSource] = []
    for source in sources:
        key = source.url.rstrip("/").casefold()
        if key not in seen:
            seen.add(key)
            result.append(source)
    return result


def citation(source: WebSource, number: int) -> str:
    """Render a citation only from retained source metadata."""
    published = source.published_at.date().isoformat() if source.published_at else "date unknown"
    return f"[{number}] {source.title} ({published}) — {source.url}"
