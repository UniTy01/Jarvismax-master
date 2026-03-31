"""
JARVIS MAX — Execution Guard

Validates execution outcomes and prevents false-DONE states.
Catches partial failures, broken code, and inconsistent results.

Functions:
  validate_step_output()   - Check if a step really succeeded
  validate_code_change()   - Verify code edit was applied correctly
  detect_false_done()      - Catch missions claiming DONE but incomplete
  should_replan()          - Decide if error warrants replanning vs retry
  classify_execution_error() - Categorize error for decision-making
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger()


# ── Error Classification ──────────────────────────────────────────

@dataclass
class ErrorClassification:
    """Structured error classification for decision-making."""
    category: str          # syntax, runtime, test_failure, import, timeout, resource, logic, unknown
    severity: str          # low, medium, high, critical
    retryable: bool
    replannable: bool      # Can be fixed with a different approach
    message: str
    suggested_action: str  # retry, replan, skip, escalate, abort


def classify_execution_error(error: str, context: str = "") -> ErrorClassification:
    """
    Classify an error to determine the best recovery action.

    Categories and their typical actions:
    - syntax:        replan (code needs fixing)
    - runtime:       retry/replan depending on type
    - test_failure:  replan (approach needs adjustment)
    - import:        replan (wrong dependency or module)
    - timeout:       retry with longer timeout
    - resource:      retry later
    - logic:         replan (fundamental approach wrong)
    - permission:    escalate
    - unknown:       retry once, then escalate
    """
    error_lower = error.lower()

    # Syntax errors — code needs fixing
    if any(k in error_lower for k in ["syntaxerror", "indentation", "unexpected indent",
                                       "invalid syntax", "unexpected token"]):
        return ErrorClassification(
            category="syntax", severity="medium", retryable=False, replannable=True,
            message=error[:200],
            suggested_action="replan — fix syntax in generated code",
        )

    # Test failures — approach may need adjustment
    if any(k in error_lower for k in ["assertionerror", "assert ", "test failed",
                                       "tests failed", "failed tests"]):
        return ErrorClassification(
            category="test_failure", severity="medium", retryable=False, replannable=True,
            message=error[:200],
            suggested_action="replan — adjust code to pass tests",
        )

    # Import errors — wrong module or missing dependency
    if any(k in error_lower for k in ["importerror", "modulenotfounderror", "no module named"]):
        return ErrorClassification(
            category="import", severity="medium", retryable=False, replannable=True,
            message=error[:200],
            suggested_action="replan — check import paths and dependencies",
        )

    # Timeout — transient, retry with adjustment
    if any(k in error_lower for k in ["timeout", "timed out", "deadline exceeded"]):
        return ErrorClassification(
            category="timeout", severity="low", retryable=True, replannable=False,
            message=error[:200],
            suggested_action="retry with increased timeout",
        )

    # Resource errors — transient
    if any(k in error_lower for k in ["resource", "memory", "disk full", "no space",
                                       "too many open files"]):
        return ErrorClassification(
            category="resource", severity="high", retryable=True, replannable=False,
            message=error[:200],
            suggested_action="retry after resource cleanup",
        )

    # Permission errors — need escalation
    if any(k in error_lower for k in ["permission", "denied", "forbidden", "unauthorized"]):
        return ErrorClassification(
            category="permission", severity="high", retryable=False, replannable=False,
            message=error[:200],
            suggested_action="escalate — insufficient permissions",
        )

    # Runtime errors — depends on specifics
    if any(k in error_lower for k in ["runtimeerror", "typeerror", "valueerror",
                                       "keyerror", "attributeerror"]):
        return ErrorClassification(
            category="runtime", severity="medium", retryable=False, replannable=True,
            message=error[:200],
            suggested_action="replan — runtime error suggests wrong approach",
        )

    # Unknown — conservative
    return ErrorClassification(
        category="unknown", severity="medium", retryable=True, replannable=True,
        message=error[:200],
        suggested_action="retry once, then replan if still failing",
    )


# ── Output Validation ────────────────────────────────────────────

def validate_step_output(step_name: str, output: str,
                         expected_patterns: list[str] | None = None) -> tuple[bool, str]:
    """
    Validate that a step's output indicates real success.

    Returns (is_valid, reason).

    Catches:
    - Empty output claiming success
    - Error messages in "successful" output
    - Missing expected patterns
    """
    if not output or not output.strip():
        return False, "Empty output — step may not have executed"

    output_lower = output.lower()

    # Check for error signatures in "successful" output
    error_signatures = [
        "traceback (most recent call last)",
        "error:", "exception:", "failed:",
        "syntaxerror", "importerror", "nameerror",
        "fatal:", "panic:", "segfault",
    ]
    for sig in error_signatures:
        if sig in output_lower:
            # But some errors are expected in test output
            if "test" in step_name.lower() and "failed" in sig:
                continue
            return False, f"Error signature found in output: '{sig}'"

    # Check expected patterns if provided
    if expected_patterns:
        missing = []
        for pattern in expected_patterns:
            if not re.search(pattern, output, re.IGNORECASE):
                missing.append(pattern)
        if missing:
            return False, f"Missing expected patterns: {missing}"

    return True, "Output looks valid"


def validate_code_change(file_path: str, expected_content: str | None = None,
                         old_content: str | None = None) -> tuple[bool, str]:
    """
    Verify a code edit was actually applied correctly.

    Checks:
    - File exists and is readable
    - Content was actually modified (if old_content provided)
    - Expected content is present (if provided)
    - No syntax errors in Python files
    """
    path = Path(file_path)

    if not path.exists():
        return False, f"File not found: {file_path}"

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return False, f"Cannot read file: {e}"

    if not content.strip():
        return False, "File is empty after edit"

    # Check content was actually changed
    if old_content is not None and content == old_content:
        return False, "File content unchanged — edit may not have been applied"

    # Check expected content is present
    if expected_content is not None and expected_content not in content:
        return False, "Expected content not found in file"

    # Syntax check for Python files
    if file_path.endswith(".py"):
        try:
            compile(content, file_path, "exec")
        except SyntaxError as e:
            return False, f"Python syntax error after edit: {e}"

    return True, "Code change verified"


# ── False-DONE Detection ─────────────────────────────────────────

def detect_false_done(mission_result: dict) -> tuple[bool, str]:
    """
    Check if a mission claiming DONE is actually incomplete.

    Returns (is_false_done, reason).

    Catches:
    - Plan had N steps but only M completed (M < N)
    - Test suite wasn't run after code changes
    - Files modified but no validation step
    - Error count > 0 but status is DONE
    """
    status = mission_result.get("status", "")
    if status not in ("DONE", "COMPLETED", "SUCCEEDED"):
        return False, "Not claiming done"

    # Check step completion
    total_steps = mission_result.get("total_steps", 0)
    completed_steps = mission_result.get("completed_steps", 0)
    if total_steps > 0 and completed_steps < total_steps:
        return True, f"Only {completed_steps}/{total_steps} steps completed"

    # Check for unresolved errors
    error_count = mission_result.get("error_count", 0)
    if error_count > 0:
        return True, f"{error_count} errors recorded but mission claims DONE"

    # Check if code was modified but no tests were run
    files_modified = mission_result.get("files_modified", [])
    steps = mission_result.get("steps", [])
    has_code_changes = any(f.endswith(".py") for f in files_modified)
    has_test_step = any("test" in s.get("name", "").lower() for s in steps)
    if has_code_changes and not has_test_step:
        return True, "Code modified but no test validation step"

    return False, "Mission completion looks valid"


# ── Replan Decision ──────────────────────────────────────────────

@dataclass
class ReplanDecision:
    """Whether and how to replan after a failure."""
    should_replan: bool
    reason: str
    strategy: str = ""       # retry_same, modify_approach, simplify, decompose, escalate
    failed_step: str = ""
    error_category: str = ""
    confidence: float = 0.5


def should_replan(error: str, step_name: str, attempt: int,
                  max_attempts: int = 3,
                  previous_errors: list[str] | None = None) -> ReplanDecision:
    """
    Decide if an error warrants replanning vs simple retry.

    Decision tree:
    1. Same error repeated 2+ times → replan (different approach needed)
    2. Syntax/import error → replan (code needs different generation)
    3. Test failure → replan (approach needs adjustment)
    4. Timeout on first try → retry
    5. Unknown error, first try → retry
    6. Max attempts reached → escalate
    """
    ec = classify_execution_error(error)
    prev = previous_errors or []

    # Check for repeated identical errors
    if len(prev) >= 2:
        recent = prev[-2:]
        if all(e[:100] == error[:100] for e in recent):
            return ReplanDecision(
                should_replan=True,
                reason=f"Same error repeated {len(recent)+1} times — need different approach",
                strategy="modify_approach",
                failed_step=step_name,
                error_category=ec.category,
                confidence=0.8,
            )

    # Syntax/import errors always need replanning
    if ec.category in ("syntax", "import"):
        return ReplanDecision(
            should_replan=True,
            reason=f"{ec.category} error — code generation needs adjustment",
            strategy="modify_approach",
            failed_step=step_name,
            error_category=ec.category,
            confidence=0.85,
        )

    # Test failures need replanning
    if ec.category == "test_failure":
        return ReplanDecision(
            should_replan=True,
            reason="Tests failed — implementation needs revision",
            strategy="modify_approach",
            failed_step=step_name,
            error_category=ec.category,
            confidence=0.75,
        )

    # Timeout on first attempt → retry
    if ec.category == "timeout" and attempt <= 1:
        return ReplanDecision(
            should_replan=False,
            reason="Timeout on first attempt — retry with longer timeout",
            strategy="retry_same",
            failed_step=step_name,
            error_category=ec.category,
            confidence=0.7,
        )

    # Max attempts reached → escalate or decompose
    if attempt >= max_attempts:
        return ReplanDecision(
            should_replan=True,
            reason=f"Max attempts ({max_attempts}) reached — need decomposition or escalation",
            strategy="decompose" if ec.replannable else "escalate",
            failed_step=step_name,
            error_category=ec.category,
            confidence=0.6,
        )

    # Default: retry for retryable, replan for non-retryable
    if ec.retryable:
        return ReplanDecision(
            should_replan=False,
            reason=f"Retryable {ec.category} error — retry attempt {attempt+1}",
            strategy="retry_same",
            failed_step=step_name,
            error_category=ec.category,
            confidence=0.6,
        )

    return ReplanDecision(
        should_replan=ec.replannable,
        reason=f"Non-retryable {ec.category} — {'replan' if ec.replannable else 'escalate'}",
        strategy="modify_approach" if ec.replannable else "escalate",
        failed_step=step_name,
        error_category=ec.category,
        confidence=0.5,
    )
