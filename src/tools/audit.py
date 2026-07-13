"""Privacy-conscious JSONL audit trail for tool invocations."""

from __future__ import annotations

import json
import re
import threading
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import RiskLevel, ToolRequest, utc_now

_SENSITIVE_PARTS = frozenset({
    "password", "token", "secret", "api_key", "authorization", "cookie",
    "body", "address", "email", "recipient", "snippet", "to", "cc",
    "from_address", "from", "bcc", "subject", "summary", "location",
    "description", "attendee", "text", "caption",
})


def _is_sensitive_key(key: str) -> bool:
    """Return True for keys that hold email-sensitive data.

    Uses exact key matching plus word-boundary token matching so that
    unrelated keys containing those substrings (e.g. ``protocol``, ``config``,
    ``format``) are not falsely redacted.
    """
    lowered = key.casefold()
    if lowered in _SENSITIVE_PARTS:
        return True
    return any(token in _SENSITIVE_PARTS for token in re.split(r"[^0-9a-z]+", lowered) if token)


def redact(value: Any, key: str = "") -> Any:
    """Recursively redact values whose key suggests sensitive content."""
    if _is_sensitive_key(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(item_key): redact(item, str(item_key)) for item_key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return f"<{type(value).__name__}>"


@dataclass(frozen=True, slots=True)
class AuditEntry:
    request_id: str
    tool_name: str
    risk: str
    status: str
    arguments: dict[str, Any]
    error_code: str | None
    created_at: str
    duration_ms: int


class ToolAuditLog:
    """Append-only local audit log that never stores tool output."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path).expanduser()
        self._lock = threading.Lock()

    def record(
        self,
        request: ToolRequest,
        risk: RiskLevel,
        *,
        status: str,
        started_at: datetime,
        error_code: str | None = None,
    ) -> AuditEntry:
        finished_at = utc_now()
        duration_ms = max(0, int((finished_at - started_at).total_seconds() * 1000))
        entry = AuditEntry(
            request_id=request.id,
            tool_name=request.tool_name,
            risk=risk.value,
            status=status,
            arguments=redact(request.arguments),
            error_code=error_code,
            created_at=finished_at.isoformat(),
            duration_ms=duration_ms,
        )
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
        return entry

    def entries(self) -> list[AuditEntry]:
        if not self.path.exists():
            return []
        with self._lock:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        return [AuditEntry(**json.loads(line)) for line in lines if line.strip()]
