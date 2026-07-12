import asyncio
from datetime import datetime, timedelta, timezone
import threading
import time

import pytest

from src.connectors.models import OAuthTokens
from src.connectors.vault import OSKeyringVault, VaultUnavailableError


class MemoryKeyring:
    def __init__(self):
        self.data = {}; self.active = 0; self.max_active = 0; self.lock = threading.Lock()
    def set_password(self, service, username, password):
        with self.lock:
            self.active += 1; self.max_active = max(self.max_active, self.active)
        time.sleep(.01); self.data[(service, username)] = password
        with self.lock: self.active -= 1
    def get_password(self, service, username): return self.data.get((service, username))
    def delete_password(self, service, username): self.data.pop((service, username), None)


def tokens(value="access"):
    return OAuthTokens(value, "refresh", datetime.now(timezone.utc) + timedelta(hours=1))


@pytest.mark.asyncio
async def test_keyring_roundtrip_and_delete():
    backend = MemoryKeyring(); vault = OSKeyringVault(backend)
    await vault.store("account", tokens())
    loaded = await vault.load("account")
    assert loaded.reveal() == ("access", "refresh")
    await vault.delete("account")
    assert await vault.load("account") is None


@pytest.mark.asyncio
async def test_same_account_access_is_serialized():
    backend = MemoryKeyring(); vault = OSKeyringVault(backend)
    await asyncio.gather(*(vault.store("same", tokens(str(i))) for i in range(5)))
    assert backend.max_active == 1


def test_missing_keyring_is_structured(monkeypatch):
    def missing(name): raise ImportError(name)
    monkeypatch.setattr("src.connectors.vault.importlib.import_module", missing)
    with pytest.raises(VaultUnavailableError, match="unavailable"):
        OSKeyringVault()
