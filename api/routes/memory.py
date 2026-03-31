"""
api/routes/memory.py — Decision memory, knowledge, and plan endpoints.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header

from api._deps import _check_auth

router = APIRouter(tags=["memory"])


@router.get("/api/v2/decision-memory/stats")
async def decision_memory_stats(x_jarvis_token: Optional[str] = Header(None), authorization: Optional[str] = Header(None)):
    """Decision memory stats — patterns, failures, RAM usage."""
    _check_auth(x_jarvis_token, authorization)
    try:
        from memory.decision_memory import get_decision_memory
        dm = get_decision_memory()
        all_entries = list(dm._entries)
        total = len(all_entries)
        pattern_keys: set = set()
        for e in all_entries:
            pattern_keys.add((e.get("mission_type", "?"), e.get("complexity", "?")))
        patterns = []
        for mt, cx in sorted(pattern_keys):
            stats = dm.get_pattern_stats(mt, cx)
            if stats["count"] > 0:
                patterns.append({"mission_type": mt, "complexity": cx, **stats})
        return {"ok": True, "data": {
            "total_entries":    total,
            "ram_kb":           dm.ram_kb(),
            "patterns":         patterns,
            "failure_patterns": dm.detect_failure_patterns(),
        }}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/api/v2/decision-memory/registry")
async def decision_memory_registry(x_jarvis_token: Optional[str] = Header(None), authorization: Optional[str] = Header(None)):
    """Agent capability registry from decision_memory."""
    _check_auth(x_jarvis_token, authorization)
    try:
        from memory.capability_registry import CapabilityRegistry
        from memory.decision_memory import get_decision_memory
        dm = get_decision_memory()
        total = len(dm._entries)
        reg = CapabilityRegistry()
        reg.build_from_memory(dm)
        return {"ok": True, "data": {
            "agents":                  reg.get_registry_summary(),
            "total_missions_analyzed": total,
            "ram_kb":                  reg.ram_kb(),
            "note": "registry empty (< 10 entries in memory)" if total < 10 else None,
        }}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/api/v2/knowledge/recent")
async def get_knowledge_recent():
    try:
        from core.knowledge_memory import get_knowledge_memory
        km = get_knowledge_memory()
        return {"stats": km.get_stats(), "solutions": km.get_recent_solutions(20)}
    except Exception as e:
        return {"stats": {}, "solutions": [], "error": str(e)}


@router.get("/api/v2/plan/last")
async def get_last_plan_endpoint():
    try:
        from core.mission_planner import get_last_plan, get_mission_planner
        plan = get_last_plan()
        if plan is None:
            return {"plan": None, "message": "Aucun plan exécuté encore"}
        planner = get_mission_planner()
        return {"plan": planner.plan_to_dict(plan)}
    except Exception as e:
        return {"plan": None, "error": str(e)}
