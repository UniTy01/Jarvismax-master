"""
core/cognitive_events/ — Cognitive Event Journal.

Unified append-only event log for all significant cognitive and runtime events.
Consumers (DecisionTrace, SI observability, routing feedback, etc.) emit events
through the journal. The journal provides replay, filtering, and audit.

Public API:
    from core.cognitive_events import emit, get_journal, EventType
"""
from core.cognitive_events.types import EventType, CognitiveEvent
from core.cognitive_events.store import get_journal
from core.cognitive_events.emitter import emit

__all__ = ["EventType", "CognitiveEvent", "get_journal", "emit"]
