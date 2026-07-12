from datetime import datetime, timedelta, timezone
import pytest
from src.connectors.models import Account, OAuthTokens, Scope, TokenState
from src.connectors.oauth import OAuthError, OAuthService

class Vault:
    def __init__(self): self.values = {}
    async def store(self, account_id, tokens): self.values[account_id] = tokens
    async def load(self, account_id): return self.values.get(account_id)
    async def delete(self, account_id): self.values.pop(account_id, None)

class Provider:
    name = "mock"
    scopes = (Scope("profile", "Read profile", True), Scope("mail", "Read mail"))
    def __init__(self): self.refreshes = 0; self.revoked = []
    async def authorize(self, account, scopes): return make_tokens("connected", "refresh")
    async def refresh(self, refresh_token):
        self.refreshes += 1; return make_tokens("refreshed", refresh_token)
    async def revoke(self, access_token): self.revoked.append(access_token)

def make_tokens(access, refresh=None, expired=False):
    delta = timedelta(seconds=-1 if expired else 3600)
    return OAuthTokens(access, refresh, datetime.now(timezone.utc) + delta)

@pytest.mark.asyncio
async def test_connect_refresh_revoke_and_reconnect():
    provider, vault = Provider(), Vault(); service = OAuthService(provider, vault)
    account = Account("a", "mock", "User")
    account = await service.connect(account, ("profile",))
    assert account.token_state is TokenState.ACTIVE and account.consent.scopes[0].name == "profile"
    vault.values["a"] = make_tokens("old", "refresh", expired=True)
    account, access = await service.access_token(account)
    assert access == "refreshed" and provider.refreshes == 1
    account = await service.revoke(account)
    assert account.token_state is TokenState.REVOKED and provider.revoked == ["refreshed"]
    account = await service.reconnect(account, ("profile",))
    assert account.token_state is TokenState.ACTIVE

@pytest.mark.asyncio
async def test_missing_refresh_requires_reconnect():
    service, vault = OAuthService(Provider(), Vault()), Vault()
    service.vault = vault; vault.values["a"] = make_tokens("old", expired=True)
    account, access = await service.access_token(Account("a", "mock", "User"))
    assert not access and account.token_state is TokenState.RECONNECT_REQUIRED

def test_scopes_are_visible_and_minimized():
    service = OAuthService(Provider(), Vault())
    assert [item.description for item in service.visible_scopes()] == ["Read profile", "Read mail"]
    with pytest.raises(ValueError): service._validate_scopes(("mail",))
    with pytest.raises(ValueError): service._validate_scopes(("profile", "unknown"))

@pytest.mark.asyncio
async def test_concurrent_expiry_refreshes_only_once():
    provider, vault = Provider(), Vault(); service = OAuthService(provider, vault)
    vault.values["a"] = make_tokens("old", "refresh", expired=True)
    account = Account("a", "mock", "User")
    import asyncio
    results = await asyncio.gather(service.access_token(account), service.access_token(account))
    assert provider.refreshes == 1 and [item[1] for item in results] == ["refreshed", "refreshed"]

@pytest.mark.asyncio
async def test_provider_errors_do_not_expose_token_text():
    class Broken(Provider):
        async def refresh(self, refresh_token): raise RuntimeError(f"leaked {refresh_token}")
    vault = Vault(); vault.values["a"] = make_tokens("old", "top-secret", expired=True)
    with pytest.raises(OAuthError) as error:
        await OAuthService(Broken(), vault).access_token(Account("a", "mock", "User"))
    assert "secret" not in str(error.value)
