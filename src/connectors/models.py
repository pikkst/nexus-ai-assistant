"""Provider-neutral connector identity and consent models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class TokenState(Enum):
    DISCONNECTED = "disconnected"
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    RECONNECT_REQUIRED = "reconnect_required"


@dataclass(frozen=True, slots=True)
class Scope:
    name: str
    description: str
    required: bool = False


@dataclass(frozen=True, slots=True)
class Consent:
    scopes: tuple[Scope, ...]
    granted_at: datetime

    @classmethod
    def grant(cls, scopes: tuple[Scope, ...]) -> Consent:
        if not scopes:
            raise ValueError("at least one visible scope is required")
        return cls(scopes, datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class Account:
    id: str
    provider: str
    display_name: str
    token_state: TokenState = TokenState.DISCONNECTED
    consent: Consent | None = None


class OAuthTokens:
    """Opaque token payload that never reveals secrets through repr or str."""

    __slots__ = ("_access_token", "_refresh_token", "expires_at")

    def __init__(self, access_token: str, refresh_token: str | None, expires_at: datetime) -> None:
        if not access_token:
            raise ValueError("access token is required")
        self._access_token = access_token
        self._refresh_token = refresh_token
        self.expires_at = expires_at

    def reveal(self) -> tuple[str, str | None]:
        """Reveal only at the vault/provider boundary."""
        return self._access_token, self._refresh_token

    def expired(self, *, now: datetime | None = None) -> bool:
        moment = now or datetime.now(timezone.utc)
        expiry = self.expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return expiry <= moment

    def __repr__(self) -> str: return "OAuthTokens([REDACTED])"
    __str__ = __repr__
