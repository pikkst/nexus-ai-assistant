from datetime import datetime, timezone

import pytest

from src.connectors.models import Account, Consent, OAuthTokens, Scope, TokenState


def test_provider_neutral_account_and_visible_consent() -> None:
    scope = Scope("mail.read", "Read message metadata", required=True)
    consent = Consent.grant((scope,))
    account = Account("a1", "example", "User", TokenState.ACTIVE, consent)
    assert account.provider == "example"
    assert account.consent.scopes[0].description == "Read message metadata"


def test_empty_consent_is_rejected() -> None:
    with pytest.raises(ValueError):
        Consent.grant(())


def test_tokens_are_redacted_from_text_representations() -> None:
    tokens = OAuthTokens("access-secret", "refresh-secret", datetime.now(timezone.utc))
    assert "secret" not in repr(tokens)
    assert str(tokens) == "OAuthTokens([REDACTED])"
    assert tokens.reveal() == ("access-secret", "refresh-secret")
