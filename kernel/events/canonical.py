"""
kernel/events/canonical.py — Canonical kernel events and emitter.

Defines the complete set of kernel-level events and provides a
typed emitter that delegates to the existing cognitive event journal.
"""
from __future__ import annotations

import structlog
from kernel.contracts.types import SystemEvent

log = structlog.get_logger("kernel.events")

# ══════════════════════════════════════════════════════════════
# Canonical Event Types
# ══════════════════════════════════════════════════════════════

CANONICAL_EVENTS = {
    # Mission lifecycle
    "mission.created": "A new mission was created from a goal",
    "mission.planning": "Mission entered planning phase",
    "mission.executing": "Mission execution started",
    "mission.completed": "Mission completed successfully",
    "mission.failed": "Mission failed",
    "mission.cancelled": "Mission was cancelled",

    # Plan lifecycle
    "plan.generated": "Execution plan was generated",
    "plan.validated": "Plan passed validation",
    "plan.approved": "Plan was approved for execution",
    "plan.rejected": "Plan was rejected",

    # Step lifecycle
    "step.started": "Plan step execution started",
    "step.completed": "Plan step completed successfully",
    "step.failed": "Plan step failed",
    "step.needs_approval": "Step requires approval before execution",
    "step.approved": "Step was approved",

    # Tool invocation
    "tool.invoked": "External tool was invoked",
    "tool.completed": "Tool invocation completed",
    "tool.failed": "Tool invocation failed",

    # Skill execution
    "skill.prepared": "Skill prompt context was prepared",
    "skill.completed": "Skill execution completed",

    # Memory
    "memory.written": "Memory record was created or updated",
    "memory.recalled": "Memory was recalled for use",

    # Policy
    "policy.evaluated": "Policy engine evaluated an action",
    "policy.blocked": "Policy engine blocked an action",

    # Approval
    "approval.requested": "Human approval was requested",
    "approval.granted": "Approval was granted",
    "approval.denied": "Approval was denied",

    # System
    "kernel.booted": "Kernel runtime initialized",
    "kernel.shutdown": "Kernel runtime shutting down",
}


class KernelEventEmitter:
    """
    Typed event emitter that bridges kernel contracts to the existing
    cognitive event journal.

    All emissions are fail-open — kernel operation is never blocked
    by event infrastructure failure.
    """

    def emit(self, event: SystemEvent) -> bool:
        """Emit a kernel event. Returns True if successfully emitted."""
        errors = event.validate()
        if errors:
            log.debug("kernel_event_invalid", errors=errors)
            return False

        if event.event_type not in CANONICAL_EVENTS:
            log.debug("kernel_event_unknown_type", event_type=event.event_type)
            # Still emit — non-canonical events allowed but logged

        # Delegate to existing cognitive event journal
        try:
            from core.cognitive_events.emitter import emit as ce_emit
            from core.cognitive_events.types import EventType, EventSeverity

            severity_map = {
                "debug": EventSeverity.DEBUG,
                "info": EventSeverity.INFO,
                "warning": EventSeverity.WARNING,
                "error": EventSeverity.ERROR,
                "critical": EventSeverity.CRITICAL,
            }

            ce_emit(
                EventType.SYSTEM_EVENT,
                summary=f"[kernel] {event.summary}",
                source=event.source or "kernel",
                mission_id=event.mission_id,
                severity=severity_map.get(event.severity, EventSeverity.INFO),
                payload={
                    "kernel_event_type": event.event_type,
                    "plan_id": event.plan_id,
                    "step_id": event.step_id,
                    **event.payload,
                },
                tags=["kernel", event.event_type.split(".")[0]],
            )
            return True
        except Exception as e:
            log.debug("kernel_event_emit_failed", err=str(e)[:80])
            return False

    def mission_created(self, mission_id: str, goal: str, **extra) -> bool:
        return self.emit(SystemEvent(
            event_type="mission.created", source="kernel",
            summary=f"Mission created: {goal[:80]}",
            mission_id=mission_id, payload={"goal": goal[:200], **extra},
        ))

    def plan_generated(self, plan_id: str, mission_id: str = "", steps: int = 0, **extra) -> bool:
        return self.emit(SystemEvent(
            event_type="plan.generated", source="kernel",
            summary=f"Plan generated with {steps} steps",
            mission_id=mission_id, plan_id=plan_id,
            payload={"step_count": steps, **extra},
        ))

    def plan_approved(self, plan_id: str, decided_by: str = "", **extra) -> bool:
        return self.emit(SystemEvent(
            event_type="plan.approved", source="kernel",
            summary=f"Plan approved by {decided_by}",
            plan_id=plan_id, payload={"decided_by": decided_by, **extra},
        ))

    def step_started(self, step_id: str, plan_id: str = "", step_name: str = "", **extra) -> bool:
        return self.emit(SystemEvent(
            event_type="step.started", source="kernel",
            summary=f"Step started: {step_name}",
            plan_id=plan_id, step_id=step_id, payload=extra,
        ))

    def step_completed(self, step_id: str, plan_id: str = "", **extra) -> bool:
        return self.emit(SystemEvent(
            event_type="step.completed", source="kernel",
            summary=f"Step completed: {step_id}",
            plan_id=plan_id, step_id=step_id, payload=extra,
        ))

    def step_failed(self, step_id: str, error: str = "", plan_id: str = "", **extra) -> bool:
        return self.emit(SystemEvent(
            event_type="step.failed", source="kernel",
            summary=f"Step failed: {error[:80]}",
            plan_id=plan_id, step_id=step_id, severity="warning",
            payload={"error": error[:200], **extra},
        ))

    def tool_invoked(self, tool_id: str, step_id: str = "", **extra) -> bool:
        return self.emit(SystemEvent(
            event_type="tool.invoked", source="kernel",
            summary=f"Tool invoked: {tool_id}",
            step_id=step_id, payload={"tool_id": tool_id, **extra},
        ))

    def approval_requested(self, target_id: str, action: str = "", **extra) -> bool:
        return self.emit(SystemEvent(
            event_type="approval.requested", source="kernel",
            summary=f"Approval requested: {action[:80]}",
            severity="warning",
            payload={"target_id": target_id, "action": action[:200], **extra},
        ))

    def memory_written(self, record_id: str, memory_type: str = "", **extra) -> bool:
        return self.emit(SystemEvent(
            event_type="memory.written", source="kernel",
            summary=f"Memory written: {memory_type} {record_id[:20]}",
            payload={"record_id": record_id, "memory_type": memory_type, **extra},
        ))


# ── Singleton ─────────────────────────────────────────────────

_emitter: KernelEventEmitter | None = None


def get_kernel_emitter() -> KernelEventEmitter:
    global _emitter
    if _emitter is None:
        _emitter = KernelEventEmitter()
    return _emitter
