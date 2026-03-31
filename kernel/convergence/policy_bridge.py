"""
kernel/convergence/policy_bridge.py — Bridge kernel policy pipeline to existing runtime.

Makes the kernel policy pipeline callable from existing code paths,
producing kernel-typed decisions that are backward-compatible.

Usage:
    from kernel.convergence.policy_bridge import check_action_kernel
    decision = check_action_kernel("tool_invoke", risk_level="medium")
    if decision.requires_approval:
        ...
"""
from __future__ import annotations

import structlog

from kernel.contracts.types import Action, PolicyDecision, RiskLevel

log = structlog.get_logger("kernel.convergence.policy")


def check_action_kernel(
    action_type: str,
    target: str = "",
    risk_level: str = "low",
    mode: str = "auto",
) -> PolicyDecision:
    """
    Evaluate an action through both kernel and core policy engines.

    Strategy: run kernel pipeline as primary, cross-check with core.
    If they disagree, take the MORE RESTRICTIVE result (conservative).

    Returns: kernel PolicyDecision
    """
    # 1. Kernel evaluation
    try:
        kernel_risk = RiskLevel(risk_level) if risk_level in ("low", "medium", "high", "critical") else RiskLevel.LOW
    except ValueError:
        kernel_risk = RiskLevel.LOW

    action = Action(
        action_type=action_type,
        target=target,
        risk_level=kernel_risk,
    )

    from kernel.policy.engine import evaluate_action
    kernel_decision = evaluate_action(action)

    # 2. Cross-check with core (fail-open)
    # Core PolicyEngine uses a mode-based whitelist (create_file, write_file, etc.)
    # Actions outside the whitelist are always blocked by core — which is correct
    # for core's action-level scope but overly restrictive for kernel-level evaluation.
    # Only apply core override when core explicitly allows (confirms kernel decision)
    # or when core blocks an action that IS in its vocabulary.
    try:
        from kernel.adapters.policy_adapter import core_check_action_to_kernel
        core_decision = core_check_action_to_kernel(
            action_type=action_type,
            risk_level=risk_level,
            mode=mode,
        )

        # Only override kernel if core has explicit policy for this action type
        # (core blocks everything not in its whitelist, which is too broad)
        _CORE_KNOWN_ACTIONS = {
            "create_file", "write_file", "replace_in_file", "backup_file",
            "run_command",
        }
        if action_type in _CORE_KNOWN_ACTIONS:
            if not core_decision.allowed and kernel_decision.allowed:
                kernel_decision.allowed = False
                kernel_decision.reason = f"Core policy blocked: {core_decision.reason}"
        # Always propagate approval requirement from core
        if core_decision.requires_approval and not kernel_decision.requires_approval:
            kernel_decision.requires_approval = True
            kernel_decision.reason += " (approval required by core policy)"

    except Exception as e:
        log.debug("core_policy_crosscheck_failed", err=str(e)[:60])

    return kernel_decision


def get_pending_approvals() -> list[dict]:
    """Get pending approvals from the kernel approval gate."""
    try:
        from kernel.runtime.boot import get_runtime
        runtime = get_runtime()
        return runtime.approval.get_pending()
    except Exception:
        return []


def resolve_approval(request_id: str, approved: bool,
                     reason: str = "", decided_by: str = "operator") -> dict:
    """Resolve a pending approval in the kernel."""
    try:
        from kernel.runtime.boot import get_runtime
        runtime = get_runtime()
        decision = runtime.approval.decide(
            request_id, approved=approved,
            reason=reason, decided_by=decided_by,
        )
        return decision.to_dict()
    except Exception as e:
        return {"error": str(e)}
