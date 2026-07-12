"""Credential-vault boundary; implementations must use an OS-backed keyring."""

from __future__ import annotations

import asyncio
import importlib
import json
from datetime import datetime
from typing import Protocol

from .models import OAuthTokens


class VaultUnavailableError(RuntimeError):
    pass


class CredentialVault(Protocol):
    async def store(self, account_id: str, tokens: OAuthTokens) -> None: ...
    async def load(self, account_id: str) -> OAuthTokens | None: ...
    async def delete(self, account_id: str) -> None: ...


class KeyringBackend(Protocol):
    def set_password(self, service: str, username: str, password: str) -> None: ...
    def get_password(self, service: str, username: str) -> str | None: ...
    def delete_password(self, service: str, username: str) -> None: ...


class OSKeyringVault:
    """Store OAuth credentials in the active operating-system keyring."""

    def __init__(self, backend: KeyringBackend | None = None, *, service: str = "Nexus") -> None:
        if backend is None:
            try:
                backend = importlib.import_module("keyring")
            except ImportError as exc:
                raise VaultUnavailableError("OS keyring support is unavailable") from exc
        self.backend, self.service = backend, service
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock(self, account_id: str) -> asyncio.Lock:
        if not account_id or any(char in account_id for char in "\r\n\0"):
            raise ValueError("invalid account id")
        return self._locks.setdefault(account_id, asyncio.Lock())

    async def store(self, account_id: str, tokens: OAuthTokens) -> None:
        access, refresh = tokens.reveal()
        payload = json.dumps({"access": access, "refresh": refresh,
                              "expires_at": tokens.expires_at.isoformat()})
        async with self._lock(account_id):
            try:
                await asyncio.to_thread(self.backend.set_password, self.service, account_id, payload)
            except Exception as exc:
                raise VaultUnavailableError("OS keyring write failed") from exc

    async def load(self, account_id: str) -> OAuthTokens | None:
        async with self._lock(account_id):
            try:
                payload = await asyncio.to_thread(
                    self.backend.get_password, self.service, account_id)
            except Exception as exc:
                raise VaultUnavailableError("OS keyring read failed") from exc
        if payload is None:
            return None
        try:
            data = json.loads(payload)
            return OAuthTokens(data["access"], data.get("refresh"),
                               datetime.fromisoformat(data["expires_at"]))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise VaultUnavailableError("OS keyring credential is invalid") from exc

    async def delete(self, account_id: str) -> None:
        async with self._lock(account_id):
            try:
                await asyncio.to_thread(self.backend.delete_password, self.service, account_id)
            except Exception as exc:
                raise VaultUnavailableError("OS keyring delete failed") from exc
