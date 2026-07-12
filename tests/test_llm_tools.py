"""Ollama protocol tests for structured tool calls."""

from __future__ import annotations

import json

import httpx
import pytest

from src.llm import LLMClient, LLMError


@pytest.mark.asyncio
async def test_chat_sends_tools_and_parses_ollama_call() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "qwen3",
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "type": "function",
                            "function": {
                                "index": 0,
                                "name": "project.inspect",
                                "arguments": {},
                            },
                        }
                    ],
                },
                "done": True,
            },
        )

    http_client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://ollama.test"
    )
    client = LLMClient(http_client=http_client)
    tools = [{"type": "function", "function": {"name": "project.inspect"}}]

    result = await client.chat([{"role": "user", "content": "Inspect"}], tools)
    await http_client.aclose()

    assert captured["tools"] == tools
    assert captured["stream"] is False
    assert result.tool_calls[0].name == "project.inspect"
    assert result.tool_calls[0].arguments == {}


@pytest.mark.asyncio
async def test_chat_accepts_tool_result_messages() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["messages"][-1] == {
            "role": "tool",
            "tool_name": "project.inspect",
            "content": '{"success": true}',
        }
        return httpx.Response(
            200,
            json={"message": {"role": "assistant", "content": "Project inspected."}},
        )

    http_client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://ollama.test"
    )
    client = LLMClient(http_client=http_client)
    messages = [
        {"role": "user", "content": "Inspect"},
        {"role": "tool", "tool_name": "project.inspect", "content": '{"success": true}'},
    ]

    result = await client.chat(messages, [])
    await http_client.aclose()

    assert result.content == "Project inspected."


@pytest.mark.asyncio
async def test_malformed_tool_call_is_rejected() -> None:
    response = httpx.Response(
        200,
        json={"message": {"content": "", "tool_calls": [{"function": {"name": 42}}]}},
    )
    client_http = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: response), base_url="http://ollama.test"
    )
    client = LLMClient(http_client=client_http)

    with pytest.raises(LLMError, match="invalid tool call fields"):
        await client.chat([{"role": "user", "content": "test"}], [])
    await client_http.aclose()
