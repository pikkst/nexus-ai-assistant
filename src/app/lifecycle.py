"""Safe lifecycle helpers for optional Nexus services."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def start_optional(name: str, service: object | None, method: str) -> bool:
    """Start one optional service without taking down the core runtime."""
    if service is None:
        return False
    try:
        await getattr(service, method)()
        return True
    except Exception:
        logger.exception("Optional %s startup failed; continuing", name)
        return False


async def stop_optional(name: str, service: object | None, method: str) -> None:
    """Stop one service while allowing remaining cleanup to continue."""
    if service is None:
        return
    try:
        await getattr(service, method)()
    except Exception:
        logger.exception("Failed to stop %s", name)
