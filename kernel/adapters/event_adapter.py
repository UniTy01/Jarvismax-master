"""
kernel/adapters/event_adapter.py — Maps existing cognitive events to kernel canonical events.

Provides bidirectional mapping between:
  - core.cognitive_events.types.EventType (existing, operational)
  - kernel.events.canonical.CANONICAL_EVENTS (kernel, authoritative)
"""
from __future__ import annotations


# ══════════════════════════════════════════════════════════════
# core EventType.value → kernel canonical event type
# ══════════════════════════════════════════════════════════════

CORE_TO_KERNEL_EVENT: dict[str, str] = {
    # Mission lifecycle
    "mission.created":          "mission.created",
    "mission.planned":          "plan.generated",
    "mission.started":          "mission.executing",
    "mission.completed":        "mission.completed",
    "mission.failed":           "mission.failed",

    # Routing
    "routing.capability_resolved": "step.started",     # capability resolution is step prep
    "routing.provider_selected":   "step.started",     # provider selection is step prep
    "routing.provider_fallback":   "step.started",

    # Risk & approval
    "risk.evaluated":           "policy.evaluated",
    "approval.requested":       "approval.requested",
    "approval.granted":         "approval.granted",
    "approval.denied":          "approval.denied",

    # Execution
    "execution.tool_requested": "tool.invoked",
    "execution.tool_completed": "tool.completed",
    "execution.tool_failed":    "tool.failed",

    # Memory
    "memory.write":             "memory.written",
    "memory.retrieve":          "memory.recalled",

    # Lab events (map to step lifecycle in kernel)
    "lab.patch_proposed":       "step.started",
    "lab.patch_validated":      "step.completed",
    "lab.patch_rejected":       "step.failed",
    "lab.patch_promoted":       "step.completed",
    "lab.lesson_stored":        "memory.written",

    # Runtime health
    "runtime.degraded":         "kernel.shutdown",  # degraded ≈ partial shutdown
    "runtime.recovered":        "kernel.booted",    # recovered ≈ partial boot
    "runtime.alert":            "policy.blocked",   # alert ≈ policy concern

    # Self-model
    "self_model.refreshed":     "kernel.booted",    # refresh ≈ partial re-init

    # System
    "system.event":             "kernel.booted",    # generic → map to kernel event
}


def core_event_to_kernel_type(core_event_value: str) -> str | None:
    """
    Map a core cognitive event type to the corresponding kernel canonical event type.

    Returns None if no mapping exists.
    """
    return CORE_TO_KERNEL_EVENT.get(core_event_value)


def kernel_to_core_event_type(kernel_event_type: str) -> list[str]:
    """
    Reverse map: kernel event type → all core event types that map to it.

    Returns list because multiple core events may map to one kernel event.
    """
    return [
        core_val for core_val, kernel_val in CORE_TO_KERNEL_EVENT.items()
        if kernel_val == kernel_event_type
    ]
