"""
executor/output_validator.py — Post-execution output validation.

Inspired by OpenHands' validation-aware execution.
Validates tool output before passing it back to the orchestrator.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

import structlog

log = structlog.get_logger("executor.validator")


class ValidationStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    SUSPICIOUS = "suspicious"
    UNVALIDATED = "unvalidated"


@dataclass
class ValidationResult:
    status: ValidationStatus
    issues: list[str]
    sanitized_output: str


def validate_output(
    output: str,
    tool_name: str = "",
    expected_format: str = "",
) -> ValidationResult:
    """
    Validate execution output.

    Checks:
    - Not empty
    - No sensitive data leakage patterns
    - No obvious error masking
    - Format expectations (if specified)
    """
    issues: list[str] = []

    if not output or not output.strip():
        return ValidationResult(
            status=ValidationStatus.INVALID,
            issues=["Empty output"],
            sanitized_output="",
        )

    sanitized = output

    # Check for leaked secrets (API keys, tokens)
    secret_patterns = [
        (r"sk-[a-zA-Z0-9]{20,}", "OpenAI API key pattern"),
        (r"ghp_[a-zA-Z0-9]{36}", "GitHub token pattern"),
        (r"AKIA[0-9A-Z]{16}", "AWS access key pattern"),
        (r"(?:password|passwd|pwd)\s*[:=]\s*\S+", "Password in output"),
    ]
    for pattern, desc in secret_patterns:
        if re.search(pattern, output, re.IGNORECASE):
            issues.append(f"Sensitive data leak: {desc}")
            sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.IGNORECASE)

    # Check for error masking (output says success but contains errors)
    if any(w in output.lower() for w in ["success", "completed", "done"]):
        if any(w in output.lower() for w in ["traceback", "exception", "error:"]):
            issues.append("Output claims success but contains error indicators")

    # Format validation
    if expected_format == "json":
        import json
        try:
            json.loads(output)
        except (json.JSONDecodeError, ValueError):
            issues.append("Expected JSON but output is not valid JSON")

    # Determine status
    has_secret = any("Sensitive" in i for i in issues)
    if has_secret:
        status = ValidationStatus.INVALID
    elif issues:
        status = ValidationStatus.SUSPICIOUS
    else:
        status = ValidationStatus.VALID

    log.debug("output_validated",
              status=status.value, tool=tool_name, issues=len(issues))

    return ValidationResult(
        status=status,
        issues=issues,
        sanitized_output=sanitized,
    )
