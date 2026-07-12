"""Asynchronous local LLM client with Ollama chat support."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from typing import Any

import httpx

from .prompts import DEFAULT_SYSTEM_PROMPT, build_messages
from .tool_types import LLMToolCall


class LLMError(RuntimeError):
    """Base exception raised by the LLM layer."""


class LLMUnavailableError(LLMError):
    """Raised when the configured model backend cannot be reached."""


class LLMTimeoutError(LLMError):
    """Raised when the configured model backend times out."""


@dataclass(frozen=True)
class LLMConfig:
    """Configuration for a local Ollama-compatible backend."""

    base_url: str = "http://localhost:11434"
    model: str = "llama3.1"
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: float = 60.0
    system_prompt: str = DEFAULT_SYSTEM_PROMPT

    def __post_init__(self) -> None:
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be greater than zero")
        if self.timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        if not self.model.strip():
            raise ValueError("model must not be empty")


@dataclass(frozen=True)
class LLMResponse:
    """Structured response returned by the language model."""

    content: str
    model: str
    done: bool = True
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    tool_calls: tuple[LLMToolCall, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


class LLMClient:
    """Async client for Ollama's ``/api/chat`` endpoint."""

    def __init__(
        self,
        config: LLMConfig | None = None,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config or LLMConfig()
        self._client = http_client or httpx.AsyncClient(
            base_url=self.config.base_url.rstrip("/"), timeout=self.config.timeout
        )
        self._owns_client = http_client is None

    def build_request(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        history: Sequence[dict[str, str]] | None = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        """Construct the backend payload without performing network I/O."""
        return {
            "model": self.config.model,
            "messages": build_messages(
                prompt,
                system_prompt=self.config.system_prompt if system_prompt is None else system_prompt,
                history=history,
            ),
            "stream": stream,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        history: Sequence[dict[str, str]] | None = None,
    ) -> LLMResponse:
        """Generate one complete assistant response asynchronously."""
        payload = self.build_request(
            prompt, system_prompt=system_prompt, history=history, stream=False
        )
        try:
            response = await self._client.post("/api/chat", json=payload)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("LLM backend request timed out") from exc
        except (httpx.ConnectError, httpx.NetworkError, httpx.HTTPStatusError) as exc:
            raise LLMUnavailableError(f"LLM backend is unavailable: {exc}") from exc

        data = response.json()
        return self._parse_response(data)

    async def chat(
        self,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict[str, Any]],
    ) -> LLMResponse:
        """Send a complete Ollama tool-capable conversation."""
        payload = {
            "model": self.config.model,
            "messages": [dict(message) for message in messages],
            "tools": [dict(tool) for tool in tools],
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }
        try:
            response = await self._client.post("/api/chat", json=payload)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("LLM backend request timed out") from exc
        except (httpx.ConnectError, httpx.NetworkError, httpx.HTTPStatusError) as exc:
            raise LLMUnavailableError(f"LLM backend is unavailable: {exc}") from exc
        return self._parse_response(response.json())

    async def stream(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        history: Sequence[dict[str, str]] | None = None,
    ) -> AsyncIterator[str]:
        """Yield text chunks from an Ollama newline-delimited JSON stream."""
        payload = self.build_request(
            prompt, system_prompt=system_prompt, history=history, stream=True
        )
        try:
            async with self._client.stream("POST", "/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("LLM backend stream timed out") from exc
        except (httpx.ConnectError, httpx.NetworkError, httpx.HTTPStatusError) as exc:
            raise LLMUnavailableError(f"LLM backend is unavailable: {exc}") from exc

    async def close(self) -> None:
        """Close the internally managed HTTP client."""
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "LLMClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    def _parse_response(self, data: dict[str, Any]) -> LLMResponse:
        message = data.get("message")
        if not isinstance(message, dict):
            raise LLMError("LLM backend returned an invalid response")
        content = message.get("content", "")
        if not isinstance(content, str):
            raise LLMError("LLM backend returned invalid message content")
        tool_calls = self._parse_tool_calls(message.get("tool_calls", []))
        if not content and not tool_calls:
            raise LLMError("LLM backend returned an empty response")
        return LLMResponse(
            content=content,
            model=str(data.get("model", self.config.model)),
            done=bool(data.get("done", True)),
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=data.get("eval_count"),
            tool_calls=tool_calls,
            metadata={key: value for key, value in data.items() if key != "message"},
        )

    def _parse_tool_calls(self, values: Any) -> tuple[LLMToolCall, ...]:
        if not isinstance(values, list):
            raise LLMError("LLM backend returned invalid tool calls")
        parsed = []
        for position, value in enumerate(values):
            function = value.get("function") if isinstance(value, dict) else None
            if not isinstance(function, dict):
                raise LLMError("LLM backend returned an invalid tool call")
            name = function.get("name")
            arguments = function.get("arguments", {})
            if not isinstance(name, str) or not name or not isinstance(arguments, dict):
                raise LLMError("LLM backend returned invalid tool call fields")
            parsed.append(LLMToolCall(name, dict(arguments), int(function.get("index", position))))
        return tuple(parsed)
