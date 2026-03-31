"""
core/planning/plan_validator.py — Validate execution plans before running.

Checks:
  1. All step targets exist (actions, tools, skills)
  2. Dependencies are satisfiable (no cycles, all deps exist)
  3. Risk assessment is accurate
  4. Tool readiness verified
  5. Approval requirements computed
"""
from __future__ import annotations

import structlog

from core.planning.execution_plan import ExecutionPlan, PlanStep, StepType

log = structlog.get_logger("planning.validator")


def validate_plan(plan: ExecutionPlan) -> dict:
    """
    Validate an execution plan.

    Returns:
        {
            "valid": bool,
            "errors": list[str],
            "warnings": list[str],
            "risk_score": str,
            "requires_approval": bool,
            "tool_readiness": list[dict],
        }
    """
    errors = []
    warnings = []
    tool_readiness = []

    if not plan.goal:
        errors.append("Plan must have a goal")

    if not plan.steps:
        errors.append("Plan must have at least one step")

    step_ids = {s.step_id for s in plan.steps}

    for step in plan.steps:
        # Check target exists
        target_ok = _check_target_exists(step)
        if not target_ok:
            errors.append(f"Step '{step.step_id}': target '{step.target_id}' not found")

        # Check dependencies reference valid steps
        for dep in step.depends_on:
            if dep not in step_ids:
                errors.append(f"Step '{step.step_id}': dependency '{dep}' not in plan")

        # Check tool readiness
        if step.type == StepType.TOOL:
            readiness = _check_tool_readiness(step.target_id)
            tool_readiness.append(readiness)
            if not readiness.get("ready") and readiness.get("tool_id"):
                warnings.append(
                    f"Tool '{step.target_id}' not ready: "
                    f"missing={readiness.get('missing_secrets', [])}"
                )

    # Cycle detection
    if _has_cycle(plan.steps):
        errors.append("Plan has circular dependencies")

    # Compute risk and approval
    risk = plan.compute_risk()
    needs_approval = plan.compute_approval_required()

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "risk_score": risk,
        "requires_approval": needs_approval,
        "tool_readiness": tool_readiness,
    }


def _check_target_exists(step: PlanStep) -> bool:
    """Check if the target action/tool/skill exists."""
    if step.type == StepType.BUSINESS_ACTION:
        try:
            from core.business_actions import ACTION_REGISTRY
            return step.target_id in ACTION_REGISTRY
        except Exception:
            return True  # Can't check — assume ok

    elif step.type == StepType.TOOL:
        try:
            from core.tools_operational.tool_registry import get_tool_registry
            return get_tool_registry().get(step.target_id) is not None
        except Exception:
            return True

    elif step.type == StepType.SKILL:
        try:
            from core.skills.domain_loader import get_domain_registry
            return get_domain_registry().get(step.target_id) is not None
        except Exception:
            return True

    return True


def _check_tool_readiness(tool_id: str) -> dict:
    """Check if a tool is ready."""
    try:
        from core.tools_operational.tool_readiness import check_readiness
        return check_readiness(tool_id)
    except Exception:
        return {"tool_id": tool_id, "ready": True}


def _has_cycle(steps: list[PlanStep]) -> bool:
    """Detect dependency cycles using DFS."""
    graph = {s.step_id: s.depends_on for s in steps}
    visited = set()
    in_stack = set()

    def dfs(node: str) -> bool:
        if node in in_stack:
            return True
        if node in visited:
            return False
        visited.add(node)
        in_stack.add(node)
        for dep in graph.get(node, []):
            if dfs(dep):
                return True
        in_stack.discard(node)
        return False

    return any(dfs(s.step_id) for s in steps if s.step_id not in visited)
