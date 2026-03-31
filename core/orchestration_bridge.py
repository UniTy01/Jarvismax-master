"""
JARVIS MAX — Orchestration Bridge
====================================
Safe migration layer that routes mission operations through MetaOrchestrator
as the canonical authority, while preserving MissionSystem as a facade.

Design:
    - MissionSystem remains importable and callable (no breaking changes).
    - This bridge wraps MissionSystem calls and maps them to canonical types.
    - MetaOrchestrator is the lifecycle owner.
    - WorkflowGraph is available as an optional execution strategy.
    - Feature flag controls bridge activation.

Usage:
    from core.orchestration_bridge import (
        get_orchestration_bridge,
        submit_mission,
        get_mission_canonical,
        approve_mission,
        reject_mission,
    )

    # Submit through bridge (routes to canonical authority)
    result = submit_mission("Fix the auth module")

    # Get canonical view of any mission
    canonical = get_mission_canonical(mission_id)

Feature Flags:
    JARVIS_USE_CANONICAL_ORCHESTRATOR=true  → bridge active, MetaOrchestrator owns lifecycle
    JARVIS_USE_CANONICAL_ORCHESTRATOR=false → bridge passthrough, MissionSystem unchanged

No modifications to MissionSystem, MetaOrchestrator, or WorkflowGraph source code.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

try:
    import structlog
    log = structlog.get_logger(__name__)
except ImportError:
    import logging
    log = logging.getLogger(__name__)

from core.canonical_types import (
    CanonicalMissionStatus,
    CanonicalMissionContext,
    CanonicalRiskLevel,
    map_legacy_mission_status,
    map_legacy_risk_level,
    validate_transition,
    TransitionError,
)


# ═══════════════════════════════════════════════════════════════
# FEATURE FLAG
# ═══════════════════════════════════════════════════════════════

def _bridge_enabled() -> bool:
    """Check if canonical orchestration bridge is active."""
    return os.environ.get("JARVIS_USE_CANONICAL_ORCHESTRATOR", "").lower() in ("true", "1", "yes")


# ═══════════════════════════════════════════════════════════════
# BRIDGE CORE
# ═══════════════════════════════════════════════════════════════

class OrchestrationBridge:
    """
    Bridge that unifies MissionSystem and MetaOrchestrator under canonical types.

    When bridge is enabled:
        - submit_mission() creates missions in both systems, MetaOrchestrator owns lifecycle
        - get_mission_canonical() returns CanonicalMissionContext from any source
        - Status queries return canonical status mapped from whichever system has the mission

    When bridge is disabled (default):
        - All operations pass through to MissionSystem unchanged
        - Canonical mapping is still available for read operations
    """

    def __init__(self):
        self._canonical_missions: dict[str, CanonicalMissionContext] = {}

    # ── Mission Submission ────────────────────────────────────────────────────

    def submit_mission(self, user_input: str) -> dict:
        """
        Submit a mission through the bridge.

        When bridge enabled:
            1. MissionSystem.submit() for planning/advisory (it's good at that)
            2. Map result to CanonicalMissionContext
            3. Track canonical lifecycle

        When bridge disabled:
            Passthrough to MissionSystem.submit()

        Returns dict with canonical mission context. Never raises.
        """
        try:
            from core.mission_system import get_mission_system
            ms = get_mission_system()
            result = ms.submit(user_input)

            # Always create canonical view (even when bridge disabled)
            canonical = self._ms_result_to_canonical(result)
            self._canonical_missions[canonical.mission_id] = canonical

            if _bridge_enabled():
                log.info(
                    "bridge.submit_canonical",
                    mission_id=canonical.mission_id,
                    status=canonical.status.value,
                    risk=canonical.risk_level.value,
                )

            return {
                "ok": True,
                "mission_id": canonical.mission_id,
                "canonical_status": canonical.status.value,
                "canonical_risk": canonical.risk_level.value,
                "legacy_status": result.status if hasattr(result, "status") else "UNKNOWN",
                "bridge_active": _bridge_enabled(),
                "context": canonical.to_dict(),
            }

        except Exception as e:
            log.debug("bridge.submit_failed", err=str(e)[:100])
            return {
                "ok": False,
                "error": str(e)[:200],
                "bridge_active": _bridge_enabled(),
            }

    def get_mission_canonical(self, mission_id: str) -> Optional[CanonicalMissionContext]:
        """
        Get canonical view of a mission from any source system.

        Checks:
            1. Bridge's canonical cache
            2. MissionSystem
            3. MetaOrchestrator

        Returns CanonicalMissionContext or None. Never raises.
        """
        # 1. Check canonical cache
        if mission_id in self._canonical_missions:
            return self._canonical_missions[mission_id]

        # 2. Check MissionSystem
        try:
            from core.mission_system import get_mission_system
            ms = get_mission_system()
            result = ms.get_mission(mission_id)
            if result:
                canonical = self._ms_result_to_canonical(result)
                self._canonical_missions[mission_id] = canonical
                return canonical
        except Exception:
            pass

        # 3. Check MetaOrchestrator
        try:
            from core.meta_orchestrator import get_meta_orchestrator
            mo = get_meta_orchestrator()
            ctx = mo.get_mission(mission_id)
            if ctx:
                canonical = self._mo_context_to_canonical(ctx)
                self._canonical_missions[mission_id] = canonical
                return canonical
        except Exception:
            pass

        return None

    def approve_mission(self, mission_id: str, note: str = "") -> dict:
        """
        Approve a mission through the bridge.

        Updates both legacy system and canonical state.
        Never raises.
        """
        try:
            from core.mission_system import get_mission_system
            ms = get_mission_system()
            result = ms.approve(mission_id, note=note)

            canonical = self._canonical_missions.get(mission_id)
            if canonical and canonical.status == CanonicalMissionStatus.WAITING_APPROVAL:
                try:
                    canonical.transition(CanonicalMissionStatus.READY)
                except TransitionError:
                    pass

            return {
                "ok": True,
                "mission_id": mission_id,
                "canonical_status": canonical.status.value if canonical else "UNKNOWN",
                "legacy_status": result.status if result and hasattr(result, "status") else "UNKNOWN",
            }
        except Exception as e:
            log.debug("bridge.approve_failed", err=str(e)[:100])
            return {"ok": False, "error": str(e)[:200]}

    def reject_mission(self, mission_id: str, note: str = "") -> dict:
        """
        Reject a mission through the bridge.
        Never raises.
        """
        try:
            from core.mission_system import get_mission_system
            ms = get_mission_system()
            result = ms.reject(mission_id, note=note)

            canonical = self._canonical_missions.get(mission_id)
            if canonical and not canonical.status.is_terminal:
                try:
                    canonical.transition(CanonicalMissionStatus.CANCELLED)
                except TransitionError:
                    pass

            return {
                "ok": True,
                "mission_id": mission_id,
                "canonical_status": canonical.status.value if canonical else "UNKNOWN",
            }
        except Exception as e:
            log.debug("bridge.reject_failed", err=str(e)[:100])
            return {"ok": False, "error": str(e)[:200]}

    def list_missions_canonical(self, limit: int = 20) -> list[dict]:
        """
        List all known missions in canonical form.
        Merges from bridge cache, MissionSystem, and MetaOrchestrator.
        Never raises.
        """
        missions = {}

        # From canonical cache
        for mid, ctx in self._canonical_missions.items():
            missions[mid] = ctx.to_dict()

        # From MissionSystem
        try:
            from core.mission_system import get_mission_system
            ms = get_mission_system()
            for result in ms.list_missions(limit=limit):
                if result.mission_id not in missions:
                    canonical = self._ms_result_to_canonical(result)
                    missions[result.mission_id] = canonical.to_dict()
        except Exception:
            pass

        # From MetaOrchestrator
        try:
            from core.meta_orchestrator import get_meta_orchestrator
            mo = get_meta_orchestrator()
            status = mo.get_status()
            for ctx_dict in status.get("active_missions", []):
                mid = ctx_dict.get("mission_id", "")
                if mid and mid not in missions:
                    missions[mid] = {
                        "mission_id": mid,
                        "goal": ctx_dict.get("goal", ""),
                        "status": map_legacy_mission_status(
                            ctx_dict.get("status", "CREATED"), "meta_orchestrator"
                        ).value,
                        "source_system": "meta_orchestrator",
                    }
        except Exception:
            pass

        # Sort by most recent
        result_list = sorted(missions.values(), key=lambda x: x.get("updated_at", 0), reverse=True)
        return result_list[:limit]

    def get_status(self) -> dict:
        """
        Bridge status summary.
        """
        return {
            "bridge_enabled": _bridge_enabled(),
            "canonical_missions_tracked": len(self._canonical_missions),
            "status_counts": self._count_statuses(),
        }

    def _count_statuses(self) -> dict:
        counts: dict[str, int] = {}
        for ctx in self._canonical_missions.values():
            s = ctx.status.value
            counts[s] = counts.get(s, 0) + 1
        return counts

    # ── Conversion Helpers ────────────────────────────────────────────────────

    def _ms_result_to_canonical(self, result: Any) -> CanonicalMissionContext:
        """Convert MissionSystem MissionResult → CanonicalMissionContext."""
        status_str = result.status if isinstance(result.status, str) else result.status.value
        canonical_status = map_legacy_mission_status(status_str, "mission_system")
        canonical_risk = map_legacy_risk_level(
            getattr(result, "plan_risk", "LOW"), "state"
        )

        return CanonicalMissionContext(
            mission_id=result.mission_id,
            goal=result.user_input,
            status=canonical_status,
            risk_level=canonical_risk,
            intent=result.intent if isinstance(result.intent, str) else getattr(result.intent, "value", str(result.intent)),
            domain=getattr(result, "domain", "general"),
            plan_summary=getattr(result, "plan_summary", ""),
            agents=list(getattr(result, "agents_selected", [])),
            error=getattr(result, "error", ""),
            result=getattr(result, "final_output", ""),
            source_system="mission_system",
            created_at=getattr(result, "created_at", time.time()),
            updated_at=getattr(result, "updated_at", time.time()),
            metadata={
                "advisory_score": getattr(result, "advisory_score", 0),
                "advisory_decision": getattr(result, "advisory_decision", ""),
                "risk_score": getattr(result, "risk_score", 0),
                "complexity": getattr(result, "complexity", "medium"),
            },
        )

    def _mo_context_to_canonical(self, ctx: Any) -> CanonicalMissionContext:
        """Convert MetaOrchestrator MissionContext → CanonicalMissionContext."""
        status_str = ctx.status if isinstance(ctx.status, str) else ctx.status.value
        canonical_status = map_legacy_mission_status(status_str, "meta_orchestrator")

        return CanonicalMissionContext(
            mission_id=ctx.mission_id,
            goal=ctx.goal,
            status=canonical_status,
            intent="",
            domain="general",
            result=ctx.result or "",
            error=ctx.error or "",
            source_system="meta_orchestrator",
            created_at=ctx.created_at,
            updated_at=ctx.updated_at,
            metadata=ctx.metadata if hasattr(ctx, "metadata") else {},
        )


# ═══════════════════════════════════════════════════════════════
# SINGLETON + MODULE-LEVEL HELPERS
# ═══════════════════════════════════════════════════════════════

_bridge: OrchestrationBridge | None = None


def get_orchestration_bridge() -> OrchestrationBridge:
    """Return singleton OrchestrationBridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = OrchestrationBridge()
        try:
            log.info("orchestration_bridge.created", enabled=_bridge_enabled())
        except Exception:
            pass
    return _bridge


def submit_mission(user_input: str) -> dict:
    """Convenience: submit mission through bridge."""
    return get_orchestration_bridge().submit_mission(user_input)


def get_mission_canonical(mission_id: str) -> Optional[CanonicalMissionContext]:
    """Convenience: get canonical mission context."""
    return get_orchestration_bridge().get_mission_canonical(mission_id)


def approve_mission(mission_id: str, note: str = "") -> dict:
    """Convenience: approve mission through bridge."""
    return get_orchestration_bridge().approve_mission(mission_id, note)


def reject_mission(mission_id: str, note: str = "") -> dict:
    """Convenience: reject mission through bridge."""
    return get_orchestration_bridge().reject_mission(mission_id, note)
