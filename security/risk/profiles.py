"""
security/risk/profiles.py — Domain-specific risk profiles (Pass 17).

Extends the kernel's generic RiskLevel with configurable, per-capability
risk thresholds. The kernel engine handles kernel-level risk; this module
handles application-domain risk (business rules, capability-specific limits).

No imports from core/ or api/ (security layer is upstream of both).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ══════════════════════════════════════════════════════════════════════════════
# Sensitivity categories
# ══════════════════════════════════════════════════════════════════════════════

class SensitivityLevel(str, Enum):
    """Application-domain sensitivity — orthogonal to kernel RiskLevel."""
    PUBLIC     = "public"      # no restrictions
    INTERNAL   = "internal"    # standard access required
    RESTRICTED = "restricted"  # elevated privileges required
    CONFIDENTIAL = "confidential"  # explicit operator approval required


# ══════════════════════════════════════════════════════════════════════════════
# RiskProfile — per action_type or capability
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class RiskProfile:
    """
    Risk profile for a given action_type or capability domain.

    Used by the SecurityLayer to enrich kernel PolicyDecisions with
    domain-specific context.
    """
    action_type:  str
    sensitivity:  SensitivityLevel = SensitivityLevel.INTERNAL
    requires_2fa: bool = False         # two-factor confirmation required
    max_rate_per_minute: int = 60     # 0 = unlimited
    allowed_modes: list[str] = field(default_factory=lambda: ["auto", "manual"])
    notes: str = ""

    def is_rate_limited(self) -> bool:
        return self.max_rate_per_minute > 0

    def to_dict(self) -> dict:
        return {
            "action_type":         self.action_type,
            "sensitivity":         self.sensitivity.value,
            "requires_2fa":        self.requires_2fa,
            "max_rate_per_minute": self.max_rate_per_minute,
            "allowed_modes":       self.allowed_modes,
            "notes":               self.notes,
        }


# ══════════════════════════════════════════════════════════════════════════════
# Default profile registry
# ══════════════════════════════════════════════════════════════════════════════

_DEFAULT_PROFILES: list[RiskProfile] = [
    RiskProfile("mission_execution",   SensitivityLevel.INTERNAL,      max_rate_per_minute=30),
    RiskProfile("tool_invoke",         SensitivityLevel.INTERNAL,      max_rate_per_minute=60),
    RiskProfile("file_write",          SensitivityLevel.RESTRICTED,    max_rate_per_minute=20),
    RiskProfile("external_api",        SensitivityLevel.RESTRICTED,    max_rate_per_minute=20, notes="Tracks outbound API calls"),
    RiskProfile("payment",             SensitivityLevel.CONFIDENTIAL,  requires_2fa=True, max_rate_per_minute=5),
    RiskProfile("data_delete",         SensitivityLevel.CONFIDENTIAL,  requires_2fa=True, max_rate_per_minute=5),
    RiskProfile("deployment",          SensitivityLevel.CONFIDENTIAL,  requires_2fa=True, max_rate_per_minute=3),
    RiskProfile("webhook",             SensitivityLevel.RESTRICTED,    max_rate_per_minute=30),
    RiskProfile("automation",          SensitivityLevel.RESTRICTED,    max_rate_per_minute=10),
    RiskProfile("self_improvement",    SensitivityLevel.CONFIDENTIAL,  requires_2fa=True, max_rate_per_minute=2,
                notes="kernel.improvement.gate — always requires operator approval"),
    RiskProfile("cognitive",           SensitivityLevel.PUBLIC,        max_rate_per_minute=0),
]

_FALLBACK_PROFILE = RiskProfile("__default__", SensitivityLevel.INTERNAL)


class RiskProfileRegistry:
    """Registry mapping action_type → RiskProfile."""

    def __init__(self, profiles: Optional[list[RiskProfile]] = None) -> None:
        self._profiles: dict[str, RiskProfile] = {}
        for p in (profiles or _DEFAULT_PROFILES):
            self._profiles[p.action_type] = p

    def get(self, action_type: str) -> RiskProfile:
        return self._profiles.get(action_type, _FALLBACK_PROFILE)

    def register(self, profile: RiskProfile) -> None:
        self._profiles[profile.action_type] = profile

    def all_profiles(self) -> list[RiskProfile]:
        return list(self._profiles.values())

    def confidential_types(self) -> list[str]:
        return [
            k for k, v in self._profiles.items()
            if v.sensitivity == SensitivityLevel.CONFIDENTIAL
        ]


# Module-level singleton
_registry: Optional[RiskProfileRegistry] = None


def get_risk_registry() -> RiskProfileRegistry:
    global _registry
    if _registry is None:
        _registry = RiskProfileRegistry()
    return _registry
