"""
api/routes/playbooks.py — Playbook management and execution API.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from api._deps import require_auth

router = APIRouter(tags=["playbooks"])


@router.get("/api/v3/playbooks")
async def list_playbooks(_user: dict = Depends(require_auth)):
    """List all available playbooks."""
    from core.planning.playbook import get_playbook_registry
    return {"ok": True, "data": get_playbook_registry().list_all()}


@router.get("/api/v3/playbooks/{playbook_id}")
async def get_playbook(playbook_id: str, _user: dict = Depends(require_auth)):
    """Get a specific playbook."""
    from core.planning.playbook import get_playbook_registry
    pb = get_playbook_registry().get(playbook_id)
    if not pb:
        raise HTTPException(404, f"Playbook not found: {playbook_id}")
    return {"ok": True, "data": pb.to_dict()}


class RunPlaybookRequest(BaseModel):
    goal: str
    inputs: Optional[dict] = None
    budget_mode: Optional[str] = "normal"  # "budget" | "normal" | "critical"


@router.post("/api/v3/playbooks/{playbook_id}/run")
async def run_playbook(
    playbook_id: str,
    req: RunPlaybookRequest,
    _user: dict = Depends(require_auth),
):
    """Execute a playbook and return results.

    budget_mode controls model selection tradeoff:
      - "budget": prefer cheaper acceptable models
      - "normal": balanced quality/price (default)
      - "critical": prefer highest quality models
    """
    from core.planning.playbook import execute_playbook
    budget_mode = req.budget_mode or "normal"
    if budget_mode not in ("budget", "normal", "critical"):
        budget_mode = "normal"
    result = execute_playbook(playbook_id, req.goal, req.inputs, budget_mode=budget_mode)
    if not result.get("ok") and "error" in result:
        raise HTTPException(404, result["error"])
    return result


@router.get("/api/v3/playbooks/{playbook_id}/stats")
async def playbook_stats(playbook_id: str, _user: dict = Depends(require_auth)):
    """Get performance stats for a playbook."""
    from core.planning.playbook import get_performance_tracker
    stats = get_performance_tracker().get_stats(playbook_id)
    return {"ok": True, "data": stats}


@router.get("/api/v3/playbooks/stats/all")
async def all_playbook_stats(_user: dict = Depends(require_auth)):
    """Get performance stats for all executed playbooks."""
    from core.planning.playbook import get_performance_tracker
    return {"ok": True, "data": get_performance_tracker().get_all_stats()}
