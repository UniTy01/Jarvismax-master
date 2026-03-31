"""
api/routes/capability_routing.py — Capability routing API.

Endpoints for inspecting and testing the capability-first routing layer.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api._deps import require_auth

router = APIRouter(prefix="/api/v3/capability-routing", tags=["capability-routing"])


@router.get("")
async def get_routing_status(_user: dict = Depends(require_auth)):
    """Registry stats and health."""
    from core.capability_routing.registry import get_provider_registry
    reg = get_provider_registry()
    return {"ok": True, "data": reg.stats()}


@router.get("/capabilities")
async def list_capabilities(_user: dict = Depends(require_auth)):
    """All known capability IDs with provider counts."""
    from core.capability_routing.registry import get_provider_registry
    reg = get_provider_registry()
    caps = {}
    for cap_id in reg.get_all_capabilities():
        providers = reg.get_providers(cap_id)
        available = [p for p in providers if p.is_available]
        caps[cap_id] = {
            "total_providers": len(providers),
            "available": len(available),
            "blocked": len(providers) - len(available),
        }
    return {"ok": True, "data": caps}


@router.get("/providers/{capability_id:path}")
async def get_providers(
    capability_id: str,
    _user: dict = Depends(require_auth),
):
    """All providers for a specific capability."""
    from core.capability_routing.registry import get_provider_registry
    reg = get_provider_registry()
    providers = reg.get_providers(capability_id)
    return {
        "ok": True,
        "data": {
            "capability_id": capability_id,
            "providers": [p.to_dict() for p in providers],
        },
    }


@router.post("/resolve")
async def resolve_goal(
    body: dict,
    _user: dict = Depends(require_auth),
):
    """Resolve a goal into capability requirements (no execution)."""
    from core.capability_routing.resolver import resolve_capabilities
    goal = body.get("goal", "")
    classification = body.get("classification")
    if not goal:
        return {"ok": False, "error": "goal is required"}

    requirements = resolve_capabilities(goal, classification)
    return {
        "ok": True,
        "data": {
            "goal": goal[:200],
            "requirements": [r.to_dict() for r in requirements],
        },
    }


@router.post("/route")
async def route_goal(
    body: dict,
    _user: dict = Depends(require_auth),
):
    """Full routing: resolve + score + select providers (no execution)."""
    from core.capability_routing.router import route_mission
    goal = body.get("goal", "")
    if not goal:
        return {"ok": False, "error": "goal is required"}

    decisions = route_mission(goal, classification=body.get("classification"))
    return {
        "ok": True,
        "data": {
            "goal": goal[:200],
            "decisions": [d.to_dict() for d in decisions],
        },
    }


@router.post("/refresh")
async def refresh_registry(_user: dict = Depends(require_auth)):
    """Force-refresh the provider registry from runtime sources."""
    from core.capability_routing.registry import get_provider_registry
    reg = get_provider_registry(force_refresh=True)
    return {"ok": True, "data": reg.stats()}


@router.get("/history")
async def get_history(
    limit: int = Query(50, ge=1, le=200),
    _user: dict = Depends(require_auth),
):
    """Recent routing decisions and outcomes."""
    from core.capability_routing.feedback import get_routing_history
    rh = get_routing_history()
    return {
        "ok": True,
        "data": {
            "summary": rh.summary(),
            "history": rh.get_recent(limit),
        },
    }


@router.get("/provider-stats")
async def get_provider_stats(_user: dict = Depends(require_auth)):
    """Per-provider success rate statistics from routing history."""
    from core.capability_routing.feedback import get_routing_history
    rh = get_routing_history()
    return {"ok": True, "data": rh.get_provider_stats()}


@router.get("/summary")
async def get_summary(_user: dict = Depends(require_auth)):
    """Combined registry + routing history summary."""
    from core.capability_routing.registry import get_provider_registry
    from core.capability_routing.feedback import get_routing_history
    reg = get_provider_registry()
    rh = get_routing_history()
    return {
        "ok": True,
        "data": {
            "registry": reg.stats(),
            "routing": rh.summary(),
        },
    }
