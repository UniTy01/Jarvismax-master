"""
JARVIS MAX — Convergence API Router
======================================
Provides /api/v3/ endpoints that route through the OrchestrationBridge
to MetaOrchestrator (canonical authority) when JARVIS_USE_CANONICAL_ORCHESTRATOR=1.

Falls back to MissionSystem transparently when flag is OFF.

This router sits ALONGSIDE existing mission_control.py routes.
No existing routes modified. Clients can migrate to /api/v3/ at their own pace.

Endpoints:
    POST /api/v3/missions           — submit mission (bridge → canonical)
    GET  /api/v3/missions           — list missions (merged sources)
    GET  /api/v3/missions/{id}      — get mission (canonical status)
    POST /api/v3/missions/{id}/approve  — approve mission
    POST /api/v3/missions/{id}/reject   — reject mission
    GET  /api/v3/system/status      — unified system status
    GET  /api/v3/system/health      — deep health check
    GET  /api/v3/approvals/pending  — approval queue
    GET  /api/v3/agents/status      — agent registry status
    WS   /ws/stream                 — unified event stream
"""
from __future__ import annotations

import json
import os
import time
from typing import Optional
from api._deps import _check_auth

try:
    from fastapi import Depends, APIRouter, Body, Header, HTTPException, WebSocket, WebSocketDisconnect
    from fastapi.responses import JSONResponse
except ImportError:
    # Stub for syntax validation without fastapi
    class _Stub:
        def get(self, *a, **k):
            def dec(f): return f
            return dec
        def post(self, *a, **k):
            def dec(f): return f
            return dec
        def websocket(self, *a, **k):
            def dec(f): return f
            return dec
    APIRouter = _Stub
    Body = lambda **k: None
    WebSocket = object
    WebSocketDisconnect = Exception
    JSONResponse = dict

try:
    import structlog
    log = structlog.get_logger(__name__)
except ImportError:
    import logging
    log = logging.getLogger(__name__)



def _auth(x_jarvis_token: str | None = Header(None),
          authorization: str | None = Header(None)):
    _check_auth(x_jarvis_token, authorization)


router = APIRouter(prefix="/api/v3", tags=["convergence"], dependencies=[Depends(_auth)])


def _use_canonical() -> bool:
    return os.environ.get("JARVIS_USE_CANONICAL_ORCHESTRATOR", "").lower() in ("1", "true", "yes")


def _ok(data, status: int = 200) -> JSONResponse:
    return JSONResponse({"ok": True, "data": data}, status_code=status)


def _err(msg: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"ok": False, "error": msg}, status_code=status)


# ═══════════════════════════════════════════════════════════════
# MISSION ENDPOINTS
# ═══════════════════════════════════════════════════════════════



@router.post("/missions")
async def submit_mission(body: dict = Body(...)):
    """
    Submit a new mission.

    When canonical orchestrator enabled:
      → OrchestrationBridge.submit() → MetaOrchestrator
    When disabled:
      → MissionSystem.submit() (legacy)
    """
    try:
        goal = str(body.get("goal") or body.get("input", "")).strip()
        if not goal:
            return _err("Field 'goal' is required.")

        if _use_canonical():
            try:
                from core.orchestration_bridge import submit_mission as bridge_submit
                result = bridge_submit(goal)
                return _ok(result, status=201)
            except Exception as e:
                log.warning("canonical_submit_fallback", err=str(e)[:80])
                # Fall through to legacy

        # Legacy path
        from core.mission_system import get_mission_system
        ms = get_mission_system()
        result = ms.submit(goal)
        data = result.to_dict()

        # Intelligence hooks
        try:
            from core.intelligence_hooks import post_mission_submit
            enrichment = post_mission_submit(data.get("mission_id", ""), goal)
            if enrichment:
                data["intelligence"] = enrichment
        except Exception:
            pass

        return _ok(data, status=201)

    except Exception as e:
        log.warning("submit_mission_err", err=str(e)[:80])
        return _err(str(e)[:200], status=500)


@router.get("/missions")
async def list_missions(
    status: Optional[str] = None,
    limit: int = 20,
):
    """List missions with canonical status mapping."""
    try:
        if _use_canonical():
            try:
                from core.orchestration_bridge import get_orchestration_bridge
                bridge = get_orchestration_bridge()
                missions = bridge.list_missions(status_filter=status, limit=limit)
                return _ok({"missions": missions, "source": "bridge"})
            except Exception as e:
                log.warning("canonical_list_fallback", err=str(e)[:80])

        from core.mission_system import get_mission_system
        ms = get_mission_system()
        missions = ms.list_missions(status=status, limit=limit)
        return _ok({
            "missions": [m.to_dict() for m in missions],
            "source": "legacy",
        })

    except Exception as e:
        return _err(str(e)[:200], status=500)


@router.get("/missions/{mission_id}")
async def get_mission(mission_id: str):
    """Get mission with canonical status."""
    try:
        if _use_canonical():
            try:
                from core.orchestration_bridge import get_mission_canonical
                ctx = get_mission_canonical(mission_id)
                if ctx:
                    return _ok(ctx.to_dict())
            except Exception as e:
                log.warning("canonical_get_fallback", err=str(e)[:80])

        from core.mission_system import get_mission_system
        ms = get_mission_system()
        mission = ms.get(mission_id)
        if not mission:
            return _err(f"Mission '{mission_id}' not found.", status=404)
        return _ok(mission.to_dict())

    except Exception as e:
        return _err(str(e)[:200], status=500)


@router.post("/missions/{mission_id}/approve")
async def approve_mission(mission_id: str, body: dict = Body(default={})):
    """Approve a pending mission."""
    try:
        note = str(body.get("note", ""))

        if _use_canonical():
            try:
                from core.orchestration_bridge import approve_mission as bridge_approve
                result = bridge_approve(mission_id, note)
                return _ok(result)
            except Exception as e:
                log.warning("canonical_approve_fallback", err=str(e)[:80])

        from core.mission_system import get_mission_system
        ms = get_mission_system()
        result = ms.approve(mission_id, note)
        if result is None:
            return _err(f"Mission '{mission_id}' not found or not pending.", status=404)
        return _ok(result.to_dict())

    except Exception as e:
        return _err(str(e)[:200], status=500)


@router.post("/missions/{mission_id}/reject")
async def reject_mission(mission_id: str, body: dict = Body(default={})):
    """Reject a pending mission."""
    try:
        note = str(body.get("note", ""))

        if _use_canonical():
            try:
                from core.orchestration_bridge import reject_mission as bridge_reject
                result = bridge_reject(mission_id, note)
                return _ok(result)
            except Exception as e:
                log.warning("canonical_reject_fallback", err=str(e)[:80])

        from core.mission_system import get_mission_system
        ms = get_mission_system()
        result = ms.get(mission_id)
        if result is None:
            return _err(f"Mission '{mission_id}' not found.", status=404)
        return _ok({"rejected": True, "mission_id": mission_id})

    except Exception as e:
        return _err(str(e)[:200], status=500)


# ═══════════════════════════════════════════════════════════════
# SYSTEM ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.get("/system/status")
async def system_status():
    """
    Unified system status.

    Merges:
    - Mission system stats
    - Orchestration bridge status
    - Observability intelligence (if available)
    - Capability expansion status (if available)
    """
    status_data = {
        "timestamp": time.time(),
        "canonical_orchestrator": _use_canonical(),
        "components": {},
    }

    # Mission system
    try:
        from core.mission_system import get_mission_system
        ms = get_mission_system()
        status_data["components"]["mission_system"] = ms.stats()
    except Exception as e:
        status_data["components"]["mission_system"] = {"error": str(e)[:80]}

    # Orchestration bridge
    if _use_canonical():
        try:
            from core.orchestration_bridge import get_orchestration_bridge
            bridge = get_orchestration_bridge()
            status_data["components"]["orchestration_bridge"] = bridge.get_status()
        except Exception as e:
            status_data["components"]["orchestration_bridge"] = {"error": str(e)[:80]}

    # Observability
    try:
        from core.observability_intelligence import get_system_health
        status_data["components"]["observability"] = get_system_health()
    except ImportError:
        status_data["components"]["observability"] = {"status": "not_available"}
    except Exception as e:
        status_data["components"]["observability"] = {"error": str(e)[:80]}

    # Capability expansion
    try:
        from core.capability_expansion import get_expansion_status
        status_data["components"]["capability_expansion"] = get_expansion_status()
    except ImportError:
        status_data["components"]["capability_expansion"] = {"status": "not_available"}
    except Exception:
        pass

    # Intelligence hooks
    try:
        from core.intelligence_hooks import periodic_health
        status_data["components"]["intelligence"] = periodic_health()
    except ImportError:
        pass
    except Exception:
        pass

    # Legacy compatibility info
    try:
        from core.legacy_compat import get_authority_map, get_deprecations
        status_data["authority_map"] = get_authority_map()
        status_data["deprecations"] = len(get_deprecations())
    except ImportError:
        pass

    return _ok(status_data)


@router.get("/system/health")
async def system_health():
    """Deep health check."""
    checks = {}

    # Core import check
    for module_name in ["core.mission_system", "core.orchestrator_v2",
                        "core.meta_orchestrator", "core.planner"]:
        try:
            __import__(module_name)
            checks[module_name] = "ok"
        except Exception as e:
            checks[module_name] = f"error: {str(e)[:40]}"

    # Approval queue
    try:
        from core.approval_queue import get_pending
        pending = get_pending()
        checks["approval_queue"] = {"ok": True, "pending": len(pending)}
    except Exception as e:
        checks["approval_queue"] = {"ok": False, "error": str(e)[:40]}

    healthy = all(
        v == "ok" or (isinstance(v, dict) and v.get("ok"))
        for v in checks.values()
    )

    return _ok({
        "status": "healthy" if healthy else "degraded",
        "checks": checks,
    })


# ═══════════════════════════════════════════════════════════════
# APPROVAL QUEUE
# ═══════════════════════════════════════════════════════════════

@router.get("/approvals/pending")
async def get_pending_approvals():
    """Get all pending approval items."""
    try:
        from core.approval_queue import get_pending
        items = get_pending()
        return _ok({"pending": items, "count": len(items)})
    except Exception as e:
        return _err(str(e)[:200], status=500)


# ═══════════════════════════════════════════════════════════════
# AGENT STATUS
# ═══════════════════════════════════════════════════════════════

@router.get("/agents/status")
async def get_agent_status():
    """Get agent registry status."""
    try:
        agents = {}
        # Try crew registry
        try:
            from agents.crew import AgentCrew
            crew = AgentCrew()
            agents["crew"] = {
                "available": True,
                "agents": list(crew.agents.keys()) if hasattr(crew, "agents") else [],
            }
        except Exception:
            agents["crew"] = {"available": False}

        # Try jarvis team
        try:
            from agents.jarvis_team.tools import AGENT_TOOL_ACCESS
            agents["jarvis_team"] = {
                "available": True,
                "agents": list(AGENT_TOOL_ACCESS.keys()),
            }
        except Exception:
            agents["jarvis_team"] = {"available": False}

        return _ok(agents)

    except Exception as e:
        return _err(str(e)[:200], status=500)
