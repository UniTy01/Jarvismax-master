"""
core/cognitive_events/types.py — Event type definitions.

All cognitive events are typed, timestamped, and carry structured payloads.
Events are append-only and immutable once created.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventType(str, Enum):
    """Canonical event types for the cognitive journal."""

    # ── Mission lifecycle ─────────────────────────────────────
    MISSION_CREATED = "mission.created"
    MISSION_PLANNED = "mission.planned"
    MISSION_STARTED = "mission.started"
    MISSION_COMPLETED = "mission.completed"
    MISSION_FAILED = "mission.failed"

    # ── Capability routing ────────────────────────────────────
    CAPABILITY_RESOLVED = "routing.capability_resolved"
    PROVIDER_SELECTED = "routing.provider_selected"
    PROVIDER_FALLBACK = "routing.provider_fallback"

    # ── Risk & approval ───────────────────────────────────────
    RISK_EVALUATED = "risk.evaluated"
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_GRANTED = "approval.granted"
    APPROVAL_DENIED = "approval.denied"

    # ── Execution ─────────────────────────────────────────────
    TOOL_EXECUTION_REQUESTED = "execution.tool_requested"
    TOOL_EXECUTION_COMPLETED = "execution.tool_completed"
    TOOL_EXECUTION_FAILED = "execution.tool_failed"

    # ── Memory ────────────────────────────────────────────────
    MEMORY_WRITE = "memory.write"
    MEMORY_RETRIEVE = "memory.retrieve"

    # ── Self-model ────────────────────────────────────────────
    SELF_MODEL_REFRESHED = "self_model.refreshed"

    # ── Lab / self-improvement ────────────────────────────────
    PATCH_PROPOSED = "lab.patch_proposed"
    PATCH_VALIDATED = "lab.patch_validated"
    PATCH_REJECTED = "lab.patch_rejected"
    PATCH_PROMOTED = "lab.patch_promoted"
    LESSON_STORED = "lab.lesson_stored"

    # ── Runtime health ────────────────────────────────────────
    RUNTIME_DEGRADED = "runtime.degraded"
    RUNTIME_RECOVERED = "runtime.recovered"
    RUNTIME_ALERT = "runtime.alert"

    # ── Generic ───────────────────────────────────────────────
    SYSTEM_EVENT = "system.event"


class EventSeverity(str, Enum):
    """How significant is this event?"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EventDomain(str, Enum):
    """Which domain does this event belong to?"""
    RUNTIME = "runtime"     # Stable runtime — serves real users
    LAB = "lab"             # Experimental — sandbox/self-improvement
    SYSTEM = "system"       # Infrastructure — health, config, startup


# ── Event type → domain mapping ───────────────────────────────
# Used to enforce runtime/lab boundary

_DOMAIN_MAP: dict[EventType, EventDomain] = {
    # Runtime events
    EventType.MISSION_CREATED: EventDomain.RUNTIME,
    EventType.MISSION_PLANNED: EventDomain.RUNTIME,
    EventType.MISSION_STARTED: EventDomain.RUNTIME,
    EventType.MISSION_COMPLETED: EventDomain.RUNTIME,
    EventType.MISSION_FAILED: EventDomain.RUNTIME,
    EventType.CAPABILITY_RESOLVED: EventDomain.RUNTIME,
    EventType.PROVIDER_SELECTED: EventDomain.RUNTIME,
    EventType.PROVIDER_FALLBACK: EventDomain.RUNTIME,
    EventType.RISK_EVALUATED: EventDomain.RUNTIME,
    EventType.APPROVAL_REQUESTED: EventDomain.RUNTIME,
    EventType.APPROVAL_GRANTED: EventDomain.RUNTIME,
    EventType.APPROVAL_DENIED: EventDomain.RUNTIME,
    EventType.TOOL_EXECUTION_REQUESTED: EventDomain.RUNTIME,
    EventType.TOOL_EXECUTION_COMPLETED: EventDomain.RUNTIME,
    EventType.TOOL_EXECUTION_FAILED: EventDomain.RUNTIME,
    EventType.MEMORY_WRITE: EventDomain.RUNTIME,
    EventType.MEMORY_RETRIEVE: EventDomain.RUNTIME,
    # Lab events
    EventType.PATCH_PROPOSED: EventDomain.LAB,
    EventType.PATCH_VALIDATED: EventDomain.LAB,
    EventType.PATCH_REJECTED: EventDomain.LAB,
    EventType.PATCH_PROMOTED: EventDomain.LAB,
    EventType.LESSON_STORED: EventDomain.LAB,
    # System events
    EventType.SELF_MODEL_REFRESHED: EventDomain.SYSTEM,
    EventType.RUNTIME_DEGRADED: EventDomain.SYSTEM,
    EventType.RUNTIME_RECOVERED: EventDomain.SYSTEM,
    EventType.RUNTIME_ALERT: EventDomain.SYSTEM,
    EventType.SYSTEM_EVENT: EventDomain.SYSTEM,
}


def get_domain(event_type: EventType) -> EventDomain:
    """Get the domain for an event type."""
    return _DOMAIN_MAP.get(event_type, EventDomain.SYSTEM)


# ── Secret scrubbing patterns ─────────────────────────────────

_SECRET_PATTERNS = ("sk-", "ghp_", "xoxb-", "Bearer ", "password", "secret")


def _scrub_value(val: Any) -> Any:
    """Recursively scrub secrets from event payloads."""
    if isinstance(val, str):
        for pat in _SECRET_PATTERNS:
            if pat in val:
                return f"[REDACTED:{pat[:3]}...]"
        return val
    if isinstance(val, dict):
        return {k: _scrub_value(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_scrub_value(v) for v in val]
    return val


@dataclass
class CognitiveEvent:
    """
    A single event in the cognitive journal.

    Immutable after creation. Payloads are scrubbed of secrets.
    """
    event_type: EventType
    summary: str
    source: str = ""                    # Which subsystem emitted this
    mission_id: str = ""
    session_id: str = ""
    severity: EventSeverity = EventSeverity.INFO
    confidence: float | None = None     # Optional confidence score
    payload: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    # Auto-generated
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    domain: EventDomain = field(default=EventDomain.RUNTIME)

    def __post_init__(self):
        # Set domain from event type
        self.domain = get_domain(self.event_type)
        # Scrub secrets from payload
        self.payload = _scrub_value(self.payload)

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "domain": self.domain.value,
            "summary": self.summary[:500],
            "source": self.source,
            "mission_id": self.mission_id,
            "session_id": self.session_id,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "payload": self.payload,
            "tags": self.tags,
            "timestamp": self.timestamp,
        }

    @property
    def is_lab(self) -> bool:
        return self.domain == EventDomain.LAB

    @property
    def is_runtime(self) -> bool:
        return self.domain == EventDomain.RUNTIME
