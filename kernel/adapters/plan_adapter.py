"""
kernel/adapters/plan_adapter.py — Bidirectional adapter: ExecutionPlan ↔ kernel Plan.

Handles mismatch between:
  - core.planning.execution_plan.ExecutionPlan (runtime, has description/mission_id/approval/timing)
  - kernel.contracts.Plan (kernel, has risk_level enum, requires_approval bool)
"""
from __future__ import annotations

from kernel.contracts.types import (
    Plan, PlanStep, PlanStatus, StepType, RiskLevel,
)


def execution_plan_to_kernel(ep) -> Plan:
    """
    Convert a core.planning.execution_plan.ExecutionPlan to a kernel Plan.

    Args:
        ep: ExecutionPlan instance
    """
    steps = []
    for s in ep.steps:
        step_type = s.type if isinstance(s.type, StepType) else StepType(s.type.value if hasattr(s.type, "value") else str(s.type))
        steps.append(PlanStep(
            step_id=s.step_id,
            type=step_type,
            target_id=s.target_id,
            name=s.name,
            inputs=s.inputs,
            depends_on=s.depends_on,
            status=s.status,
            result=s.result,
        ))

    # Map risk_score string to RiskLevel enum
    risk_str = getattr(ep, "risk_score", "low")
    if isinstance(risk_str, str):
        try:
            risk = RiskLevel(risk_str)
        except ValueError:
            risk = RiskLevel.LOW
    else:
        risk = RiskLevel.LOW

    # Map plan status
    status_str = ep.status.value if hasattr(ep.status, "value") else str(ep.status)
    try:
        plan_status = PlanStatus(status_str)
    except ValueError:
        plan_status = PlanStatus.DRAFT

    return Plan(
        plan_id=ep.plan_id,
        goal=ep.goal,
        steps=steps,
        status=plan_status,
        risk_level=risk,
        requires_approval=getattr(ep, "requires_approval", False),
        template_id=getattr(ep, "template_id", ""),
        created_at=ep.created_at,
    )


def kernel_plan_to_dict(plan: Plan) -> dict:
    """
    Convert kernel Plan to dict compatible with ExecutionPlan.from_dict().

    Returns dict rather than ExecutionPlan to avoid circular imports.
    """
    return {
        "plan_id": plan.plan_id,
        "goal": plan.goal,
        "steps": [s.to_dict() for s in plan.steps],
        "status": plan.status.value,
        "risk_score": plan.risk_level.value,
        "requires_approval": plan.requires_approval,
        "template_id": plan.template_id,
        "created_at": plan.created_at,
    }
