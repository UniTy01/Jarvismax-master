"""
kernel/state/ — Kernel Mission State Layer
==========================================
Canonical location for the mission state machine.

K1 RULE: zero imports from core/, agents/, api/, tools/.

Exports:
  MissionStatus         — enum (kernel-canonical definition, Pass 12)
  MissionContext        — pure data snapshot of one mission
  VALID_TRANSITIONS     — deterministic transition table
  MissionStateMachine   — validator + applier (no side effects)

Usage:
  from kernel.state import MissionContext, MissionStateMachine, MissionStatus

Note: core/state.py defines an identical MissionStatus (str, Enum).
Both are interoperable via string value comparison.
"""
from kernel.state.mission_state import (
    MissionContext,
    MissionStateMachine,
    VALID_TRANSITIONS,
    MissionStatus,
)

__all__ = [
    "MissionContext",
    "MissionStateMachine",
    "VALID_TRANSITIONS",
    "MissionStatus",
]
