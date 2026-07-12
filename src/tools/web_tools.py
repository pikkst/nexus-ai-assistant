"""Permissioned web search, retrieval, and research organization tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .development_files import WriteTextTool
from .models import RiskLevel, ToolValidationError
from .snapshots import SnapshotStore
from .web_models import PageProvider, SearchProvider, WebSource, unique_sources
from .web_security import validate_public_url


def source_dict(source: WebSource) -> dict[str, Any]:
    return {"url": source.url, "title": source.title,
            "published_at": source.published_at.isoformat() if source.published_at else None,
            "retrieved_at": source.retrieved_at.isoformat(), "source_type": source.source_type.value,
            "excerpt": source.excerpt}


class WebSearchTool:
    name, description, risk = "web.search", "Search the web through a configured provider.", RiskLevel.EXTERNAL
    parameters = {"type": "object", "properties": {"query": {"type": "string"},
        "limit": {"type": "integer", "minimum": 1, "maximum": 10}}, "required": ["query"],
        "additionalProperties": False}
    def __init__(self, provider: SearchProvider, *, max_results: int = 10) -> None:
        self.provider, self.max_results = provider, max_results
    def validate(self, arguments: dict[str, Any]) -> None:
        if not isinstance(arguments.get("query"), str) or not arguments["query"].strip():
            raise ToolValidationError("query must be a non-empty string")
        limit = arguments.get("limit", 5)
        if not isinstance(limit, int) or not 1 <= limit <= self.max_results:
            raise ToolValidationError(f"limit must be between 1 and {self.max_results}")
    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        results = unique_sources(await self.provider.search(arguments["query"], limit=arguments.get("limit", 5)))
        return {"query": arguments["query"], "sources": [source_dict(item) for item in results]}


class OpenPageTool:
    name, description, risk = "web.open_page", "Retrieve and extract a bounded public web page.", RiskLevel.EXTERNAL
    parameters = {"type": "object", "properties": {"url": {"type": "string"}},
                  "required": ["url"], "additionalProperties": False}
    def __init__(self, provider: PageProvider) -> None: self.provider = provider
    def validate(self, arguments: dict[str, Any]) -> None: validate_public_url(arguments.get("url"))
    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        page = await self.provider.open(arguments["url"])
        return {"source": source_dict(page.source), "content": page.content,
                "content_type": page.content_type, "bytes_read": page.bytes_read}


class CompareSourcesTool:
    name, description, risk = "research.compare_sources", "Organize claims with citations to supplied sources.", RiskLevel.READ_ONLY
    parameters = {"type": "object", "properties": {"claims": {"type": "array"},
        "sources": {"type": "array"}}, "required": ["claims", "sources"], "additionalProperties": False}
    def validate(self, arguments: dict[str, Any]) -> None:
        sources, claims = arguments.get("sources"), arguments.get("claims")
        if not isinstance(sources, list) or not sources or not isinstance(claims, list):
            raise ToolValidationError("non-empty sources and claims arrays are required")
        urls = {item.get("url") for item in sources if isinstance(item, dict)}
        for claim in claims:
            if (not isinstance(claim, dict) or not isinstance(claim.get("text"), str)
                    or claim.get("source_url") not in urls):
                raise ToolValidationError("every claim must reference a supplied source URL")
    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        sources = {item["url"]: item for item in arguments["sources"]}
        ordered = list(sources.values()); numbers = {item["url"]: i + 1 for i, item in enumerate(ordered)}
        claims = [{"text": item["text"], "citation": numbers[item["source_url"]]}
                  for item in arguments["claims"]]
        refs = [f"[{i}] {item['title']} — {item['url']}" for i, item in enumerate(ordered, 1)]
        return {"claims": claims, "references": refs}


class SaveResearchNoteTool(WriteTextTool):
    name, description = "research.save_note", "Save a research note inside the configured notes root."
    def __init__(self, root: Path | str, snapshots: SnapshotStore) -> None: super().__init__(root, snapshots)
