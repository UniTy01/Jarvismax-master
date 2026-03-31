"""
api/routes/business_actions.py — Business Action Layer API.

Endpoints for listing, executing, and inspecting business actions.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api._deps import require_auth

router = APIRouter(prefix="/api/v3/business-actions", tags=["business-actions"])


class ExecuteRequest(BaseModel):
    action_id: str
    agent_output: dict = {}
    mission_id: str = ""
    project_name: str = ""


@router.get("")
async def list_actions(_user: dict = Depends(require_auth)):
    """List all registered business actions."""
    from core.business_actions import list_actions
    return {"ok": True, "data": list_actions()}


@router.get("/{action_id}")
async def get_action(action_id: str, _user: dict = Depends(require_auth)):
    """Get details for a specific business action."""
    from core.business_actions import ACTION_REGISTRY
    action = ACTION_REGISTRY.get(action_id)
    if not action:
        raise HTTPException(404, f"Action not found: {action_id}")
    return {"ok": True, "data": action.to_dict()}


@router.get("/readiness")
async def check_readiness(_user: dict = Depends(require_auth)):
    """Check readiness of all registered business actions."""
    from core.business_actions import ACTION_REGISTRY, check_action_readiness
    results = {}
    for action_id in ACTION_REGISTRY:
        results[action_id] = check_action_readiness(action_id)
    ready_count = sum(1 for r in results.values() if r.get("ready"))
    return {
        "ok": True,
        "data": {
            "total": len(results),
            "ready": ready_count,
            "blocked": len(results) - ready_count,
            "actions": results,
        },
    }


@router.post("/execute")
async def execute_action(
    body: ExecuteRequest,
    _user: dict = Depends(require_auth),
):
    """
    Execute a business action with provided agent output.

    Returns the execution result including created files and project directory.
    """
    from core.business_actions import get_business_executor
    result = get_business_executor().execute(
        action_id=body.action_id,
        agent_output=body.agent_output,
        mission_id=body.mission_id,
        project_name=body.project_name,
    )
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "Execution failed"))
    return {"ok": True, "data": result}
