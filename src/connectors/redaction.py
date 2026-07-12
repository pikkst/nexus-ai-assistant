"""Connector-safe recursive redaction for prompts, logs, memory, and errors."""

from __future__ import annotations

from typing import Any

from .models import OAuthTokens

SENSITIVE = ("token", "secret", "password", "authorization", "cookie", "credential")


def redact_secrets(value: Any, key: str = "") -> Any:
    if isinstance(value, OAuthTokens) or any(part in key.casefold() for part in SENSITIVE):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(name): redact_secrets(item, str(name)) for name, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_secrets(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return f"<{type(value).__name__}>"
