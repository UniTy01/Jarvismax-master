"""
core/planning/workflow_templates.py — Load workflow templates and build execution plans from them.

Templates are JSON files in business/workflows/.
A template becomes an ExecutionPlan when instantiated with inputs.
"""
from __future__ import annotations

import json
import os
import structlog
from pathlib import Path

from core.planning.execution_plan import ExecutionPlan, PlanStep, StepType

log = structlog.get_logger("planning.templates")

_TEMPLATES_DIR = Path(os.path.dirname(__file__)).parent.parent / "business" / "workflows"


def load_templates() -> list[dict]:
    """Load all workflow templates from disk."""
    templates = []
    if not _TEMPLATES_DIR.is_dir():
        return templates
    for f in sorted(_TEMPLATES_DIR.glob("*.json")):
        try:
            with open(f) as fh:
                templates.append(json.load(fh))
        except Exception as e:
            log.debug("template_load_failed", path=str(f), err=str(e)[:80])
    return templates


def get_template(template_id: str) -> dict | None:
    """Get a specific template by ID."""
    for t in load_templates():
        if t.get("template_id") == template_id:
            return t
    return None


def list_template_ids() -> list[str]:
    """List all available template IDs."""
    return [t["template_id"] for t in load_templates() if "template_id" in t]


def build_plan_from_template(
    template_id: str,
    goal_override: str = "",
    inputs: dict | None = None,
    mission_id: str = "",
) -> ExecutionPlan | None:
    """
    Build an ExecutionPlan from a workflow template.

    Args:
        template_id: Which template to use
        goal_override: Override the template's default goal
        inputs: Default inputs to inject into steps
        mission_id: Associated mission ID
    """
    tmpl = get_template(template_id)
    if not tmpl:
        return None

    steps = []
    for i, step_def in enumerate(tmpl.get("steps", [])):
        step_inputs = dict(inputs or {})
        step_inputs.update(step_def.get("inputs", {}))

        step = PlanStep(
            type=StepType(step_def.get("type", "business_action")),
            target_id=step_def.get("id", ""),
            name=step_def.get("name", f"Step {i+1}"),
            inputs=step_inputs,
        )
        steps.append(step)

    plan = ExecutionPlan(
        goal=goal_override or tmpl.get("goal", ""),
        description=tmpl.get("description", ""),
        steps=steps,
        template_id=template_id,
        mission_id=mission_id,
    )
    plan.risk_score = plan.compute_risk()
    plan.requires_approval = plan.compute_approval_required()

    return plan
