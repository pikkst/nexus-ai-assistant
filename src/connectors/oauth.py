"""Provider-neutral OAuth lifecycle orchestration."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import Protocol

from .models import Account, Consent, OAuthTokens, Scope, TokenState
from .vault import CredentialVault


class OAuthProvider(Protocol):
    name: str
    scopes: tuple[Scope, ...]
    async def authorize(self, account: Account, scopes: tuple[str, ...]) -> OAuthTokens: ...
    async def refresh(self, refresh_token: str) -> OAuthTokens: ...
    async def revoke(self, access_token: str) -> None: ...


class OAuthError(RuntimeError):
    """Public authentication error that never includes provider secrets."""


class OAuthService:
    def __init__(self, provider: OAuthProvider, vault: CredentialVault) -> None:
        self.provider, self.vault = provider, vault
        self._locks: dict[str, asyncio.Lock] = {}

    def visible_scopes(self) -> tuple[Scope, ...]:
        return self.provider.scopes

    def _validate_scopes(self, names: tuple[str, ...]) -> tuple[Scope, ...]:
        available = {scope.name: scope for scope in self.provider.scopes}
        if not names or any(name not in available for name in names):
            raise ValueError("requested scopes must be visible provider scopes")
        missing = [scope.name for scope in available.values() if scope.required and scope.name not in names]
        if missing:
            raise ValueError("required scopes are missing")
        return tuple(available[name] for name in names)

    async def connect(self, account: Account, scopes: tuple[str, ...]) -> Account:
        selected = self._validate_scopes(scopes)
        async with self._locks.setdefault(account.id, asyncio.Lock()):
            try:
                tokens = await self.provider.authorize(account, scopes)
            except Exception:
                raise OAuthError("OAuth authorization failed") from None
            await self.vault.store(account.id, tokens)
        return replace(account, token_state=TokenState.ACTIVE, consent=Consent.grant(selected))

    async def access_token(self, account: Account) -> tuple[Account, str]:
        async with self._locks.setdefault(account.id, asyncio.Lock()):
            tokens = await self.vault.load(account.id)
            if tokens is None:
                return replace(account, token_state=TokenState.RECONNECT_REQUIRED), ""
            access, refresh = tokens.reveal()
            if tokens.expired():
                if not refresh:
                    return replace(account, token_state=TokenState.RECONNECT_REQUIRED), ""
                try:
                    tokens = await self.provider.refresh(refresh)
                except Exception:
                    raise OAuthError("OAuth token refresh failed") from None
                await self.vault.store(account.id, tokens)
                access, _ = tokens.reveal()
            return replace(account, token_state=TokenState.ACTIVE), access

    async def revoke(self, account: Account) -> Account:
        async with self._locks.setdefault(account.id, asyncio.Lock()):
            tokens = await self.vault.load(account.id)
            if tokens is not None:
                access, _ = tokens.reveal()
                try:
                    await self.provider.revoke(access)
                except Exception:
                    raise OAuthError("OAuth revocation failed") from None
                await self.vault.delete(account.id)
        return replace(account, token_state=TokenState.REVOKED)

    async def reconnect(self, account: Account, scopes: tuple[str, ...]) -> Account:
        return await self.connect(account, scopes)
