"""URL and response boundaries for web research."""

from __future__ import annotations

import ipaddress
from urllib.parse import urljoin, urlparse

from .models import ToolValidationError


def validate_public_url(url: str) -> str:
    if not isinstance(url, str) or not url:
        raise ToolValidationError("url must be a non-empty string")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username:
        raise ToolValidationError("only public HTTP(S) URLs are supported")
    host = parsed.hostname.casefold().rstrip(".")
    if host == "localhost" or host.endswith(".localhost"):
        raise ToolValidationError("local URLs are not allowed")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return url
    if not address.is_global:
        raise ToolValidationError("private or reserved addresses are not allowed")
    return url


def redirect_url(current: str, location: str) -> str:
    return validate_public_url(urljoin(current, location))
