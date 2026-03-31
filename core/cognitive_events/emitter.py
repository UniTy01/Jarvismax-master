"""
core/cognitive_events/emitter.py — Convenience emitter functions.

Thin wrappers around journal.append() for each event type.
All functions are fail-open — never crash the caller.
"""
from __future__ import annotations

import structlog

from core.cognitive_events.types import (
    CognitiveEvent, EventType, EventSeverity,
)
from core.cognitive_events.store import get_journal

log = structlog.get_logger("cognitive_events.emitter")


def emit(
    event_type: EventType,
    summary: str,
    source: str = "",
    mission_id: str = "",
    session_id: str = "",
    severity: EventSeverity = EventSeverity.INFO,
    confidence: float | None = None,
    payload: dict | None = None,
    tags: list[str] | None = None,
) -> CognitiveEvent | None:
    """
    Emit a cognitive event to the journal.

    Returns the event on success, None on failure. Never raises.
    """
    try:
        event = CognitiveEvent(
            event_type=event_type,
            summary=summary,
            source=source,
            mission_id=mission_id,
            session_id=session_id,
            severity=severity,
            confidence=confidence,
            payload=payload or {},
            tags=tags or [],
        )
        return get_journal().append(event)
    except Exception as e:
        log.debug("cognitive_event_emit_failed", err=str(e)[:60])
        return None


# ── Typed convenience emitters ────────────────────────────────
# Each wraps emit() with the correct EventType.

def emit_mission_created(
    mission_id: str, goal: str, mode: str = "auto", **extra
) -> CognitiveEvent | None:
    return emit(
        EventType.MISSION_CREATED,
        summary=f"Mission created: {goal[:100]}",
        source="meta_orchestrator",
        mission_id=mission_id,
        payload={"goal": goal[:200], "mode": mode, **extra},
    )


def emit_mission_completed(
    mission_id: str, duration_ms: float = 0, confidence: float = 0.0, **extra
) -> CognitiveEvent | None:
    return emit(
        EventType.MISSION_COMPLETED,
        summary=f"Mission completed in {duration_ms:.0f}ms",
        source="meta_orchestrator",
        mission_id=mission_id,
        confidence=confidence,
        payload={"duration_ms": duration_ms, **extra},
    )


def emit_mission_failed(
    mission_id: str, error: str = "", error_class: str = "", **extra
) -> CognitiveEvent | None:
    return emit(
        EventType.MISSION_FAILED,
        summary=f"Mission failed: {error[:100]}",
        source="meta_orchestrator",
        mission_id=mission_id,
        severity=EventSeverity.ERROR,
        payload={"error": error[:300], "error_class": error_class, **extra},
    )


def emit_capability_resolved(
    mission_id: str, capabilities: list[str], **extra
) -> CognitiveEvent | None:
    return emit(
        EventType.CAPABILITY_RESOLVED,
        summary=f"Resolved {len(capabilities)} capabilities: {', '.join(capabilities[:3])}",
        source="capability_routing",
        mission_id=mission_id,
        payload={"capabilities": capabilities[:10], **extra},
    )


def emit_provider_selected(
    mission_id: str, capability_id: str, provider_id: str,
    score: float = 0.0, alternatives: int = 0, **extra
) -> CognitiveEvent | None:
    return emit(
        EventType.PROVIDER_SELECTED,
        summary=f"{capability_id} → {provider_id} (score={score:.3f})",
        source="capability_routing",
        mission_id=mission_id,
        confidence=score,
        payload={
            "capability_id": capability_id,
            "provider_id": provider_id,
            "score": score,
            "alternatives": alternatives,
            **extra,
        },
    )


def emit_risk_evaluated(
    mission_id: str, risk_level: str, needs_approval: bool = False, **extra
) -> CognitiveEvent | None:
    sev = EventSeverity.WARNING if risk_level in ("high", "critical") else EventSeverity.INFO
    return emit(
        EventType.RISK_EVALUATED,
        summary=f"Risk={risk_level}, approval={'required' if needs_approval else 'not needed'}",
        source="policy_engine",
        mission_id=mission_id,
        severity=sev,
        payload={"risk_level": risk_level, "needs_approval": needs_approval, **extra},
    )


def emit_approval_requested(
    mission_id: str, item_id: str = "", action: str = "", **extra
) -> CognitiveEvent | None:
    return emit(
        EventType.APPROVAL_REQUESTED,
        summary=f"Approval requested: {action[:60]}",
        source="approval_system",
        mission_id=mission_id,
        severity=EventSeverity.WARNING,
        payload={"item_id": item_id, "action": action, **extra},
    )


def emit_approval_resolved(
    mission_id: str, granted: bool, item_id: str = "", **extra
) -> CognitiveEvent | None:
    etype = EventType.APPROVAL_GRANTED if granted else EventType.APPROVAL_DENIED
    return emit(
        etype,
        summary=f"Approval {'granted' if granted else 'denied'}",
        source="approval_system",
        mission_id=mission_id,
        payload={"granted": granted, "item_id": item_id, **extra},
    )


def emit_tool_execution(
    mission_id: str, tool_name: str, success: bool,
    duration_ms: float = 0, error: str = "", **extra
) -> CognitiveEvent | None:
    etype = EventType.TOOL_EXECUTION_COMPLETED if success else EventType.TOOL_EXECUTION_FAILED
    sev = EventSeverity.INFO if success else EventSeverity.WARNING
    return emit(
        etype,
        summary=f"Tool {tool_name}: {'ok' if success else 'failed'} ({duration_ms:.0f}ms)",
        source="tool_executor",
        mission_id=mission_id,
        severity=sev,
        payload={
            "tool_name": tool_name, "success": success,
            "duration_ms": duration_ms, "error": error[:200],
            **extra,
        },
    )


def emit_patch_proposed(
    patch_id: str, description: str, files: list[str] | None = None, **extra
) -> CognitiveEvent | None:
    return emit(
        EventType.PATCH_PROPOSED,
        summary=f"Patch proposed: {description[:100]}",
        source="self_improvement",
        payload={"patch_id": patch_id, "files": (files or [])[:10], **extra},
        tags=["lab", "self-improvement"],
    )


def emit_patch_validated(
    patch_id: str, passed: bool, tests_run: int = 0, **extra
) -> CognitiveEvent | None:
    return emit(
        EventType.PATCH_VALIDATED if passed else EventType.PATCH_REJECTED,
        summary=f"Patch {'passed' if passed else 'failed'} validation ({tests_run} tests)",
        source="self_improvement",
        severity=EventSeverity.INFO if passed else EventSeverity.WARNING,
        payload={"patch_id": patch_id, "passed": passed, "tests_run": tests_run, **extra},
        tags=["lab", "self-improvement"],
    )


def emit_lesson_stored(
    lesson_summary: str, source_subsystem: str = "self_improvement", **extra
) -> CognitiveEvent | None:
    return emit(
        EventType.LESSON_STORED,
        summary=f"Lesson: {lesson_summary[:100]}",
        source=source_subsystem,
        payload={"lesson": lesson_summary[:500], **extra},
        tags=["lab", "learning"],
    )


def emit_runtime_health(
    component: str, healthy: bool, detail: str = "", **extra
) -> CognitiveEvent | None:
    etype = EventType.RUNTIME_RECOVERED if healthy else EventType.RUNTIME_DEGRADED
    sev = EventSeverity.INFO if healthy else EventSeverity.WARNING
    return emit(
        etype,
        summary=f"{component}: {'recovered' if healthy else 'degraded'} — {detail[:60]}",
        source="health_monitor",
        severity=sev,
        payload={"component": component, "healthy": healthy, "detail": detail[:200], **extra},
        tags=["health"],
    )


def emit_self_model_refreshed(
    readiness: float, capabilities: int = 0, duration_ms: float = 0, **extra
) -> CognitiveEvent | None:
    return emit(
        EventType.SELF_MODEL_REFRESHED,
        summary=f"Self-model refreshed: readiness={readiness:.0%}, {capabilities} capabilities",
        source="self_model",
        payload={
            "readiness": readiness, "capabilities": capabilities,
            "duration_ms": duration_ms, **extra,
        },
    )
