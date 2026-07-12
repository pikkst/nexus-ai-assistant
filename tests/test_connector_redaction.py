from datetime import datetime, timezone
from src.connectors.models import OAuthTokens
from src.connectors.redaction import redact_secrets

def test_recursive_redaction_covers_tokens_and_credentials():
    tokens = OAuthTokens("access-secret", "refresh-secret", datetime.now(timezone.utc))
    value = {"access_token": "a", "nested": [{"credential": "b"}], "object": tokens,
             "safe": "visible"}
    redacted = redact_secrets(value)
    assert redacted == {"access_token": "[REDACTED]", "nested": [{"credential": "[REDACTED]"}],
                        "object": "[REDACTED]", "safe": "visible"}
    assert "secret" not in str(redacted)
