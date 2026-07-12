"""Bounded HTTP page-provider adapter."""

from __future__ import annotations

from html.parser import HTMLParser
from typing import Protocol

import httpx

from .models import ToolError
from .web_models import SourceType, WebPage, WebSource
from .web_security import redirect_url, validate_public_url


class RobotsPolicy(Protocol):
    async def allowed(self, url: str, user_agent: str) -> bool: ...


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(); self.parts: list[str] = []; self.title = ""
        self._in_title = False
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "title": self._in_title = True
    def handle_endtag(self, tag: str) -> None:
        if tag == "title": self._in_title = False
    def handle_data(self, data: str) -> None:
        value = data.strip()
        if value:
            self.parts.append(value)
            if self._in_title: self.title += value


class HttpPageProvider:
    def __init__(self, client: httpx.AsyncClient, *, robots: RobotsPolicy,
                 max_bytes: int = 1_000_000, max_redirects: int = 3,
                 user_agent: str = "NexusResearch/1.0") -> None:
        self.client, self.robots = client, robots
        self.max_bytes, self.max_redirects, self.user_agent = max_bytes, max_redirects, user_agent

    async def open(self, url: str) -> WebPage:
        current = validate_public_url(url)
        for redirect in range(self.max_redirects + 1):
            if not await self.robots.allowed(current, self.user_agent):
                raise ToolError("robots policy disallows retrieval", code="robots_denied")
            try:
                response = await self.client.send(
                    self.client.build_request("GET", current, headers={"User-Agent": self.user_agent}),
                    stream=True,
                )
            except httpx.TimeoutException as exc:
                raise ToolError("page retrieval timed out", code="timeout") from exc
            try:
                if response.is_redirect:
                    if redirect == self.max_redirects:
                        raise ToolError("redirect limit exceeded", code="redirect_limit")
                    current = redirect_url(current, response.headers.get("location", "")); continue
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                if content_type not in {"text/html", "text/plain"}:
                    raise ToolError("unsupported page format", code="unsupported_format")
                declared = int(response.headers.get("content-length", "0"))
                if declared > self.max_bytes:
                    raise ToolError("page exceeds content size limit", code="content_too_large")
                chunks = bytearray()
                async for chunk in response.aiter_bytes():
                    chunks.extend(chunk)
                    if len(chunks) > self.max_bytes:
                        raise ToolError("page exceeds content size limit", code="content_too_large")
                body = bytes(chunks)
            finally:
                await response.aclose()
            text, title = body.decode(response.encoding or "utf-8", errors="replace"), current
            if content_type == "text/html":
                parser = _TextExtractor(); parser.feed(text)
                text, title = "\n".join(parser.parts), parser.title or current
            source = WebSource.retrieved(current, title, source_type=SourceType.WEB_PAGE)
            return WebPage(source, text, content_type, len(body))
        raise ToolError("redirect limit exceeded", code="redirect_limit")
