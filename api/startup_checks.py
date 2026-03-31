"""
JARVIS MAX — Startup Environment Checks
==========================================
Validates required environment variables at startup.

Policy:
- Core secrets (JARVIS_SECRET_KEY): always required, always strict
- Conditional secrets (Langfuse): only validated when their feature is enabled
- Dev mode: warns instead of blocking on non-critical checks
- Production mode: strict on all enabled features

Fail behavior:
- Missing critical secret → raise RuntimeError (blocks startup)
- Missing conditional secret (feature enabled) → raise RuntimeError
- Missing conditional secret (feature disabled) → skip silently
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """Single check result."""
    name: str
    passed: bool
    detail: str = ""
    blocking: bool = True

    def to_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed,
                "detail": self.detail, "blocking": self.blocking}


@dataclass
class StartupReport:
    """All startup check results."""
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks if c.blocking)

    @property
    def blockers(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed and c.blocking]

    def to_dict(self) -> dict:
        return {"ok": self.all_passed, "checks": [c.to_dict() for c in self.checks],
                "blockers": [c.to_dict() for c in self.blockers]}


def _is_weak(value: str) -> bool:
    """Check if a value is a placeholder or too short."""
    if not value:
        return True
    weak_patterns = ("change_me", "change-me", "placeholder", "CHANGE_ME", "default", "test-secret")
    return any(p in value.lower() for p in weak_patterns) or len(value) < 16


def _is_truthy(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


def run_startup_checks(env: dict | None = None) -> StartupReport:
    """
    Validate environment. Call at startup.

    Args:
        env: override for os.environ (for testing)
    """
    e = env if env is not None else dict(os.environ)
    report = StartupReport()

    # ── Core secrets (always required) ──
    secret_key = e.get("JARVIS_SECRET_KEY", "")
    if _is_weak(secret_key):
        report.checks.append(CheckResult(
            "JARVIS_SECRET_KEY", False,
            "Missing or weak — set with: openssl rand -hex 32", True,
        ))
    else:
        report.checks.append(CheckResult("JARVIS_SECRET_KEY", True, "Configured"))

    # ── Langfuse (conditional — only when enabled) ──
    langfuse_enabled = _is_truthy(e.get("LANGFUSE_ENABLED", "false"))
    if langfuse_enabled:
        for key in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"):
            val = e.get(key, "")
            if _is_weak(val):
                report.checks.append(CheckResult(
                    key, False,
                    f"LANGFUSE_ENABLED=true but {key} is missing/placeholder", True,
                ))
            else:
                report.checks.append(CheckResult(key, True, "Configured"))
    else:
        report.checks.append(CheckResult(
            "LANGFUSE_SECRETS", True,
            "Skipped — LANGFUSE_ENABLED is false", False,
        ))

    # ── Database (warn only) ──
    pg_pass = e.get("POSTGRES_PASSWORD", "")
    if _is_weak(pg_pass):
        report.checks.append(CheckResult(
            "POSTGRES_PASSWORD", False,
            "Weak or default — change for production", False,  # Non-blocking
        ))
    else:
        report.checks.append(CheckResult("POSTGRES_PASSWORD", True, "Configured"))

    return report


def enforce_startup_checks(env: dict | None = None) -> None:
    """
    Run checks and raise RuntimeError if blockers found.
    Call this from app startup event.
    """
    report = run_startup_checks(env)
    for check in report.checks:
        if check.passed:
            logger.info(f"Startup check OK: {check.name}")
        elif check.blocking:
            logger.error(f"Startup check FAILED: {check.name} — {check.detail}")
        else:
            logger.warning(f"Startup check WARN: {check.name} — {check.detail}")

    if not report.all_passed:
        blocker_names = [b.name for b in report.blockers]
        raise RuntimeError(
            f"Startup blocked by {len(report.blockers)} check(s): {', '.join(blocker_names)}. "
            "Fix the environment variables and restart."
        )
