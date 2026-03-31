"""
core/economic/economic_output.py — Economic output parser + validator.

Phase A: Ensures playbooks produce structured economic artifacts reliably.

Responsibilities:
  1. Map playbook outputs to economic schema types
  2. Validate schema completeness and field coherence
  3. Parse step results into typed economic objects
  4. Fail-open: returns untyped output if parsing fails

Design:
  - Zero modifications to ExecutionPlan or PlanRunner
  - Works on step outputs AFTER execution
  - Additive layer — all existing behavior preserved
"""
from __future__ import annotations

import structlog

log = structlog.get_logger("economic.output")


# ── Playbook → Schema mapping ────────────────────────────────

PLAYBOOK_SCHEMA_MAP: dict[str, str] = {
    "market_analysis": "OpportunityReport",
    "product_creation": "BusinessConcept",
    "offer_design": "BusinessConcept",
    "growth_experiment": "VenturePlan",
    "content_strategy": "MarketingPlan",
    "landing_page": "BusinessConcept",
}

# Skill → schema field mapping (which skill outputs feed which schema fields)
SKILL_SCHEMA_FIELDS: dict[str, dict[str, str]] = {
    # market_analysis playbook
    "market_research.basic": {
        "tam": "market_size_estimate",
        "problems": "problem_description",
        "opportunities": "feasibility_reasoning",
        "risks": "risk_flags",
        "trends": "market_size_reasoning",
        "sam": "market_size_reasoning_supplement",
        "som": "market_size_estimate_supplement",
    },
    "persona.basic": {
        "persona": "target_users",
        "pain_points": "pain_intensity_signal",
        "motivations": "target_users_supplement",
        "trigger_events": "feasibility_reasoning_supplement",
        "decision_drivers": "market_size_reasoning_supplement",
    },
    "competitor.analysis": {
        "competitors": "competition_overview",
        "gaps": "feasibility_reasoning_supplement",
        "threats": "risk_flags_supplement",
        "feature_matrix": "competition_overview_supplement",
        "positioning_map": "differentiation_hypothesis_supplement",
    },
    "positioning.basic": {
        "positioning_statement": "value_proposition",
        "unique_attributes": "differentiation_hypothesis",
        "category": "target_segment",
        "target_customer": "target_segment_supplement",
        "value_themes": "value_proposition_supplement",
    },
    # product_creation / offer_design
    "offer_design.basic": {
        "value_proposition": "value_proposition",
        "offer_structure": "solution_description",
        "differentiation": "differentiation_hypothesis",
        "usp": "value_proposition_supplement",
        "pricing": "pricing_logic",
    },
    "pricing.strategy": {
        "pricing_model": "revenue_logic",
        "tiers": "pricing_logic",
        "unit_economics": "pricing_logic_supplement",
        "willingness_to_pay": "market_size_reasoning_supplement",
        "competitive_positioning": "competition_overview_supplement",
    },
    "value_proposition.design": {
        "value_proposition": "value_proposition",
        "headline": "value_proposition",
        "elevator_pitch": "solution_description",
        "customer_profile": "target_segment",
        "fit_score": "confidence_signal",
    },
    "saas_scope.basic": {
        "must_features": "mvp_scope",
        "should_features": "mvp_scope_supplement",
        "cut_features": "execution_risks_supplement",
        "dependencies": "required_capabilities",
        "risk_assessment": "execution_risks",
        "dev_estimate": "estimated_timeline_weeks",
    },
    "spec.writing": {
        "problem_statement": "problem_description",
        "solution_design": "solution_description",
        "api_contracts": "required_capabilities",
        "implementation_plan": "mvp_scope",
        "edge_cases": "execution_risks",
    },
    # growth / strategy
    "strategy.reasoning": {
        "recommendation": "strategy_description",
        "situation_analysis": "feasibility_reasoning",
        "options": "strategy_description_supplement",
        "trade_offs": "risk_flags",
        "risks": "risk_flags_supplement",
        "next_steps": "milestones",
    },
    "growth.plan": {
        "growth_model": "strategy_description",
        "channels": "acquisition_channels",
        "retention_strategy": "growth_strategy_supplement",
        "metrics": "milestones_supplement",
        "experiments": "validation_steps",
        "timeline": "estimated_timeline_weeks",
    },
    "acquisition.basic": {
        "channels": "acquisition_channels",
        "organic_vs_paid": "growth_strategy",
        "content_strategy": "growth_strategy_supplement",
        "early_traction": "validation_steps",
        "metrics": "milestones_supplement",
    },
    # Additional skills
    "automation_opportunity.basic": {
        "processes": "mvp_scope",
        "roi_estimates": "pricing_logic",
        "recommended_tools": "required_capabilities",
        "feasibility_scores": "confidence_signal",
        "implementation_order": "milestones",
    },
    "funnel.design": {
        "funnel_stages": "solution_description",
        "metrics": "milestones_supplement",
        "automation": "required_capabilities_supplement",
        "bottleneck_analysis": "risk_flags",
    },
    "copywriting.basic": {
        "headlines": "value_proposition_supplement",
        "value_proposition": "value_proposition",
        "ctas": "solution_description_supplement",
        "objection_handlers": "differentiation_hypothesis_supplement",
    },
    "landing.structure": {
        "page_structure": "solution_description",
        "hero_section": "value_proposition",
        "social_proof_strategy": "differentiation_hypothesis",
        "cta_strategy": "growth_strategy",
    },
}


# ── Field alias resolution ───────────────────────────────────
# Maps LLM output field aliases to canonical schema fields.
# Used during assembly to fill schema gaps from semantically
# equivalent output fields.

FIELD_ALIASES: dict[str, list[str]] = {
    # OpportunityReport
    "pain_intensity": [
        "pain_severity", "urgency", "problem_severity",
        "pain_score", "severity_score", "pain_level",
    ],
    "confidence": [
        "confidence_score", "confidence_level", "certainty",
        "recommendation_confidence", "assessment_confidence",
        "reliability", "accuracy_estimate",
    ],
    "problem_description": [
        "problem_statement", "key_problem", "core_problem",
        "problem_summary", "main_problem", "problem",
    ],
    "market_size_estimate": [
        "total_addressable_market", "market_size", "market_opportunity",
        "tam_estimate", "TAM", "addressable_market",
    ],
    "target_users": [
        "target_audience", "ideal_customer", "target_customers",
        "user_segments", "customer_segments", "personas",
    ],
    "risk_flags": [
        "risks", "key_risks", "risk_factors", "threats",
        "risk_assessment", "potential_risks", "risk_signals",
    ],
    "competition_overview": [
        "competitive_landscape", "competitors", "competition",
        "market_competitors", "competitive_analysis",
    ],
    # BusinessConcept
    "value_proposition": [
        "headline", "core_value", "unique_value",
        "main_benefit", "key_value",
    ],
    "target_segment": [
        "target_market", "target_customer", "customer_segment",
        "ideal_customer_profile", "icp", "market_segment",
        "category",
    ],
    "solution_description": [
        "solution", "product_description", "offer_description",
        "service_description", "concept_description",
        "elevator_pitch", "offer_structure",
    ],
    "differentiation_hypothesis": [
        "differentiation", "unique_selling_point", "usp",
        "competitive_advantage", "moat",
    ],
    "delivery_mechanism": [
        "delivery_model", "distribution", "channel",
        "delivery_method",
    ],
    "revenue_logic": [
        "revenue_model", "monetization", "business_model",
        "pricing_model", "revenue_stream",
    ],
    # VenturePlan
    "mvp_scope": [
        "mvp", "mvp_features", "minimum_viable_product",
        "core_features", "must_features", "essential_features",
    ],
    "milestones": [
        "key_milestones", "timeline", "roadmap",
        "phases", "stages", "next_steps",
    ],
    "estimated_timeline_weeks": [
        "timeline_weeks", "duration_weeks", "dev_estimate",
        "estimated_duration", "time_estimate",
    ],
    "required_capabilities": [
        "requirements", "dependencies", "tech_stack",
        "capabilities_needed", "tools_needed",
    ],
    "execution_risks": [
        "implementation_risks", "execution_challenges",
        "project_risks", "risk_assessment",
    ],
    "validation_steps": [
        "validation_criteria", "success_criteria",
        "acceptance_criteria", "experiments",
    ],
    # FinancialModel
    "pricing_logic": [
        "pricing", "pricing_strategy", "pricing_model",
        "tiers", "price_tiers",
    ],
    "sensitivity_assumptions": [
        "assumptions", "key_assumptions", "model_assumptions",
        "sensitivity_factors",
    ],
}


def _resolve_via_alias(assembled: dict, content_pool: dict, field: str) -> None:
    """
    If a schema field is missing, try to fill it from known aliases.

    Mutates `assembled` in-place. Fail-open.
    """
    if field in assembled and assembled[field] not in (None, "", [], {}):
        return  # already filled
    aliases = FIELD_ALIASES.get(field, [])
    for alias in aliases:
        val = content_pool.get(alias)
        if val is not None and val != "" and val != [] and val != {}:
            assembled[field] = val
            return


# ── Safe numeric derivation ──────────────────────────────────

def _derive_pain_intensity(content_pool: dict) -> float | None:
    """
    Derive pain_intensity (0.0-1.0) from available signals.

    Sources (checked in order):
      1. Explicit numeric field: pain_intensity, pain_severity, pain_score
      2. Pain points list length → bounded heuristic (more pains = higher intensity)
      3. Problem severity scores inside problems list

    Returns float in [0.0, 1.0] or None if no signal available.
    """
    # 1. Direct numeric
    for key in ("pain_intensity", "pain_severity", "pain_score",
                "severity_score", "pain_level", "urgency"):
        val = content_pool.get(key)
        if isinstance(val, (int, float)) and val > 0:
            return max(0.0, min(1.0, float(val) if val <= 1.0 else val / 10.0))

    # 2. Pain points / problems list
    pain_points = content_pool.get("pain_points") or content_pool.get("problems")
    if isinstance(pain_points, list) and len(pain_points) > 0:
        # 2a. Check for severity scores inside dict items first (more precise)
        severities = []
        for item in pain_points:
            if isinstance(item, dict):
                for k in ("severity", "score", "intensity", "impact"):
                    v = item.get(k)
                    if isinstance(v, (int, float)):
                        severities.append(float(v))
                        break  # one score per item
        if severities:
            avg = sum(severities) / len(severities)
            return max(0.0, min(1.0, avg if avg <= 1.0 else avg / 10.0))

        # 2b. No severity scores → length heuristic
        # 1 point=0.3, 3 points=0.5, 5+=0.7, 10+=0.9
        count = len(pain_points)
        if count >= 10:
            return 0.9
        elif count >= 5:
            return 0.7
        elif count >= 3:
            return 0.5
        else:
            return 0.3

    return None


def _derive_confidence(content_pool: dict) -> float | None:
    """
    Derive confidence (0.0-1.0) from available signals.

    Sources (checked in order):
      1. Explicit: confidence, confidence_score, confidence_level, certainty
      2. Opportunity scores → weighted average
      3. Feasibility scores → bounded conversion
      4. Fit score (from value_proposition.design)

    Returns float in [0.0, 1.0] or None if no signal available.
    """
    # 1. Direct numeric
    for key in ("confidence", "confidence_score", "confidence_level",
                "certainty", "assessment_confidence", "reliability",
                "recommendation_confidence"):
        val = content_pool.get(key)
        if isinstance(val, (int, float)) and val > 0:
            return max(0.0, min(1.0, float(val) if val <= 1.0 else val / 10.0))

    # 2. Opportunity scores
    opps = content_pool.get("opportunities")
    if isinstance(opps, list) and len(opps) > 0:
        scores = []
        for item in opps:
            if isinstance(item, dict):
                for k in ("score", "rating", "confidence", "viability"):
                    v = item.get(k)
                    if isinstance(v, (int, float)):
                        scores.append(float(v))
        if scores:
            avg = sum(scores) / len(scores)
            return max(0.0, min(1.0, avg if avg <= 1.0 else avg / 10.0))

    # 3. Feasibility scores
    feas = content_pool.get("feasibility_scores")
    if isinstance(feas, (list, dict)):
        vals = feas.values() if isinstance(feas, dict) else feas
        numerics = [float(v) for v in vals if isinstance(v, (int, float))]
        if numerics:
            avg = sum(numerics) / len(numerics)
            return max(0.0, min(1.0, avg if avg <= 1.0 else avg / 10.0))

    # 4. Fit score
    fit = content_pool.get("fit_score")
    if isinstance(fit, (int, float)) and fit > 0:
        return max(0.0, min(1.0, float(fit) if fit <= 1.0 else fit / 10.0))

    return None


def _derive_estimated_difficulty(content_pool: dict) -> float | None:
    """
    Derive estimated_difficulty (0.0-1.0) from available signals.

    Sources: complexity, difficulty, dev_estimate analysis.
    """
    for key in ("complexity", "estimated_complexity", "difficulty",
                "difficulty_score", "technical_difficulty"):
        val = content_pool.get(key)
        if isinstance(val, (int, float)):
            return max(0.0, min(1.0, float(val) if val <= 1.0 else val / 10.0))
        if isinstance(val, str):
            lower = val.lower()
            if "high" in lower or "complex" in lower:
                return 0.8
            elif "medium" in lower or "moderate" in lower:
                return 0.5
            elif "low" in lower or "simple" in lower:
                return 0.3
    return None


# ── Schema validation ────────────────────────────────────────

# Minimum required fields per schema type
SCHEMA_REQUIRED_FIELDS: dict[str, list[str]] = {
    "OpportunityReport": ["problem_description", "pain_intensity", "confidence"],
    "BusinessConcept": ["value_proposition", "target_segment", "solution_description"],
    "VenturePlan": ["mvp_scope", "milestones", "estimated_timeline_weeks"],
    "FinancialModel": ["pricing_logic", "sensitivity_assumptions"],
    "ComplianceChecklist": ["jurisdiction_assumptions", "items"],
    "MarketingPlan": [],  # flexible
}

# Confidence thresholds
MIN_CONFIDENCE = 0.1  # very lenient — just not zero


def validate_economic_output(data: dict, schema_type: str) -> dict:
    """
    Validate an economic output dict against schema requirements.

    Returns:
        {
            "valid": bool,
            "schema_type": str,
            "completeness": float (0.0-1.0),
            "issues": [str],
            "field_count": int,
        }

    Fail-open: always returns a result dict, never raises.
    """
    try:
        issues: list[str] = []
        required = SCHEMA_REQUIRED_FIELDS.get(schema_type, [])

        # Check required fields
        present = 0
        for field in required:
            val = data.get(field)
            if val is None or val == "" or val == [] or val == {}:
                issues.append(f"missing_or_empty: {field}")
            else:
                present += 1

        completeness = present / len(required) if required else 1.0

        # Check confidence threshold
        confidence = data.get("confidence")
        if confidence is not None and isinstance(confidence, (int, float)):
            if confidence < MIN_CONFIDENCE:
                issues.append(f"confidence_below_threshold: {confidence} < {MIN_CONFIDENCE}")

        # Check field count (non-trivial output)
        non_empty = sum(1 for v in data.values()
                        if v is not None and v != "" and v != [] and v != {})

        return {
            "valid": len(issues) == 0,
            "schema_type": schema_type,
            "completeness": round(completeness, 3),
            "issues": issues,
            "field_count": non_empty,
        }
    except Exception as e:
        return {
            "valid": False,
            "schema_type": schema_type,
            "completeness": 0.0,
            "issues": [f"validation_error: {str(e)[:100]}"],
            "field_count": 0,
        }


# ── Output assembly ──────────────────────────────────────────

def assemble_economic_output(
    playbook_id: str,
    step_outputs: list[dict],
) -> dict:
    """
    Assemble step outputs into a structured economic artifact.

    Takes raw step results from PlanRunner and:
      1. Identifies the target schema from playbook_id
      2. Maps skill output fields to schema fields
      3. Validates the assembled output
      4. Returns typed dict with schema tag

    Returns:
        {
            "schema": str,
            "data": dict (the assembled artifact),
            "validation": dict (validation result),
            "source_steps": int,
        }

    Fail-open: returns partial data if assembly is incomplete.
    """
    schema_type = PLAYBOOK_SCHEMA_MAP.get(playbook_id, "")
    if not schema_type:
        return {
            "schema": "",
            "data": {},
            "validation": {"valid": False, "issues": ["unknown_playbook"]},
            "source_steps": len(step_outputs),
        }

    assembled: dict = {"schema": schema_type, "version": "1.0"}
    # Collect all content fields from all steps for alias resolution
    content_pool: dict = {}

    for step_out in step_outputs:
        if not isinstance(step_out, dict):
            continue

        # Get skill_id from step output
        skill_id = step_out.get("skill_id", "")
        content = step_out.get("content", {})
        if not content:
            # Fallback: use the step output itself
            content = step_out

        # Accumulate all content into pool for alias resolution
        for k, v in content.items():
            if v is not None and v != "" and v != [] and v != {}:
                if k not in content_pool:
                    content_pool[k] = v

        # Map skill fields to schema fields
        field_map = SKILL_SCHEMA_FIELDS.get(skill_id, {})
        for skill_field, schema_field in field_map.items():
            value = content.get(skill_field)
            if value is not None and value != "" and value != []:
                # Don't overwrite existing values (skip _supplement fields)
                if schema_field.endswith("_supplement"):
                    continue
                if schema_field not in assembled or assembled[schema_field] in (None, "", []):
                    assembled[schema_field] = value

    # Phase 2: Resolve schema fields via field aliases
    required = SCHEMA_REQUIRED_FIELDS.get(schema_type, [])
    for field in required:
        _resolve_via_alias(assembled, content_pool, field)

    # Phase 3: Safe numeric derivation for required float fields
    if schema_type == "OpportunityReport":
        if "pain_intensity" not in assembled or assembled.get("pain_intensity") in (None, 0, 0.0):
            derived = _derive_pain_intensity(content_pool)
            if derived is not None:
                assembled["pain_intensity"] = derived
        if "confidence" not in assembled or assembled.get("confidence") in (None, 0, 0.0):
            derived = _derive_confidence(content_pool)
            if derived is not None:
                assembled["confidence"] = derived
        if "estimated_difficulty" not in assembled or assembled.get("estimated_difficulty") in (None, 0, 0.0):
            derived = _derive_estimated_difficulty(content_pool)
            if derived is not None:
                assembled["estimated_difficulty"] = derived

    validation = validate_economic_output(assembled, schema_type)

    log.debug("economic_output_assembled",
              playbook=playbook_id, schema=schema_type,
              completeness=validation["completeness"],
              fields=validation["field_count"])

    return {
        "schema": schema_type,
        "data": assembled,
        "validation": validation,
        "source_steps": len(step_outputs),
    }


def parse_step_to_economic(step_output: dict, skill_id: str) -> dict | None:
    """
    Try to parse a single step output into an economic schema object.

    Returns the typed dict if successful, None otherwise.
    Fail-open: never raises.
    """
    try:
        from kernel.contracts.economic import parse_economic_output

        content = step_output.get("content", {})
        if not content:
            content = step_output

        # Check if content already has a schema tag
        if "schema" in content:
            obj = parse_economic_output(content)
            if obj:
                return obj.to_dict()

        return None
    except Exception:
        return None
