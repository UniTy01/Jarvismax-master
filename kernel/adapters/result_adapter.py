"""
kernel/adapters/result_adapter.py — Adapter for execution results.

Converts:
  - core tool results (dicts) → kernel ExecutionResult
  - core policy decisions → kernel PolicyDecision
  - routing decisions → kernel Decision
"""
from __future__ import annotations

import time
from kernel.contracts.types import (
    ExecutionResult, PolicyDecision, Decision,
    DecisionType, RiskLevel,
)


def tool_result_to_kernel(result: dict, step_id: str = "",
                          mission_id: str = "") -> ExecutionResult:
    """
    Convert a tool execution result dict to kernel ExecutionResult.

    Expected dict shape:
      {"success": bool, "output": ..., "error": str, "duration_ms": float, ...}
    """
    return ExecutionResult(
        ok=result.get("success", result.get("ok", False)),
        output=result if isinstance(result, dict) else {"raw": str(result)},
        error=result.get("error", ""),
        duration_ms=result.get("duration_ms", 0),
        artifacts=result.get("artifacts", []),
        step_id=step_id,
        mission_id=mission_id,
    )


def core_policy_to_kernel(decision) -> PolicyDecision:
    """
    Convert a core.policy_engine.PolicyDecision to kernel PolicyDecision.

    Core PolicyDecision has: allowed, reason, suggestion, metadata
    Kernel PolicyDecision has: allowed, action_id, risk_level, requires_approval, reason
    """
    risk_str = getattr(decision, "metadata", {}).get("risk_level", "low")
    try:
        risk = RiskLevel(risk_str)
    except (ValueError, KeyError):
        risk = RiskLevel.LOW

    return PolicyDecision(
        allowed=decision.allowed,
        action_id=getattr(decision, "metadata", {}).get("action_id", ""),
        risk_level=risk,
        requires_approval=risk in (RiskLevel.HIGH, RiskLevel.CRITICAL),
        reason=decision.reason,
    )


def routing_decision_to_kernel(route_result: dict) -> Decision:
    """
    Convert a capability routing result to a kernel Decision.

    Expected shape from core/capability_routing/router.py route_single_capability():
      {"capability_id": str, "provider": {...}, "score": float, "alternatives": [...]}
    """
    provider = route_result.get("provider", {})
    score = route_result.get("score", 0.5)

    return Decision(
        decision_type=DecisionType.APPROVE if provider else DecisionType.DEFER,
        target_id=route_result.get("capability_id", ""),
        reason=f"Routed to {provider.get('id', 'unknown')} (score={score:.2f})",
        confidence=min(max(score, 0.0), 1.0),
        decided_by="capability_router",
        timestamp=time.time(),
    )
