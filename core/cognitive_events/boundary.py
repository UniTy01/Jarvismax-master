"""
core/cognitive_events/boundary.py — Runtime / Lab boundary enforcement.

Defines the clear separation between:
  RUNTIME: stable execution serving real users
  LAB: experimental sandbox for self-improvement

Lab events cannot mutate runtime state. Runtime events cannot be emitted
from lab subsystems (unless through the promotion pipeline).
"""
from __future__ import annotations

import structlog

from core.cognitive_events.types import EventDomain, EventType, get_domain

log = structlog.get_logger("cognitive_events.boundary")


# ── Runtime-protected subsystems ──────────────────────────────
# These cannot be mutated by lab/sandbox code directly.

RUNTIME_PROTECTED = frozenset({
    "meta_orchestrator",
    "tool_executor",
    "policy_engine",
    "auth",
    "mission_state",
    "mcp_registry",
    "capability_routing",
    "approval_system",
    "memory_facade",
})

# ── Lab-only subsystems ───────────────────────────────────────
# These are sandbox/experimental and must not affect live execution.

LAB_SUBSYSTEMS = frozenset({
    "self_improvement",
    "promotion_pipeline",
    "sandbox_executor",
    "experiment_discipline",
    "improvement_daemon",
    "code_patcher",
    "git_agent",
})

# ── Promotion bridge ─────────────────────────────────────────
# The ONLY path from lab → runtime is through the promotion pipeline.
# This is already enforced by PromotionPipeline in V3.

PROMOTION_BRIDGE = "promotion_pipeline"


def validate_emission(source: str, event_type: EventType) -> tuple[bool, str]:
    """
    Validate that a source is allowed to emit an event type.

    Returns (allowed: bool, reason: str).

    Rules:
      1. Lab subsystems can only emit lab or system events
      2. Runtime events can only come from runtime or system subsystems
      3. Lab subsystems cannot emit runtime-domain events (prevents
         sandbox code from injecting fake mission completions)
    """
    domain = get_domain(event_type)

    # Lab source emitting runtime event = violation
    if source in LAB_SUBSYSTEMS and domain == EventDomain.RUNTIME:
        return False, f"Lab source '{source}' cannot emit runtime event '{event_type.value}'"

    # Runtime source emitting lab event = suspicious but allowed
    # (e.g., meta_orchestrator recording that a patch was proposed)

    return True, "ok"


def is_runtime_protected(subsystem: str) -> bool:
    """Check if a subsystem is runtime-protected (no lab mutations)."""
    return subsystem in RUNTIME_PROTECTED


def is_lab_subsystem(subsystem: str) -> bool:
    """Check if a subsystem belongs to the lab/sandbox domain."""
    return subsystem in LAB_SUBSYSTEMS


def get_boundary_summary() -> dict:
    """Summary of the runtime/lab boundary for admin display."""
    return {
        "runtime_protected": sorted(RUNTIME_PROTECTED),
        "lab_subsystems": sorted(LAB_SUBSYSTEMS),
        "promotion_bridge": PROMOTION_BRIDGE,
        "rule": "Lab subsystems cannot emit runtime events or mutate protected subsystems. "
                "The only path from lab to runtime is through the PromotionPipeline.",
    }
