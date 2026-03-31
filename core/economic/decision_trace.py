"""
core/economic/decision_trace.py — Decision traceability for economic outputs.

Phase F: Every economic artifact must expose its decision rationale.

Structure:
  DecisionTrace:
    - rationale (why this decision)
    - assumptions (what was assumed)
    - risk_factors (what could go wrong)
    - confidence (how sure)
    - evidence_sources (what informed the decision)
    - alternatives_considered (what else was evaluated)

Integrates with ExecutionResult.output metadata.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


@dataclass
class DecisionTrace:
    """Structured explanation of an economic decision."""
    trace_id: str = ""
    decision_type: str = ""  # "opportunity_selected", "concept_chosen", "plan_created"
    rationale: str = ""
    assumptions: list[str] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    confidence: float = 0.5
    evidence_sources: list[str] = field(default_factory=list)
    alternatives_considered: list[str] = field(default_factory=list)
    schema_ref: str = ""  # "OpportunityReport:opp-xxx" or similar
    created_at: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.trace_id:
            self.trace_id = f"dt-{uuid.uuid4().hex[:8]}"

    def validate(self) -> list[str]:
        errors = []
        if not self.rationale:
            errors.append("rationale is required")
        if not self.assumptions:
            errors.append("at least one assumption is required")
        if not 0.0 <= self.confidence <= 1.0:
            errors.append("confidence must be 0.0-1.0")
        return errors

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "decision_type": self.decision_type,
            "rationale": self.rationale[:500],
            "assumptions": self.assumptions[:10],
            "risk_factors": self.risk_factors[:10],
            "confidence": round(self.confidence, 3),
            "evidence_sources": self.evidence_sources[:10],
            "alternatives_considered": self.alternatives_considered[:5],
            "schema_ref": self.schema_ref,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DecisionTrace":
        return cls(
            trace_id=d.get("trace_id", ""),
            decision_type=d.get("decision_type", ""),
            rationale=d.get("rationale", ""),
            assumptions=list(d.get("assumptions", [])),
            risk_factors=list(d.get("risk_factors", [])),
            confidence=float(d.get("confidence", 0.5)),
            evidence_sources=list(d.get("evidence_sources", [])),
            alternatives_considered=list(d.get("alternatives_considered", [])),
            schema_ref=d.get("schema_ref", ""),
            created_at=float(d.get("created_at", time.time())),
        )


def build_trace_from_output(
    schema_type: str,
    data: dict,
    validation: dict,
) -> DecisionTrace:
    """
    Build a DecisionTrace from an economic output and its validation.

    Extracts rationale/assumptions/risks from the data fields.
    Fail-open: returns minimal trace if extraction fails.
    """
    try:
        # Extract rationale from schema fields
        rationale = ""
        assumptions: list[str] = []
        risk_factors: list[str] = []
        confidence = 0.5
        evidence: list[str] = []

        if schema_type == "OpportunityReport":
            rationale = data.get("feasibility_reasoning", "")
            assumptions = [
                f"Market size: {data.get('market_size_estimate', 'unknown')}",
                f"Pain intensity: {data.get('pain_intensity', 'unknown')}",
            ]
            risk_factors = data.get("risk_flags", [])
            confidence = float(data.get("confidence", 0.5))
            evidence = data.get("data_sources", [])

        elif schema_type == "BusinessConcept":
            rationale = data.get("differentiation_hypothesis", "")
            assumptions = [
                f"Target: {data.get('target_segment', 'unknown')}",
                f"Delivery: {data.get('delivery_mechanism', 'unknown')}",
                f"Revenue: {data.get('revenue_logic', 'unknown')}",
            ]
            risk_factors = [
                f"Complexity: {data.get('estimated_complexity', 'unknown')}",
            ]

        elif schema_type == "VenturePlan":
            rationale = data.get("mvp_scope", "")
            assumptions = [
                f"Timeline: {data.get('estimated_timeline_weeks', 'unknown')} weeks",
            ]
            risk_factors = data.get("execution_risks", [])

        elif schema_type == "FinancialModel":
            rationale = data.get("break_even_reasoning", "")
            assumptions = data.get("sensitivity_assumptions", [])
            risk_factors = [
                f"Margin: {data.get('expected_margin', 'unknown')}",
            ]

        elif schema_type == "ComplianceChecklist":
            rationale = "Regulatory compliance assessment"
            assumptions = data.get("jurisdiction_assumptions", [])
            risk_factors = data.get("risk_flags", [])

        # Add validation info
        if not assumptions:
            assumptions = ["No explicit assumptions extracted"]

        # Build schema reference
        id_field_map = {
            "OpportunityReport": "report_id",
            "BusinessConcept": "concept_id",
            "VenturePlan": "plan_id",
            "FinancialModel": "model_id",
            "ComplianceChecklist": "checklist_id",
        }
        id_field = id_field_map.get(schema_type, "")
        obj_id = data.get(id_field, "")
        schema_ref = f"{schema_type}:{obj_id}" if obj_id else schema_type

        return DecisionTrace(
            decision_type=f"{schema_type.lower()}_generated",
            rationale=rationale or f"Generated via {schema_type} schema",
            assumptions=assumptions,
            risk_factors=risk_factors,
            confidence=confidence,
            evidence_sources=evidence,
            schema_ref=schema_ref,
        )
    except Exception:
        return DecisionTrace(
            decision_type=f"{schema_type.lower()}_generated",
            rationale=f"Generated via {schema_type} schema",
            assumptions=["Auto-generated trace — extraction failed"],
        )


def enrich_output_with_trace(output: dict, trace: DecisionTrace) -> dict:
    """
    Add decision trace to an execution output dict.

    Returns enriched dict (does not modify input).
    """
    enriched = dict(output)
    enriched["decision_trace"] = trace.to_dict()
    return enriched
