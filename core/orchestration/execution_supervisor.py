"""
core/orchestration/execution_supervisor.py — Monitor execution and decide on failures.

Wraps the actual execution delegate with supervision logic:
retry, replan, escalate, or abort.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

import structlog

log = structlog.get_logger("orchestration.supervisor")


class RecoveryAction(str, Enum):
    RETRY = "retry"
    REPLAN = "replan"
    FALLBACK = "fallback"
    ESCALATE = "escalate"
    ABORT = "abort"


@dataclass
class ExecutionOutcome:
    """Structured outcome from supervised execution."""
    success: bool = False
    result: str = ""
    error: str = ""
    error_class: str = ""
    retries: int = 0
    recovery_actions: list[str] = field(default_factory=list)
    duration_ms: int = 0
    decision_trace: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "result": self.result[:500],
            "error": self.error[:200],
            "error_class": self.error_class,
            "retries": self.retries,
            "recovery_actions": self.recovery_actions,
            "duration_ms": self.duration_ms,
            "decision_trace": self.decision_trace,
        }


# Maximum retries before giving up
_MAX_RETRIES = 2
_RETRY_BACKOFF_BASE = 1.5  # seconds

# Per-attempt hard deadline (prevents a hung LLM from stalling the retry loop).
# The outer asyncio.wait_for() in MetaOrchestrator handles the overall mission budget;
# this finer-grain timeout ensures retry logic can fire between attempts.
#
# Coherence: outer timeout is 600s; _MAX_RETRIES=2 means 3 attempts.
# 180s × 3 = 540s < 600s, so the retry budget is reachable before the outer deadline.
# (The old 300s × 3 = 900s exceeded the outer deadline — retries past attempt 0 were
# unreachable because the outer wait_for fired first.)
_ATTEMPT_TIMEOUT_S = 180  # 3 minutes per attempt — allows ≥2 retries within 600s outer

# Approval queue submission timeout — prevents hangs on slow approval backends.
_APPROVAL_SUBMIT_TIMEOUT_S = 10  # 10 seconds to submit


async def supervise(
    execute_fn: Callable,
    *,
    mission_id: str,
    goal: str,
    mode: str = "auto",
    session_id: str = "",
    risk_level: str = "low",
    requires_approval: bool = False,
    skip_approval: bool = False,
    callback: Any = None,
) -> ExecutionOutcome:
    """
    Execute with supervision: approval gate, retry on transient failures,
    abort on permanent ones.

    execute_fn should be an async callable that performs the actual mission work
    and returns a session-like object with final_report and auto_count.
    """
    outcome = ExecutionOutcome()
    t0 = time.monotonic()
    last_error = ""

    # ── Approval gate ─────────────────────────────────────────
    # skip_approval=True means a human already approved (resumption path)
    if not skip_approval and _needs_approval(risk_level, requires_approval):
        # If explicitly flagged but low risk, elevate for queue submission
        gate_risk = risk_level if risk_level.lower() in _APPROVAL_RISK_THRESHOLD else "medium"
        approval = await _request_approval(
            mission_id=mission_id,
            goal=goal,
            risk_level=gate_risk,
        )
        outcome.decision_trace.append({
            "step": "approval_gate",
            "risk_level": risk_level,
            "approved": approval["approved"],
            "auto": approval.get("auto", False),
            "item_id": approval.get("item_id", ""),
        })

        if not approval["approved"]:
            if approval.get("pending"):
                # Waiting for human approval
                outcome.success = False
                outcome.error = "awaiting_approval"
                outcome.error_class = "awaiting_approval"
                outcome.duration_ms = int((time.monotonic() - t0) * 1000)
                outcome.decision_trace.append({
                    "step": "paused",
                    "reason": "Execution paused — awaiting human approval",
                    "item_id": approval.get("item_id", ""),
                })
                log.info("execution_awaiting_approval",
                         mission_id=mission_id, risk_level=risk_level,
                         item_id=approval.get("item_id", "")[:8])
                return outcome
            else:
                # Approval denied or failed
                outcome.success = False
                outcome.error = "approval_denied"
                outcome.error_class = "approval_denied"
                outcome.duration_ms = int((time.monotonic() - t0) * 1000)
                log.warning("execution_approval_denied",
                            mission_id=mission_id, risk_level=risk_level)
                return outcome
        else:
            log.info("execution_approved",
                     mission_id=mission_id,
                     auto=approval.get("auto", False))

    for attempt in range(1 + _MAX_RETRIES):
        # Emit attempt_start to EventStream (fail-open)
        try:
            from core.event_stream import get_mission_stream
            from core.events import Action
            _es = get_mission_stream(mission_id)
            if _es:
                await _es.append(Action(
                    source="supervisor",
                    action_type="execution_attempt",
                    reasoning=f"Attempt {attempt + 1} of {1 + _MAX_RETRIES}",
                ))
        except Exception:
            pass

        try:
            # Per-attempt timeout: prevents a hung LLM/delegate from blocking the
            # retry loop indefinitely. asyncio.TimeoutError is caught below → RETRY.
            session = await asyncio.wait_for(
                execute_fn(
                    user_input=goal,
                    mode=mode,
                    session_id=session_id,
                    callback=callback,
                ),
                timeout=_ATTEMPT_TIMEOUT_S,
            )
            outcome.success = True
            outcome.result = getattr(session, "final_report", "") or ""
            outcome.retries = attempt
            outcome.duration_ms = int((time.monotonic() - t0) * 1000)

            outcome.decision_trace.append({
                "step": "execution_complete",
                "attempt": attempt + 1,
                "success": True,
            })

            # Emit execution_complete to EventStream (fail-open)
            try:
                from core.event_stream import get_mission_stream
                from core.events import Observation
                _es = get_mission_stream(mission_id)
                if _es:
                    await _es.append(Observation(
                        source="supervisor",
                        observation_type="execution_complete",
                        content=outcome.result[:500],
                        metadata={"success": True, "attempts": attempt + 1,
                                  "duration_ms": outcome.duration_ms},
                    ))
            except Exception:
                pass

            log.info("execution_supervised_ok",
                     mission_id=mission_id, attempts=attempt + 1,
                     duration_ms=outcome.duration_ms)
            return outcome

        except asyncio.TimeoutError:
            last_error = "timeout"
            outcome.error_class = "timeout"
            action = _decide_recovery("timeout", attempt, risk_level)

        except asyncio.CancelledError:
            outcome.error = "cancelled"
            outcome.error_class = "cancelled"
            outcome.decision_trace.append({"step": "cancelled", "action": "abort"})
            outcome.duration_ms = int((time.monotonic() - t0) * 1000)
            return outcome

        except ConnectionError as e:
            last_error = str(e)[:100]
            outcome.error_class = "connection_error"
            action = _decide_recovery("connection_error", attempt, risk_level)

        except Exception as e:
            last_error = str(e)[:200]
            outcome.error_class = _classify_exception(e)
            action = _decide_recovery(outcome.error_class, attempt, risk_level)

        # Record decision
        outcome.decision_trace.append({
            "step": "failure",
            "attempt": attempt + 1,
            "error_class": outcome.error_class,
            "error": last_error[:80],
            "recovery_action": action.value,
        })
        outcome.recovery_actions.append(action.value)

        if action == RecoveryAction.RETRY:
            backoff = _RETRY_BACKOFF_BASE * (attempt + 1)
            log.warning("execution_retry",
                        mission_id=mission_id, attempt=attempt + 1,
                        backoff=backoff, error=last_error[:60])
            await asyncio.sleep(backoff)
            continue

        elif action == RecoveryAction.ABORT:
            break

        elif action == RecoveryAction.FALLBACK:
            # Strategy switch: try simplified execution
            log.warning("execution_fallback",
                        mission_id=mission_id, error=last_error[:60])
            outcome.decision_trace.append({
                "step": "strategy_switch",
                "from": "normal",
                "to": "simplified",
            })
            # Simplify goal and retry once
            try:
                session = await execute_fn(
                    user_input=f"[SIMPLIFIED] {goal}",
                    mode=mode,
                    session_id=session_id,
                    callback=callback,
                )
                outcome.success = True
                outcome.result = getattr(session, "final_report", "") or ""
                outcome.retries = attempt + 1
                outcome.duration_ms = int((time.monotonic() - t0) * 1000)
                outcome.recovery_actions.append("fallback_succeeded")
                return outcome
            except Exception as fe:
                log.warning("fallback_failed", err=str(fe)[:60])
                break

        else:
            # ESCALATE, REPLAN — abort with structured reason
            log.warning("execution_escalated",
                        mission_id=mission_id, action=action.value,
                        error=last_error[:60])
            break

    # All retries exhausted or abort
    outcome.success = False
    outcome.error = last_error
    outcome.retries = min(attempt, _MAX_RETRIES)
    outcome.duration_ms = int((time.monotonic() - t0) * 1000)

    log.error("execution_supervised_failed",
              mission_id=mission_id,
              retries=outcome.retries,
              error_class=outcome.error_class,
              error=last_error[:80])
    return outcome




# ── Approval helpers ─────────────────────────────────────────

# BLOC H: "medium" must require approval — only "low" is auto-approved.
# Previously only "high"/"critical" were gated, leaving medium-risk actions
# bypassing the approval gate silently.
_APPROVAL_RISK_THRESHOLD = {"medium", "high", "critical"}


def _needs_approval(risk_level: str, explicit_flag: bool) -> bool:
    """Determine if approval is needed based on risk and explicit flag."""
    if explicit_flag:
        return True
    return risk_level.lower() in _APPROVAL_RISK_THRESHOLD


async def _request_approval(
    mission_id: str,
    goal: str,
    risk_level: str,
) -> dict:
    """
    Submit to approval queue and check result.
    Returns dict with: approved, pending, auto, item_id.

    Runs the sync submit_for_approval() in a thread executor with a hard timeout
    (_APPROVAL_SUBMIT_TIMEOUT_S) so a slow approval backend can never block the
    event loop or hang a mission indefinitely.
    """
    try:
        from core.approval_queue import submit_for_approval, RiskLevel

        # Map string risk to RiskLevel enum
        risk_map = {
            "low": RiskLevel.WRITE_LOW,
            "medium": RiskLevel.WRITE_HIGH,
            "high": RiskLevel.INFRA,
            "critical": RiskLevel.DEPLOY,
        }
        rl = risk_map.get(risk_level.lower(), RiskLevel.WRITE_HIGH)

        def _submit():
            return submit_for_approval(
                action=f"Execute mission: {goal[:100]}",
                risk_level=rl,
                reason=f"Risk level: {risk_level}",
                expected_impact=f"Mission {mission_id} will execute with {risk_level} risk",
                rollback_plan="Mission can be cancelled",
                source="meta_orchestrator",
                payload={"mission_id": mission_id, "goal": goal[:200]},
            )

        loop = asyncio.get_running_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, _submit),
            timeout=_APPROVAL_SUBMIT_TIMEOUT_S,
        )
        return result

    except asyncio.TimeoutError:
        log.warning("approval_gate_timeout",
                    mission_id=mission_id, timeout_s=_APPROVAL_SUBMIT_TIMEOUT_S)
        # Timeout on approval submission: fail-closed for high risk, fail-open otherwise
        if risk_level.lower() in ("high", "critical"):
            return {"approved": False, "pending": False, "auto": False,
                    "error": "approval_submission_timeout"}
        return {"approved": True, "auto": True, "error": "approval_submission_timeout"}

    except Exception as e:
        log.warning("approval_gate_error", err=str(e)[:60])
        # Fail-open for low risk, fail-closed for high risk
        if risk_level.lower() in ("high", "critical"):
            return {"approved": False, "pending": False, "auto": False}
        return {"approved": True, "auto": True}


def _decide_recovery(error_class: str, attempt: int, risk_level: str) -> RecoveryAction:
    """
    Decide recovery action based on error type, attempt count, and risk.

    Logic: high risk → escalate, permanent → abort, transient → retry,
    last retry exhausted → try FALLBACK before final abort.
    """
    # Never retry high-risk operations
    if risk_level in ("high", "critical"):
        return RecoveryAction.ESCALATE

    # Permanent errors → abort immediately (no point retrying)
    if error_class in ("permission_denied", "invalid_input", "not_found"):
        return RecoveryAction.ABORT

    # Transient errors → retry if attempts remain
    if error_class in ("timeout", "connection_error", "rate_limit"):
        if attempt < _MAX_RETRIES:
            return RecoveryAction.RETRY
        # Last chance: try FALLBACK (simplified execution)
        return RecoveryAction.FALLBACK

    # LLM errors → retry once, then fallback
    if error_class in ("llm_error", "llm_unavailable"):
        if attempt < 1:
            return RecoveryAction.RETRY
        return RecoveryAction.FALLBACK

    # Execution errors → try fallback instead of blind retry
    if error_class in ("execution_error", "execution_exception"):
        if attempt == 0:
            return RecoveryAction.RETRY
        return RecoveryAction.FALLBACK

    # Default: abort after retries exhausted
    if attempt >= _MAX_RETRIES:
        return RecoveryAction.FALLBACK

    return RecoveryAction.RETRY


def _classify_exception(e: Exception) -> str:
    """Classify an exception into an error category."""
    name = type(e).__name__.lower()
    msg = str(e).lower()

    if "timeout" in name or "timeout" in msg:
        return "timeout"
    if "permission" in msg or "denied" in msg:
        return "permission_denied"
    if "not found" in msg or "404" in msg:
        return "not_found"
    if "rate" in msg and "limit" in msg:
        return "rate_limit"
    if "connection" in name or "network" in msg:
        return "connection_error"
    if "llm" in msg or "openai" in msg or "anthropic" in msg:
        return "llm_error"
    if "validation" in msg or "invalid" in msg:
        return "invalid_input"
    return "execution_error"
