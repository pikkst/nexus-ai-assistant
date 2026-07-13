"""Prompt templates and conversation message construction for Nexus."""

from __future__ import annotations

from collections.abc import Sequence


def apply_persona(base_prompt: str, *, mode: str = "balanced", playfulness: float = 0.5, response_detail: float = 0.5) -> str:
    tone = (
        "Use warm, brief responses with light emoji sparingly."
        if playfulness > 0.7
        else "Keep responses factual and concise."
        if playfulness < 0.3
        else "Balance warmth and clarity."
    )
    detail = (
        "Provide short, focused answers."
        if response_detail < 0.33
        else "Offer thorough explanations with context."
        if response_detail > 0.66
        else "Provide clear, complete answers."
    )
    return (
        f"{base_prompt}\n\n"
        f"Persona mode: {mode}. {tone} {detail}\n"
        "Always preserve factual accuracy, cite uncertainty, and respect user control."
    )


DEFAULT_SYSTEM_PROMPT = (
    "You are Nexus, a helpful privacy-first local AI assistant. "
    "Answer clearly and concisely."
)


def build_messages(
    user_prompt: str,
    *,
    system_prompt: str | None = DEFAULT_SYSTEM_PROMPT,
    history: Sequence[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    """Build an Ollama-compatible ordered message list.

    A copy of every message is returned so callers cannot mutate the supplied
    conversation history through the request payload.
    """
    if not user_prompt.strip():
        raise ValueError("user_prompt must not be empty")

    messages: list[dict[str, str]] = []
    if system_prompt and system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt.strip()})

    for message in history or ():
        role = message.get("role", "")
        content = message.get("content", "")
        if role not in {"user", "assistant", "system"}:
            raise ValueError(f"unsupported message role: {role!r}")
        if not content.strip():
            raise ValueError("history message content must not be empty")
        messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_prompt.strip()})
    return messages
