"""
JARVIS MAX — Phase 9 MissionSummaryBuilder
Builds a MissionSummary from execution data and stores it in:
1. MissionStateStore (in-memory + JSON)
2. MemoryBus episodic layer (fail-open)
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from api.mission_store import MissionStateStore

if TYPE_CHECKING:
    from api.models import MissionLogEvent, MissionSummary


class MissionSummaryBuilder:
    """
    Builds a MissionSummary from execution data.
    Called after mission completion.
    """

    def build_and_store(
        self,
        mission_id: str,
        goal: str,
        status: str,
        log_events: list["MissionLogEvent"],
        duration_ms: int,
    ) -> "MissionSummary":
        """
        Extract from log_events:
        - tools_used: unique tool_names from TOOL_CALL events
        - agents_involved: unique agent_ids from AGENT_DECISION events
        - errors: messages from ERROR events
        - lessons_learned: auto-generate from error patterns
        - performance_score: 1.0 - (error_count / max(1, total_events)) capped [0,1]
        """
        from api.models import MissionSummary, LogEventType

        # Extract data from log events
        tools_used: list[str] = list({
            e.tool_name for e in log_events
            if e.event_type == LogEventType.TOOL_CALL and e.tool_name
        })
        agents_involved: list[str] = list({
            e.agent_id for e in log_events
            if e.event_type == LogEventType.AGENT_DECISION and e.agent_id
        })
        errors: list[str] = [
            e.message for e in log_events
            if e.event_type == LogEventType.ERROR
        ]

        # Auto-generate lessons from error patterns
        lessons_learned: list[str] = []
        error_tools = [
            e.tool_name for e in log_events
            if e.event_type == LogEventType.ERROR and e.tool_name
        ]
        for tool in set(error_tools):
            lessons_learned.append(f"Tool '{tool}' caused errors — consider fallback.")
        fallbacks = [e for e in log_events if e.event_type == LogEventType.FALLBACK]
        if fallbacks:
            lessons_learned.append(f"{len(fallbacks)} fallback(s) triggered during mission.")

        # Performance score: 1.0 - (errors / total), clamped [0, 1]
        total_events = max(1, len(log_events))
        error_count = len(errors)
        performance_score = max(0.0, min(1.0, 1.0 - (error_count / total_events)))

        # Build agent_outputs from TOOL_RESULT events (AGENT_RESULT)
        agent_outputs: dict[str, dict] = {}
        try:
            from api.models import LogEventType as _LET
            for e in log_events:
                if e.event_type == _LET.TOOL_RESULT and e.agent_id:
                    ar = (e.data or {}).get("agent_result")
                    if ar and isinstance(ar, dict):
                        agent_outputs[e.agent_id] = {
                            "reasoning":   ar.get("reasoning"),
                            "decision":    ar.get("decision"),
                            "confidence":  ar.get("confidence"),
                            "risks":       ar.get("risks") or [],
                            "suggestions": ar.get("suggestions") or [],
                        }
        except Exception:
            pass

        summary = MissionSummary(
            mission_id=mission_id,
            goal=goal,
            status=status,
            tools_used=tools_used,
            agents_involved=agents_involved,
            errors=errors,
            lessons_learned=lessons_learned,
            performance_score=round(performance_score, 4),
            duration_ms=duration_ms,
            created_at=time.time(),
            completed_at=time.time(),
            metadata={"agent_outputs": agent_outputs},
        )

        # 1. Store in MissionStateStore
        MissionStateStore.get().save_summary(summary)

        # 2. Store in MemoryBus episodic layer (fail-open)
        self._store_in_memory_bus(summary)

        return summary

    def _store_in_memory_bus(self, summary: "MissionSummary") -> None:
        try:
            from memory.memory_bus import MemoryBus, BACKEND_STORE
            from config.settings import get_settings
            bus = MemoryBus(get_settings())
            text = (
                f"Mission {summary.mission_id}: {summary.goal} — "
                f"status={summary.status}, score={summary.performance_score:.2f}, "
                f"tools={summary.tools_used}, agents={summary.agents_involved}"
            )
            bus.remember(
                text=text,
                metadata={
                    "type":        "mission_summary",
                    "mission_id":  summary.mission_id,
                    "status":      summary.status,
                    "score":       summary.performance_score,
                },
                tags=["mission", "summary", summary.status.lower()],
                backends=(BACKEND_STORE,),
                key=f"mission_summary_{summary.mission_id}",
            )
        except Exception:
            pass  # fail-open
