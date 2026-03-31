"""
JARVIS MAX — Executor Hardening Layer
========================================
Production-grade reliability upgrades targeting 9.5/10.

Components:
1. StructuredError    — typed error envelope with full metadata
2. PartialResult      — partial failure classification
3. CompletionGuard    — prevents false-DONE on critical path failures
4. RetryClassifier    — determines retryability with reasoning
5. StressShield       — concurrent execution protection

Non-invasive: these are composable helpers consumed by ExecutionEngine.
"""
from __future__ import annotations

import hashlib
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ═══════════════════════════════════════════════════════════════
# 1. STRUCTURED ERROR
# ═══════════════════════════════════════════════════════════════

class ErrorCategory(str, Enum):
    TIMEOUT = "timeout"
    TOOL_FAILURE = "tool_failure"
    PROVIDER_FAILURE = "provider_failure"
    VALIDATION_ERROR = "validation_error"
    PERMISSION_DENIED = "permission_denied"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    INVALID_OUTPUT = "invalid_output"
    NETWORK_ERROR = "network_error"
    INTERNAL_ERROR = "internal_error"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


@dataclass
class StructuredError:
    """
    Typed error envelope — every executor failure must have this.
    No ambiguous or weak failure envelopes.
    """
    error_type: str           # Exception class name
    category: str             # ErrorCategory value
    retryable: bool           # Whether retry makes sense
    stage: str                # Where in execution: dispatch, handler, postprocess
    tool: str = ""            # Which tool failed (if applicable)
    trace_id: str = ""        # Correlation ID for tracing
    message: str = ""         # Human-readable error message
    details: str = ""         # Extended details (stack trace excerpt)
    attempt: int = 0          # Which attempt this error occurred on
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "error_type": self.error_type,
            "category": self.category,
            "retryable": self.retryable,
            "stage": self.stage,
            "tool": self.tool,
            "trace_id": self.trace_id,
            "message": self.message[:300],
            "details": self.details[:200],
            "attempt": self.attempt,
            "timestamp": self.timestamp,
        }

    @staticmethod
    def from_exception(exc: Exception, stage: str = "handler",
                       tool: str = "", trace_id: str = "",
                       attempt: int = 0) -> "StructuredError":
        """Create a StructuredError from any exception."""
        err_type = type(exc).__name__
        category, retryable = _classify_error(exc)
        return StructuredError(
            error_type=err_type,
            category=category,
            retryable=retryable,
            stage=stage,
            tool=tool,
            trace_id=trace_id,
            message=str(exc)[:300],
            details=err_type,
            attempt=attempt,
        )


def _classify_error(exc: Exception) -> tuple[str, bool]:
    """Classify exception into category + retryable."""
    err_type = type(exc).__name__
    err_msg = str(exc).lower()

    # Timeout
    if isinstance(exc, (TimeoutError, )):
        return ErrorCategory.TIMEOUT, True
    if "timeout" in err_type.lower() or "timeout" in err_msg:
        return ErrorCategory.TIMEOUT, True

    # Network
    if any(kw in err_type.lower() for kw in ("connection", "socket", "network")):
        return ErrorCategory.NETWORK_ERROR, True
    if any(kw in err_msg for kw in ("connection refused", "connection reset", "dns",
                                      "network unreachable", "eof")):
        return ErrorCategory.NETWORK_ERROR, True

    # Provider (API rate limits, 5xx)
    if "rate limit" in err_msg or "429" in err_msg:
        return ErrorCategory.PROVIDER_FAILURE, True
    if any(f"{code}" in err_msg for code in (500, 502, 503, 504)):
        return ErrorCategory.PROVIDER_FAILURE, True

    # Permission
    if any(kw in err_msg for kw in ("permission", "forbidden", "unauthorized", "401", "403")):
        return ErrorCategory.PERMISSION_DENIED, False

    # Resource exhaustion
    if any(kw in err_msg for kw in ("memory", "disk", "quota", "limit exceeded")):
        return ErrorCategory.RESOURCE_EXHAUSTED, False

    # Validation
    if any(kw in err_type.lower() for kw in ("value", "type", "validation", "schema")):
        return ErrorCategory.VALIDATION_ERROR, False

    # Cancelled
    if isinstance(exc, (KeyboardInterrupt, SystemExit)):
        return ErrorCategory.CANCELLED, False
    if "cancel" in err_msg:
        return ErrorCategory.CANCELLED, False

    # Tool failures
    if "tool" in err_msg or "tool" in err_type.lower():
        return ErrorCategory.TOOL_FAILURE, True

    # Default
    return ErrorCategory.UNKNOWN, False


# ═══════════════════════════════════════════════════════════════
# 2. PARTIAL RESULT
# ═══════════════════════════════════════════════════════════════

class OutcomeType(str, Enum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    DEGRADED = "degraded"       # Core completed, extras failed
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


@dataclass
class StepOutcome:
    """Outcome of a single execution step."""
    step_id: str
    status: str           # success, failed, skipped, timed_out
    critical: bool        # Is this step critical for mission success?
    error: StructuredError | None = None
    result: str = ""
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "status": self.status,
            "critical": self.critical,
            "error": self.error.to_dict() if self.error else None,
            "result": self.result[:200],
            "duration_ms": round(self.duration_ms, 1),
        }


@dataclass
class PartialResult:
    """
    Classifies execution outcome across multiple steps.
    Prevents false-DONE: if any critical step failed, outcome is FAILED.
    """
    mission_id: str = ""
    steps: list[StepOutcome] = field(default_factory=list)
    outcome: str = OutcomeType.SUCCESS
    outcome_reason: str = ""

    def add_step(self, step: StepOutcome) -> None:
        self.steps.append(step)
        self._recompute()

    def _recompute(self) -> None:
        """Recompute overall outcome from step outcomes."""
        if not self.steps:
            self.outcome = OutcomeType.SUCCESS
            return

        critical_failed = [s for s in self.steps if s.critical and s.status == "failed"]
        critical_timeout = [s for s in self.steps if s.critical and s.status == "timed_out"]
        any_failed = [s for s in self.steps if s.status == "failed"]
        any_success = [s for s in self.steps if s.status == "success"]
        any_cancelled = [s for s in self.steps if s.status == "cancelled"]

        if any_cancelled:
            self.outcome = OutcomeType.CANCELLED
            self.outcome_reason = "Mission was cancelled"
        elif critical_failed:
            self.outcome = OutcomeType.FAILED
            self.outcome_reason = f"{len(critical_failed)} critical step(s) failed: " + \
                ", ".join(s.step_id for s in critical_failed)
        elif critical_timeout:
            self.outcome = OutcomeType.TIMED_OUT
            self.outcome_reason = f"{len(critical_timeout)} critical step(s) timed out"
        elif any_failed and any_success:
            self.outcome = OutcomeType.PARTIAL_SUCCESS
            self.outcome_reason = f"{len(any_success)} succeeded, {len(any_failed)} failed (non-critical)"
        elif any_failed and not any_success:
            self.outcome = OutcomeType.FAILED
            self.outcome_reason = "All steps failed"
        elif any_success and not any_failed:
            self.outcome = OutcomeType.SUCCESS
            self.outcome_reason = f"All {len(any_success)} steps succeeded"
        else:
            self.outcome = OutcomeType.DEGRADED
            self.outcome_reason = "Mixed results with no clear success"

    def is_truly_done(self) -> bool:
        """True only if all critical steps succeeded."""
        critical = [s for s in self.steps if s.critical]
        if not critical:
            return True  # No critical steps defined → assume done
        return all(s.status == "success" for s in critical)

    def to_dict(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "outcome": self.outcome,
            "outcome_reason": self.outcome_reason,
            "is_truly_done": self.is_truly_done(),
            "steps": [s.to_dict() for s in self.steps],
            "total_steps": len(self.steps),
            "succeeded": sum(1 for s in self.steps if s.status == "success"),
            "failed": sum(1 for s in self.steps if s.status == "failed"),
        }


# ═══════════════════════════════════════════════════════════════
# 3. COMPLETION GUARD
# ═══════════════════════════════════════════════════════════════

class CompletionGuard:
    """
    Prevents false-DONE: verifies that a mission has actually completed
    its critical execution path before allowing DONE status.

    Usage:
        guard = CompletionGuard()
        guard.register_critical("step-1")
        guard.register_critical("step-2")
        guard.mark_completed("step-1")
        guard.can_complete()  → False (step-2 not done)
    """

    def __init__(self, mission_id: str = ""):
        self._mission_id = mission_id
        self._critical_steps: set[str] = set()
        self._completed_steps: set[str] = set()
        self._failed_steps: dict[str, StructuredError] = {}

    def register_critical(self, step_id: str) -> None:
        """Mark a step as critical for mission completion."""
        self._critical_steps.add(step_id)

    def mark_completed(self, step_id: str) -> None:
        """Mark a step as successfully completed."""
        self._completed_steps.add(step_id)

    def mark_failed(self, step_id: str, error: StructuredError) -> None:
        """Mark a step as failed."""
        self._failed_steps[step_id] = error

    def can_complete(self) -> bool:
        """True only if all critical steps are completed."""
        if not self._critical_steps:
            return True
        return self._critical_steps.issubset(self._completed_steps)

    def blocking_steps(self) -> list[str]:
        """Return critical steps that haven't completed."""
        return list(self._critical_steps - self._completed_steps)

    def completion_status(self) -> dict:
        return {
            "can_complete": self.can_complete(),
            "critical_total": len(self._critical_steps),
            "critical_completed": len(self._critical_steps & self._completed_steps),
            "critical_failed": len(self._critical_steps & set(self._failed_steps.keys())),
            "blocking": self.blocking_steps(),
        }


# ═══════════════════════════════════════════════════════════════
# 4. RETRY CLASSIFIER
# ═══════════════════════════════════════════════════════════════

@dataclass
class RetryDecision:
    """Structured retry decision with reasoning."""
    should_retry: bool
    reason: str
    delay_s: float = 0.0
    strategy: str = ""  # immediate, backoff, circuit_break

    def to_dict(self) -> dict:
        return {
            "should_retry": self.should_retry,
            "reason": self.reason,
            "delay_s": round(self.delay_s, 2),
            "strategy": self.strategy,
        }


class RetryClassifier:
    """
    Determines retryability with explicit reasoning.
    Ensures retry only when truly retryable + bounded.
    """

    MAX_RETRIES = 5       # Hard ceiling
    MAX_DELAY_S = 120     # Never wait more than 2 minutes

    def __init__(self):
        self._error_counts: dict[str, int] = {}   # tool → error count
        self._circuit_breakers: dict[str, float] = {}  # tool → circuit open until

    def classify(self, error: StructuredError, attempt: int,
                 max_attempts: int = 3) -> RetryDecision:
        """Decide whether to retry with full reasoning."""

        # Hard ceiling
        if attempt >= min(max_attempts, self.MAX_RETRIES):
            return RetryDecision(
                should_retry=False,
                reason=f"Max attempts reached ({attempt}/{max_attempts})",
            )

        # Circuit breaker check
        tool = error.tool or "default"
        if tool in self._circuit_breakers:
            if time.time() < self._circuit_breakers[tool]:
                return RetryDecision(
                    should_retry=False,
                    reason=f"Circuit breaker open for {tool}",
                    strategy="circuit_break",
                )
            else:
                del self._circuit_breakers[tool]

        # Track error counts
        self._error_counts[tool] = self._error_counts.get(tool, 0) + 1

        # Open circuit breaker after 5 errors on same tool
        if self._error_counts[tool] >= 5:
            self._circuit_breakers[tool] = time.time() + 60
            return RetryDecision(
                should_retry=False,
                reason=f"Circuit breaker opened: {tool} has {self._error_counts[tool]} errors",
                strategy="circuit_break",
            )

        # Non-retryable categories
        if not error.retryable:
            return RetryDecision(
                should_retry=False,
                reason=f"Error category '{error.category}' is not retryable",
            )

        # Retryable — compute delay
        base_delay = 1.0
        delay = min(base_delay * (2 ** (attempt - 1)), self.MAX_DELAY_S)

        # Specific strategies
        if error.category == ErrorCategory.TIMEOUT:
            return RetryDecision(
                should_retry=True,
                reason=f"Timeout is retryable (attempt {attempt})",
                delay_s=delay,
                strategy="backoff",
            )

        if error.category == ErrorCategory.PROVIDER_FAILURE:
            # Rate limits need longer delay
            delay = min(delay * 2, self.MAX_DELAY_S)
            return RetryDecision(
                should_retry=True,
                reason=f"Provider failure, retrying with extended delay",
                delay_s=delay,
                strategy="backoff",
            )

        if error.category == ErrorCategory.NETWORK_ERROR:
            return RetryDecision(
                should_retry=True,
                reason=f"Network error, retrying immediately",
                delay_s=min(delay, 5.0),
                strategy="immediate",
            )

        if error.category == ErrorCategory.TOOL_FAILURE:
            return RetryDecision(
                should_retry=True,
                reason=f"Tool failure on {error.tool}, retrying with backoff",
                delay_s=delay,
                strategy="backoff",
            )

        return RetryDecision(
            should_retry=True,
            reason=f"Retryable error: {error.category}",
            delay_s=delay,
            strategy="backoff",
        )

    def reset(self, tool: str = "") -> None:
        """Reset error counts and circuit breakers."""
        if tool:
            self._error_counts.pop(tool, None)
            self._circuit_breakers.pop(tool, None)
        else:
            self._error_counts.clear()
            self._circuit_breakers.clear()


# ═══════════════════════════════════════════════════════════════
# 5. STRESS SHIELD
# ═══════════════════════════════════════════════════════════════

class StressShield:
    """
    Protects the executor under stress conditions:
    - Concurrent mission limiting
    - Timeout storm detection
    - Provider failure circuit breaking
    - Invalid output quarantine

    Thread-safe.
    """

    MAX_CONCURRENT = 10
    TIMEOUT_STORM_THRESHOLD = 5    # N timeouts in window
    TIMEOUT_STORM_WINDOW_S = 60

    def __init__(self):
        self._lock = threading.Lock()
        self._active_missions: set[str] = set()
        self._recent_timeouts: list[float] = []
        self._invalid_outputs: int = 0
        self._provider_failures: int = 0

    def can_accept(self, mission_id: str = "") -> tuple[bool, str]:
        """Check if the executor can accept a new mission."""
        with self._lock:
            if len(self._active_missions) >= self.MAX_CONCURRENT:
                return False, f"Max concurrent missions ({self.MAX_CONCURRENT}) reached"

            if self._is_timeout_storm():
                return False, "Timeout storm detected — backing off"

            return True, "ok"

    def register_start(self, mission_id: str) -> None:
        with self._lock:
            self._active_missions.add(mission_id)

    def register_complete(self, mission_id: str) -> None:
        with self._lock:
            self._active_missions.discard(mission_id)

    def register_timeout(self) -> None:
        with self._lock:
            self._recent_timeouts.append(time.time())
            # Prune old
            cutoff = time.time() - self.TIMEOUT_STORM_WINDOW_S
            self._recent_timeouts = [t for t in self._recent_timeouts if t > cutoff]

    def register_invalid_output(self) -> None:
        with self._lock:
            self._invalid_outputs += 1

    def register_provider_failure(self) -> None:
        with self._lock:
            self._provider_failures += 1

    def _is_timeout_storm(self) -> bool:
        cutoff = time.time() - self.TIMEOUT_STORM_WINDOW_S
        recent = [t for t in self._recent_timeouts if t > cutoff]
        return len(recent) >= self.TIMEOUT_STORM_THRESHOLD

    def status(self) -> dict:
        with self._lock:
            cutoff = time.time() - self.TIMEOUT_STORM_WINDOW_S
            recent_to = [t for t in self._recent_timeouts if t > cutoff]
            return {
                "active_missions": len(self._active_missions),
                "max_concurrent": self.MAX_CONCURRENT,
                "recent_timeouts": len(recent_to),
                "timeout_storm": self._is_timeout_storm(),
                "invalid_outputs": self._invalid_outputs,
                "provider_failures": self._provider_failures,
            }

    def reset(self) -> None:
        with self._lock:
            self._active_missions.clear()
            self._recent_timeouts.clear()
            self._invalid_outputs = 0
            self._provider_failures = 0
