"""
kernel/convergence/execution_trace.py — Query execution-level events from the cognitive journal.

Provides useful execution trace queries:
  - Recent tools invoked
  - Failed tools by mission
  - Step failure timeline
  - Provider usage per mission
  - Execution event counts

All queries are fail-open and return empty results on error.
"""
from __future__ import annotations

import structlog

log = structlog.get_logger("kernel.convergence.trace")


def get_recent_tool_events(limit: int = 20) -> list[dict]:
    """Get recent tool invocation events from the cognitive journal."""
    try:
        from core.cognitive_events.store import get_journal
        journal = get_journal()
        events = journal.get_recent(limit=limit * 3)  # over-fetch to filter
        tool_events = [
            e for e in events
            if e.get("event_type", "").startswith("execution.tool")
            or e.get("payload", {}).get("kernel_event_type", "").startswith("tool.")
        ]
        return tool_events[:limit]
    except Exception:
        return []


def get_failed_tools(mission_id: str = "", limit: int = 20) -> list[dict]:
    """Get failed tool executions, optionally filtered by mission."""
    try:
        from core.cognitive_events.store import get_journal
        journal = get_journal()
        events = journal.get_recent(limit=limit * 5)
        failed = []
        for e in events:
            is_tool_fail = (
                e.get("event_type") == "execution.tool_failed"
                or e.get("payload", {}).get("kernel_event_type") == "tool.failed"
            )
            if not is_tool_fail:
                continue
            if mission_id and e.get("mission_id") != mission_id:
                continue
            failed.append({
                "tool": e.get("payload", {}).get("tool_name", e.get("payload", {}).get("tool_id", "unknown")),
                "error": e.get("payload", {}).get("error", "")[:200],
                "mission_id": e.get("mission_id", ""),
                "timestamp": e.get("timestamp", 0),
            })
        return failed[:limit]
    except Exception:
        return []


def get_step_timeline(plan_id: str = "", limit: int = 30) -> list[dict]:
    """Get step lifecycle events in chronological order."""
    try:
        from core.cognitive_events.store import get_journal
        journal = get_journal()
        events = journal.get_recent(limit=limit * 5)
        step_events = []
        for e in events:
            kernel_type = e.get("payload", {}).get("kernel_event_type", "")
            is_step = (
                kernel_type.startswith("step.")
                or "plan_runner" in e.get("tags", [])
                or e.get("source") == "plan_runner"
            )
            if not is_step:
                continue
            if plan_id and e.get("payload", {}).get("plan_id") != plan_id:
                continue
            step_events.append({
                "event": kernel_type or e.get("payload", {}).get("event", ""),
                "step_id": e.get("payload", {}).get("step_id", ""),
                "step_name": e.get("payload", {}).get("step_name", ""),
                "plan_id": e.get("payload", {}).get("plan_id", ""),
                "ok": e.get("payload", {}).get("step_ok"),
                "timestamp": e.get("timestamp", 0),
            })
        return step_events[:limit]
    except Exception:
        return []


def get_execution_summary() -> dict:
    """Get summary counts of execution events from the journal."""
    try:
        from core.cognitive_events.store import get_journal
        journal = get_journal()
        events = journal.get_recent(limit=200)

        counts = {
            "tools_invoked": 0,
            "tools_completed": 0,
            "tools_failed": 0,
            "steps_started": 0,
            "steps_completed": 0,
            "steps_failed": 0,
            "missions_created": 0,
            "missions_completed": 0,
            "missions_failed": 0,
            "approvals_requested": 0,
            "total_events": len(events),
        }

        for e in events:
            et = e.get("event_type", "")
            kt = e.get("payload", {}).get("kernel_event_type", "")

            if et == "execution.tool_requested" or kt == "tool.invoked":
                counts["tools_invoked"] += 1
            elif et == "execution.tool_completed" or kt == "tool.completed":
                counts["tools_completed"] += 1
            elif et == "execution.tool_failed" or kt == "tool.failed":
                counts["tools_failed"] += 1
            elif kt == "step.started":
                counts["steps_started"] += 1
            elif kt == "step.completed":
                counts["steps_completed"] += 1
            elif kt == "step.failed":
                counts["steps_failed"] += 1
            elif et == "mission.created" or kt == "mission.created":
                counts["missions_created"] += 1
            elif et == "mission.completed" or kt == "mission.completed":
                counts["missions_completed"] += 1
            elif et == "mission.failed" or kt == "mission.failed":
                counts["missions_failed"] += 1
            elif et in ("approval.requested",) or kt == "approval.requested":
                counts["approvals_requested"] += 1

        # Success rates
        total_tools = counts["tools_completed"] + counts["tools_failed"]
        counts["tool_success_rate"] = round(counts["tools_completed"] / total_tools, 2) if total_tools else None

        total_steps = counts["steps_completed"] + counts["steps_failed"]
        counts["step_success_rate"] = round(counts["steps_completed"] / total_steps, 2) if total_steps else None

        return counts
    except Exception:
        return {"error": "journal_unavailable", "total_events": 0}
