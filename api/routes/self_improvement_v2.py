"""
api/routes/self_improvement_v2.py — Extended self-improvement endpoints.

Complements api/routes/self_improvement.py with additional V2 controls.
Registered in api/main.py as self_improvement_v2_router.

Endpoints:
  GET  /api/v2/self-improvement/failures
  GET  /api/v2/self-improvement/proposals
  POST /api/v2/self-improvement/validate
  GET  /api/v2/self-improvement/status
  GET  /api/v2/self-improvement/suggestions
  POST /api/v2/self-improve/run
  GET  /api/v2/self-improve/report
"""
from __future__ import annotations

import os
import logging
from fastapi import APIRouter, BackgroundTasks, Depends, Query

logger = logging.getLogger("jarvis.api.self_improvement_v2")

try:
    from api._deps import require_auth
    _auth = Depends(require_auth)
except Exception:
    _auth = None

router = APIRouter(tags=["self-improvement"])


@router.get("/api/v2/self-improvement/failures")
async def si_get_failures(
    limit: int = Query(20, ge=1, le=100),
    _user: dict = _auth,
):
    """Return recent FailureEntry list."""
    try:
        from core.self_improvement.failure_collector import FailureCollector
        collector = FailureCollector()
        entries = collector.load_from_disk(limit=limit)
        return {"ok": True, "data": {
            "failures": [e.to_dict() for e in entries],
            "count": len(entries),
        }}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/api/v2/self-improvement/proposals")
async def si_get_proposals(
    limit: int = Query(20, ge=1, le=50),
    _user: dict = _auth,
):
    """Return ImprovementProposal list."""
    try:
        from core.self_improvement.improvement_planner import ImprovementPlanner
        proposals = ImprovementPlanner().load_proposals(limit=limit)
        return {"ok": True, "data": {
            "proposals": [p.to_dict() for p in proposals],
            "count": len(proposals),
        }}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/api/v2/self-improvement/validate")
async def si_run_validation(_user: dict = _auth):
    """Launch ValidationRunner.run_validation_suite()."""
    try:
        import asyncio
        from core.self_improvement.validation_runner import ValidationRunner
        runner = ValidationRunner()
        loop = asyncio.get_event_loop()
        report = await loop.run_in_executor(None, runner.run_validation_suite, "http://localhost:8000")
        return {"ok": True, "data": report.to_dict()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/api/v2/self-improvement/status")
async def si_status(_user: dict = _auth):
    """Self-improvement status overview."""
    try:
        from core.self_improvement.failure_collector import FailureCollector, _FAILURE_LOG
        from core.self_improvement.improvement_planner import ImprovementPlanner
        from core.self_improvement.validation_runner import ValidationRunner
        from core.mode_system import get_mode_system

        failure_count = 0
        try:
            if _FAILURE_LOG.exists():
                failure_count = len(_FAILURE_LOG.read_text("utf-8").strip().splitlines())
        except Exception:
            pass

        proposals = ImprovementPlanner().load_proposals()
        pending_count = sum(1 for p in proposals if p.status == "pending")
        last_report = ValidationRunner.get_last_report()
        mode_val = get_mode_system().get_mode().value

        return {"ok": True, "data": {
            "failure_count": failure_count,
            "pending_proposals": pending_count,
            "total_proposals": len(proposals),
            "last_validation": last_report.to_dict() if last_report else None,
            "system_mode": mode_val,
        }}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/api/v2/self-improvement/suggestions")
async def get_suggestions(_user: dict = _auth):
    try:
        from core.self_improvement import get_self_improvement_manager
        mgr = get_self_improvement_manager()
        suggestions = mgr.analyze_patterns()
        return {
            "suggestions": [
                {
                    "problem_type": s.problem_type,
                    "mission_type": s.mission_type,
                    "frequency": s.frequency,
                    "confidence_avg": s.confidence_avg,
                    "impact_estimate": s.impact_estimate,
                    "risk_estimate": s.risk_estimate,
                    "suggested_change": s.suggested_change,
                    "affected_files": s.affected_files,
                    "priority_score": s.priority_score,
                }
                for s in suggestions
            ],
            "count": len(suggestions),
        }
    except Exception as e:
        return {"suggestions": [], "count": 0, "error": str(e)}


@router.post("/api/v2/self-improve/run", status_code=200)
async def self_improve_run(
    background_tasks: BackgroundTasks,
    _user: dict = _auth,
):
    """Launch full self-improvement analysis cycle."""
    if os.environ.get("JARVIS_EXECUTION_DISABLED", "").lower() in ("1", "true", "yes"):
        return {"ok": False, "error": "execution_disabled"}
    try:
        from core.self_improvement_engine import run_improvement_cycle
        report = run_improvement_cycle()
        return {"ok": True, "data": report.to_dict()}
    except Exception as e:
        logger.error("SelfImproveV2 run failed: %s", str(e)[:200])
        return {"ok": False, "error": str(e)[:200]}


@router.get("/api/v2/self-improve/report")
async def self_improve_report(_user: dict = _auth):
    """Get last self-improvement cycle report."""
    try:
        from core.self_improvement_engine import get_improvement_report
        report = get_improvement_report()
        if report:
            return {"ok": True, "data": report}
        return {"ok": True, "data": None, "message": "No improvement cycle has run yet"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


@router.post("/api/v2/self-improvement/proposals/{proposal_id}/apply")
async def si_apply_proposal(proposal_id: str, _user: dict = _auth):
    """Apply an improvement proposal: LLM patch → syntax check → tests → commit."""
    try:
        from core.self_improvement.proposal_applicator import apply_proposal
        result = await apply_proposal(proposal_id)
        return {"ok": result.ok, "data": result.to_dict()}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}
