"""
api/routes/system_readiness.py — System readiness across all 6 layers.

Validates: cognition, skills, planning, execution, memory, control.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from api._deps import require_auth

router = APIRouter(prefix="/api/v3/readiness", tags=["readiness"])


@router.get("")
async def system_readiness(_user: dict = Depends(require_auth)):
    """Check readiness of all 6 system layers."""
    layers = {}

    # 1. Cognition Layer
    try:
        from core.cognitive_bridge import get_bridge
        bridge = get_bridge()
        layers["cognition"] = {
            "ready": True,
            "components": {
                "cognitive_bridge": True,
                "capability_graph": bool(bridge._capability_graph),
                "decision_confidence": bool(bridge._decision_confidence),
            },
        }
    except Exception as e:
        layers["cognition"] = {"ready": False, "error": str(e)[:100]}

    # 2. Skills Layer
    try:
        from core.skills.domain_loader import get_domain_registry
        reg = get_domain_registry()
        skills = reg.list_all()
        layers["skills"] = {
            "ready": len(skills) >= 6,
            "count": len(skills),
            "domains": list(set(s.domain for s in skills)),
        }
    except Exception as e:
        layers["skills"] = {"ready": False, "error": str(e)[:100]}

    # 3. Planning Layer
    try:
        from core.planning.workflow_templates import load_templates
        from core.planning.plan_serializer import get_plan_store
        templates = load_templates()
        layers["planning"] = {
            "ready": len(templates) >= 1,
            "templates": len(templates),
            "plans": get_plan_store().stats(),
        }
    except Exception as e:
        layers["planning"] = {"ready": False, "error": str(e)[:100]}

    # 4. Execution Layer
    try:
        from core.tools_operational.tool_registry import get_tool_registry
        from core.tools_operational.tool_readiness import get_ready_tools
        tools = get_tool_registry().list_all()
        ready_tools = get_ready_tools()
        layers["execution"] = {
            "ready": len(tools) >= 1,
            "tools_total": len(tools),
            "tools_ready": len(ready_tools),
            "ready_tool_ids": ready_tools,
        }
    except Exception as e:
        layers["execution"] = {"ready": False, "error": str(e)[:100]}

    # 5. Memory Layer
    try:
        from core.planning.execution_memory import get_execution_memory
        from core.skills.skill_feedback import get_feedback_store
        layers["memory"] = {
            "ready": True,
            "execution_history": get_execution_memory().stats(),
        }
    except Exception as e:
        layers["memory"] = {"ready": False, "error": str(e)[:100]}

    # 6. Control Layer
    try:
        from core.cognitive_events.store import get_journal
        journal = get_journal()
        layers["control"] = {
            "ready": True,
            "journal_entries": len(journal._buffer) if hasattr(journal, '_buffer') else 0,
        }
    except Exception as e:
        layers["control"] = {"ready": False, "error": str(e)[:100]}

    # Summary
    ready_count = sum(1 for l in layers.values() if l.get("ready"))
    total = len(layers)

    return {
        "ok": True,
        "ready": ready_count == total,
        "score": f"{ready_count}/{total}",
        "layers": layers,
    }


@router.get("/agents")
async def agent_readiness(_user: dict = Depends(require_auth)):
    """List agent roles and their readiness."""
    from core.agents.roles import list_roles
    return {"ok": True, "data": list_roles()}


@router.get("/skills")
async def skill_readiness(_user: dict = Depends(require_auth)):
    """Skill layer readiness details."""
    from core.skills.domain_loader import get_domain_registry
    skills = get_domain_registry().list_all()
    return {
        "ok": True,
        "data": {
            "count": len(skills),
            "skills": [{"id": s.id, "domain": s.domain, "version": s.version,
                        "has_logic": bool(s.logic), "has_examples": bool(s.examples)}
                       for s in skills],
        },
    }


@router.get("/tools")
async def tool_readiness_detail(_user: dict = Depends(require_auth)):
    """Tool layer readiness details."""
    from core.tools_operational.tool_readiness import check_all_readiness
    return {"ok": True, "data": check_all_readiness()}
