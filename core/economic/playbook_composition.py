"""
core/economic/playbook_composition.py — Playbook composition layer.

Phase C: Chain playbooks so outputs feed into next playbook's inputs.

Example flow:
  OpportunityReport → BusinessConcept → VenturePlan → GrowthPlan

Design:
  - No modifications to ExecutionPlan or PlanRunner
  - Composition = multi-playbook plan generation
  - Schema compatibility validation before chaining
  - Works on existing playbook and skill infrastructure
"""
from __future__ import annotations

import time
import uuid
import structlog
from dataclasses import dataclass, field

log = structlog.get_logger("economic.composition")


# ── Schema compatibility matrix ───────────────────────────────

# Which schema can feed which next playbook
SCHEMA_FEEDS: dict[str, list[str]] = {
    "OpportunityReport": ["product_creation", "offer_design"],
    "BusinessConcept": ["growth_experiment", "landing_page", "content_strategy"],
    "VenturePlan": ["content_strategy"],
    "MarketingPlan": [],
}

# Output→input field mapping between playbooks
FIELD_BRIDGES: dict[tuple[str, str], dict[str, str]] = {
    # market_analysis → product_creation
    ("market_analysis", "product_creation"): {
        "target_users": "audience",
        "problem_description": "business_context",
        "market_size_estimate": "market",
        "competition_overview": "competitors",
    },
    # market_analysis → offer_design
    ("market_analysis", "offer_design"): {
        "target_users": "audience",
        "problem_description": "business_context",
    },
    # product_creation → growth_experiment
    ("product_creation", "growth_experiment"): {
        "value_proposition": "product",
        "target_segment": "audience",
        "delivery_mechanism": "business_context",
    },
    # product_creation → landing_page
    ("product_creation", "landing_page"): {
        "value_proposition": "product",
        "target_segment": "audience",
        "differentiation_hypothesis": "feature",
    },
    # offer_design → growth_experiment
    ("offer_design", "growth_experiment"): {
        "value_proposition": "product",
        "target_segment": "audience",
    },
    # growth_experiment → content_strategy
    ("growth_experiment", "content_strategy"): {
        "acquisition_channels": "business_context",
        "target_segment": "audience",
    },
}


@dataclass
class CompositionStep:
    """A step in a composed playbook chain."""
    playbook_id: str
    input_overrides: dict = field(default_factory=dict)
    expected_schema: str = ""


@dataclass
class PlaybookChain:
    """A sequence of playbooks designed to be executed in order."""
    chain_id: str = ""
    name: str = ""
    description: str = ""
    steps: list[CompositionStep] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.chain_id:
            self.chain_id = f"chain-{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict:
        return {
            "chain_id": self.chain_id,
            "name": self.name,
            "description": self.description,
            "steps": [
                {
                    "playbook_id": s.playbook_id,
                    "input_overrides": s.input_overrides,
                    "expected_schema": s.expected_schema,
                }
                for s in self.steps
            ],
            "step_count": len(self.steps),
            "created_at": self.created_at,
        }


def validate_chain(chain: PlaybookChain) -> dict:
    """
    Validate a playbook chain for schema compatibility.

    Returns:
        {"valid": bool, "issues": [str], "bridges": [dict]}
    """
    issues: list[str] = []
    bridges: list[dict] = []

    from core.economic.economic_output import PLAYBOOK_SCHEMA_MAP

    for i in range(len(chain.steps) - 1):
        current = chain.steps[i]
        next_step = chain.steps[i + 1]

        current_schema = PLAYBOOK_SCHEMA_MAP.get(current.playbook_id, "")
        compatible = SCHEMA_FEEDS.get(current_schema, [])

        if next_step.playbook_id not in compatible:
            issues.append(
                f"step {i+1}→{i+2}: {current.playbook_id} ({current_schema}) "
                f"cannot feed {next_step.playbook_id}"
            )
        else:
            bridge = FIELD_BRIDGES.get(
                (current.playbook_id, next_step.playbook_id), {}
            )
            bridges.append({
                "from": current.playbook_id,
                "to": next_step.playbook_id,
                "field_mappings": bridge,
                "mapping_count": len(bridge),
            })

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "bridges": bridges,
        "step_count": len(chain.steps),
    }


def map_outputs_to_inputs(
    from_playbook: str,
    to_playbook: str,
    outputs: dict,
) -> dict:
    """
    Map outputs from one playbook to inputs for the next.

    Uses FIELD_BRIDGES for explicit mapping.
    Returns dict of input overrides for the next playbook.
    """
    bridge = FIELD_BRIDGES.get((from_playbook, to_playbook), {})
    mapped: dict = {}

    for output_field, input_field in bridge.items():
        value = outputs.get(output_field)
        if value is not None and value != "" and value != []:
            mapped[input_field] = value

    return mapped


def execute_chain(chain: PlaybookChain, goal: str) -> dict:
    """
    Execute a playbook chain, passing outputs between steps.

    Returns:
        {
            "ok": bool,
            "chain_id": str,
            "steps_completed": int,
            "results": [dict],  # per-step results
            "final_output": dict,  # assembled economic artifact from last step
        }
    """
    from core.planning.playbook import execute_playbook
    from core.economic.economic_output import assemble_economic_output

    validation = validate_chain(chain)
    if not validation["valid"]:
        return {
            "ok": False,
            "chain_id": chain.chain_id,
            "error": f"Invalid chain: {validation['issues']}",
            "steps_completed": 0,
            "results": [],
            "final_output": {},
        }

    results: list[dict] = []
    accumulated_outputs: dict = {}
    last_playbook_id = ""

    for i, step in enumerate(chain.steps):
        # Build inputs: goal + mapped outputs from previous step + overrides
        inputs = dict(accumulated_outputs)
        inputs.update(step.input_overrides)

        # Execute playbook
        step_goal = goal if i == 0 else f"{goal} (step {i+1}: {step.playbook_id})"
        result = execute_playbook(step.playbook_id, step_goal, inputs)

        results.append({
            "playbook_id": step.playbook_id,
            "ok": result.get("ok", False),
            "steps_completed": result.get("run", {}).get("steps_completed", 0),
        })

        if not result.get("ok"):
            return {
                "ok": False,
                "chain_id": chain.chain_id,
                "error": f"Step {i+1} ({step.playbook_id}) failed",
                "steps_completed": i,
                "results": results,
                "final_output": {},
            }

        # Extract outputs for next step
        run = result.get("run", {})
        step_outputs = []
        for s in run.get("steps", []):
            if isinstance(s, dict) and s.get("result"):
                res = s["result"]
                if isinstance(res, dict):
                    step_outputs.append(res.get("output", {}))

        # Map to next playbook inputs
        if i < len(chain.steps) - 1:
            next_pb = chain.steps[i + 1].playbook_id
            assembled = assemble_economic_output(step.playbook_id, step_outputs)
            accumulated_outputs = map_outputs_to_inputs(
                step.playbook_id, next_pb,
                assembled.get("data", {})
            )
        else:
            last_playbook_id = step.playbook_id

    # Assemble final output from last step
    final_output = {}
    if results and results[-1].get("ok"):
        final_output = assemble_economic_output(last_playbook_id, []).get("data", {})

    return {
        "ok": True,
        "chain_id": chain.chain_id,
        "steps_completed": len(chain.steps),
        "results": results,
        "final_output": final_output,
    }


# ── Built-in chains ──────────────────────────────────────────

VENTURE_CHAIN = PlaybookChain(
    chain_id="venture_creation",
    name="Full Venture Creation",
    description="Market analysis → Product creation → Growth experiment",
    steps=[
        CompositionStep(playbook_id="market_analysis", expected_schema="OpportunityReport"),
        CompositionStep(playbook_id="product_creation", expected_schema="BusinessConcept"),
        CompositionStep(playbook_id="growth_experiment", expected_schema="VenturePlan"),
    ],
)

OFFER_LAUNCH_CHAIN = PlaybookChain(
    chain_id="offer_launch",
    name="Offer Launch",
    description="Market analysis → Offer design → Landing page",
    steps=[
        CompositionStep(playbook_id="market_analysis", expected_schema="OpportunityReport"),
        CompositionStep(playbook_id="offer_design", expected_schema="BusinessConcept"),
        CompositionStep(playbook_id="landing_page", expected_schema="BusinessConcept"),
    ],
)

BUILT_IN_CHAINS = {
    "venture_creation": VENTURE_CHAIN,
    "offer_launch": OFFER_LAUNCH_CHAIN,
}
