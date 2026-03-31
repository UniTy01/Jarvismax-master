"""
api/routes/mission_persistence.py — Mission persistence + approval resume endpoints.

Auth-protected. Read-only queries + approval resolution.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api._deps import require_auth

router = APIRouter(prefix="/api/v3/mission-state", tags=["mission-persistence"])


# ── Models ────────────────────────────────────────────────────

class ApprovalRequest(BaseModel):
    granted: bool
    reason: str = ""


# ── Endpoints ─────────────────────────────────────────────────

@router.get("")
async def list_missions(
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    _user: dict = Depends(require_auth),
):
    """List persisted missions, optionally filtered by status."""
    from core.mission_persistence import get_mission_persistence
    store = get_mission_persistence()
    if status:
        missions = store.list_by_status(status.upper(), limit)
    else:
        missions = store.list_all(limit)
    return {"ok": True, "data": [m.to_dict() for m in missions]}


@router.get("/stats")
async def mission_stats(_user: dict = Depends(require_auth)):
    """Mission persistence statistics."""
    from core.mission_persistence import get_mission_persistence
    return {"ok": True, "data": get_mission_persistence().stats()}


@router.get("/active")
async def active_missions(_user: dict = Depends(require_auth)):
    """Non-terminal missions."""
    from core.mission_persistence import get_mission_persistence
    missions = get_mission_persistence().list_active()
    return {"ok": True, "data": [m.to_dict() for m in missions]}


@router.get("/awaiting-approval")
async def awaiting_approval(_user: dict = Depends(require_auth)):
    """Missions waiting for human approval."""
    from core.mission_persistence import get_mission_persistence
    missions = get_mission_persistence().list_awaiting_approval()
    return {"ok": True, "data": [m.to_dict() for m in missions]}


# NOTE: Dynamic path routes MUST come AFTER static ones to avoid
# /stats /active /awaiting-approval being matched as {mission_id}

@router.post("/{mission_id}/resolve-approval")
async def resolve_approval(
    mission_id: str,
    body: ApprovalRequest,
    _user: dict = Depends(require_auth),
):
    """
    Resolve approval for a paused mission.

    The mission will either resume execution (granted=True)
    or be marked failed (granted=False).
    """
    try:
        from core.meta_orchestrator import get_orchestrator
        orch = get_orchestrator()
        ctx = await orch.resolve_approval(
            mission_id=mission_id,
            granted=body.granted,
            reason=body.reason,
        )
        if ctx is None:
            raise HTTPException(404, "Mission not found or not awaiting approval")
        return {
            "ok": True,
            "data": ctx.to_dict() if hasattr(ctx, "to_dict") else {"mission_id": mission_id},
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Approval resolution failed: {str(e)[:200]}")


@router.get("/{mission_id}")
async def get_mission(mission_id: str, _user: dict = Depends(require_auth)):
    """Get a specific persisted mission."""
    from core.mission_persistence import get_mission_persistence
    record = get_mission_persistence().get(mission_id)
    if not record:
        raise HTTPException(404, detail=f"Mission '{mission_id}' not found")
    return {"ok": True, "data": record.to_dict()}
