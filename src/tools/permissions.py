"""Risk-based permission decisions for Nexus tool calls."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .models import RiskLevel


class PermissionDecision(Enum):
    ALLOW = "allow"
    CONFIRM = "confirm"
    DENY = "deny"


@dataclass(frozen=True, slots=True)
class PermissionPolicy:
    """Default-safe local tool permission policy."""

    confirmation_levels: frozenset[RiskLevel] = field(
        default_factory=lambda: frozenset(
            {RiskLevel.LOCAL_WRITE, RiskLevel.EXTERNAL, RiskLevel.DESTRUCTIVE}
        )
    )
    denied_levels: frozenset[RiskLevel] = field(default_factory=frozenset)

    def decide(self, risk: RiskLevel, *, confirmed: bool = False) -> PermissionDecision:
        if risk in self.denied_levels:
            return PermissionDecision.DENY
        if risk in self.confirmation_levels and not confirmed:
            return PermissionDecision.CONFIRM
        return PermissionDecision.ALLOW
