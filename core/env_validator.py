"""
JARVIS MAX — Environment Validator
====================================
Validates the runtime environment for common issues:
- Python version compatibility
- Required vs optional imports
- requirements.txt completeness
- Optional dependency fail-open behavior
- Environment variable presence

Designed to run at startup or on-demand. Every check is fail-open:
a single failing check produces a WARNING, never crashes the process.

Usage:
    from core.env_validator import validate_environment, get_env_report
    report = validate_environment()
    print(report["summary"])
"""
from __future__ import annotations

import importlib
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import structlog
    log = structlog.get_logger(__name__)
except ImportError:
    import logging
    log = logging.getLogger(__name__)

REPO_ROOT = Path(os.environ.get("JARVIS_ROOT", os.getcwd()))

# Minimum supported Python version
MIN_PYTHON = (3, 10)


# ═══════════════════════════════════════════════════════════════
# STRUCTURES
# ═══════════════════════════════════════════════════════════════

@dataclass
class CheckResult:
    """Result of a single validation check."""
    name:     str
    passed:   bool
    severity: str = "info"  # info | warning | error
    detail:   str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "severity": self.severity,
            "detail": self.detail,
        }


@dataclass
class EnvReport:
    """Full environment validation report."""
    checks:   list[CheckResult] = field(default_factory=list)
    warnings: list[str]         = field(default_factory=list)
    errors:   list[str]         = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0

    @property
    def summary(self) -> str:
        ok = sum(1 for c in self.checks if c.passed)
        total = len(self.checks)
        status = "PASS" if self.passed else "FAIL"
        return (
            f"Environment: {status} ({ok}/{total} checks passed, "
            f"{len(self.warnings)} warnings, {len(self.errors)} errors)"
        )

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "summary": self.summary,
            "checks": [c.to_dict() for c in self.checks],
            "warnings": self.warnings,
            "errors": self.errors,
        }


# ═══════════════════════════════════════════════════════════════
# CHECKS
# ═══════════════════════════════════════════════════════════════

def check_python_version() -> CheckResult:
    """Verify Python version >= MIN_PYTHON."""
    version = sys.version_info[:2]
    ok = version >= MIN_PYTHON
    return CheckResult(
        name="python_version",
        passed=ok,
        severity="error" if not ok else "info",
        detail=f"Python {version[0]}.{version[1]} (min: {MIN_PYTHON[0]}.{MIN_PYTHON[1]})",
    )


# Required imports that MUST be available
_REQUIRED_MODULES = [
    "asyncio", "json", "os", "pathlib", "re", "time",
    "dataclasses", "enum", "typing", "logging",
]

# Optional imports that should degrade gracefully
_OPTIONAL_MODULES = {
    "structlog":     "Structured logging (falls back to stdlib logging)",
    "pydantic":      "Data validation (some features degraded without it)",
    "requests":      "HTTP client (web tools unavailable without it)",
    "langchain_core": "LangChain integration (agent framework)",
    "qdrant_client":  "Vector memory (falls back to local storage)",
    "redis":          "Cache layer (operates without cache)",
    "fastapi":        "API server",
    "uvicorn":        "ASGI server",
}


def check_required_imports() -> list[CheckResult]:
    """Verify required stdlib modules are importable."""
    results = []
    for mod in _REQUIRED_MODULES:
        try:
            importlib.import_module(mod)
            results.append(CheckResult(
                name=f"import:{mod}", passed=True,
                detail=f"{mod} available",
            ))
        except ImportError as e:
            results.append(CheckResult(
                name=f"import:{mod}", passed=False,
                severity="error",
                detail=f"{mod} MISSING: {e}",
            ))
    return results


def check_optional_imports() -> list[CheckResult]:
    """Check optional dependencies — warnings only, never errors."""
    results = []
    for mod, description in _OPTIONAL_MODULES.items():
        try:
            importlib.import_module(mod)
            results.append(CheckResult(
                name=f"optional:{mod}", passed=True,
                detail=f"{mod} available — {description}",
            ))
        except ImportError:
            results.append(CheckResult(
                name=f"optional:{mod}", passed=True,  # pass because optional
                severity="warning",
                detail=f"{mod} not installed — {description}",
            ))
    return results


def check_requirements_file() -> CheckResult:
    """Verify requirements.txt exists and is parseable."""
    req_path = REPO_ROOT / "requirements.txt"
    if not req_path.exists():
        return CheckResult(
            name="requirements.txt",
            passed=True,
            severity="warning",
            detail=f"requirements.txt not found at {req_path}",
        )
    try:
        content = req_path.read_text(encoding="utf-8")
        lines = [l.strip() for l in content.splitlines()
                 if l.strip() and not l.strip().startswith("#") and not l.strip().startswith("-")]
        return CheckResult(
            name="requirements.txt",
            passed=True,
            detail=f"{len(lines)} packages listed",
        )
    except Exception as e:
        return CheckResult(
            name="requirements.txt",
            passed=False,
            severity="warning",
            detail=f"Cannot read requirements.txt: {e}",
        )


def check_env_vars() -> list[CheckResult]:
    """Check expected environment variables (names only, not values)."""
    # Required for core operation
    required = ["JARVIS_ROOT"]
    # Optional but useful
    optional = [
        "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
        "QDRANT_URL", "REDIS_URL", "GITHUB_TOKEN",
    ]
    results = []
    for var in required:
        val = os.environ.get(var, "")
        results.append(CheckResult(
            name=f"env:{var}",
            passed=bool(val),
            severity="warning" if not val else "info",
            detail=f"{'SET' if val else 'MISSING'} (required)",
        ))
    for var in optional:
        val = os.environ.get(var, "")
        results.append(CheckResult(
            name=f"env:{var}",
            passed=True,  # optional never fails
            severity="info" if val else "warning",
            detail=f"{'SET' if val else 'NOT SET'} (optional)",
        ))
    return results


def check_fail_open_imports() -> list[CheckResult]:
    """
    Verify that key modules handle missing optional imports gracefully.
    
    Imports each module and checks it doesn't crash even when
    optional dependencies are missing.
    """
    # Modules that should import cleanly regardless of optional deps
    modules_to_check = [
        "core.tool_registry",
        "core.observability_helpers",
        "core.execution_policy",
        "core.policy_mode",
    ]
    results = []
    for mod_path in modules_to_check:
        try:
            importlib.import_module(mod_path)
            results.append(CheckResult(
                name=f"fail_open:{mod_path}",
                passed=True,
                detail=f"{mod_path} imports cleanly",
            ))
        except Exception as e:
            results.append(CheckResult(
                name=f"fail_open:{mod_path}",
                passed=False,
                severity="warning",
                detail=f"{mod_path} failed to import: {str(e)[:100]}",
            ))
    return results


# ═══════════════════════════════════════════════════════════════
# MAIN VALIDATOR
# ═══════════════════════════════════════════════════════════════

def validate_environment() -> EnvReport:
    """
    Run all environment validation checks.
    
    Returns an EnvReport with all checks, warnings, and errors.
    Never raises — always returns a report.
    """
    report = EnvReport()

    # Run each check category with try/except (fail-open)
    check_fns = [
        ("python_version", lambda: [check_python_version()]),
        ("required_imports", check_required_imports),
        ("optional_imports", check_optional_imports),
        ("requirements_file", lambda: [check_requirements_file()]),
        ("env_vars", check_env_vars),
        ("fail_open_imports", check_fail_open_imports),
    ]

    for name, fn in check_fns:
        try:
            checks = fn()
            for c in checks:
                report.checks.append(c)
                if c.severity == "warning" and not c.passed:
                    report.warnings.append(f"{c.name}: {c.detail}")
                elif c.severity == "warning" and c.passed and "not installed" in c.detail:
                    report.warnings.append(f"{c.name}: {c.detail}")
                elif c.severity == "error" and not c.passed:
                    report.errors.append(f"{c.name}: {c.detail}")
        except Exception as e:
            report.checks.append(CheckResult(
                name=name, passed=False, severity="warning",
                detail=f"Check failed: {str(e)[:200]}",
            ))
            report.warnings.append(f"{name}: check itself failed — {str(e)[:100]}")

    try:
        log.info("env_validated", summary=report.summary,
                 warnings=len(report.warnings), errors=len(report.errors))
    except Exception:
        pass

    return report


def get_env_report() -> dict:
    """Convenience function: run validation and return dict."""
    return validate_environment().to_dict()
