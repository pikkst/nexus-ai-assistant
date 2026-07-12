"""Tests for local LLM prompt construction and backend behavior."""

from __future__ import annotations

import httpx
import pytest

from src.llm import LLMClient, LLMConfig, LLMTimeoutError, LLMUnavailableError, build_messages


def test_build_messages_includes_system_history_and_prompt() -> None:
    history = [
        {"role": "user", "content": "My name is Kai."},
        {"role": "assistant", "content": "Nice to meet you."},
    ]
    messages = build_messages("What is my name?", system_prompt="Be brief.", history=history)
    assert messages == [
        {"role": "system", "content": "Be brief."},
        *history,
        {"role": "user", "content": "What is my name?"},
    ]


def test_build_request_uses_configured_generation_options() -> None:
    client = LLMClient(LLMConfig(model="mistral", temperature=0.2, max_tokens=123))
    payload = client.build_request("Hello")
    assert payload["model"] == "mistral"
    assert payload["options"] == {"temperature": 0.2, "num_predict": 123}
    assert payload["stream"] is False


@pytest.mark.asyncio
async def test_generate_returns_structured_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        return httpx.Response(
            200,
            json={
                "model": "llama3.1",
                "message": {"role": "assistant", "content": "Tere!"},
                "done": True,
                "prompt_eval_count": 8,
                "eval_count": 2,
            },
        )

    http_client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://ollama.test"
    )
    client = LLMClient(http_client=http_client)
    result = await client.generate("Say hello")
    await http_client.aclose()
    assert result.content == "Tere!"
    assert result.prompt_tokens == 8
    assert result.completion_tokens == 2


@pytest.mark.asyncio
async def test_generate_maps_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow backend", request=request)

    http_client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://ollama.test"
    )
    client = LLMClient(http_client=http_client)
    with pytest.raises(LLMTimeoutError):
        await client.generate("Hello")
    await http_client.aclose()


@pytest.mark.asyncio
async def test_generate_maps_backend_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, request=request)

    http_client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://ollama.test"
    )
    client = LLMClient(http_client=http_client)
    with pytest.raises(LLMUnavailableError):
        await client.generate("Hello")
    await http_client.aclose()


@pytest.mark.asyncio
async def test_stream_yields_response_chunks() -> None:
    body = (
        b'{"message":{"content":"Ter"},"done":false}\n'
        b'{"message":{"content":"e!"},"done":true}\n'
    )
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=body))
    http_client = httpx.AsyncClient(transport=transport, base_url="http://ollama.test")
    client = LLMClient(http_client=http_client)
    chunks = [chunk async for chunk in client.stream("Hello")]
    await http_client.aclose()
    assert chunks == ["Ter", "e!"]
