"""
api/routes/tools.py — Tool registry, live test, and rollback endpoints.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header

from api._deps import _check_auth

router = APIRouter(tags=["tools"])


@router.get("/api/v2/tools/registry")
async def get_tools_registry():
    try:
        from core.tool_registry import get_tool_registry
        reg = get_tool_registry()
        return {"tools": reg.summary(), "count": len(reg.list_tools())}
    except Exception as e:
        return {"tools": [], "count": 0, "error": str(e)}


@router.post("/api/v2/tools/test")
async def test_tool_live(
    payload: dict,
    x_jarvis_token: Optional[str] = Header(None), authorization: Optional[str] = Header(None),
):
    """
    Live tool test. Body: {"tool": "shell_command", "params": {"cmd": "docker ps"}}
    """
    _check_auth(x_jarvis_token, authorization)
    tool_name = payload.get("tool", "")
    params    = payload.get("params", {})
    if not tool_name:
        return {"ok": False, "error": "tool name required"}
    try:
        from core.tool_executor import get_tool_executor
        result = get_tool_executor().execute(tool_name, params, approval_mode="SUPERVISED")
        return {"ok": True, "tool": tool_name, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/api/v2/tools/rollback")
async def rollback_file(
    payload: dict,
    x_jarvis_token: Optional[str] = Header(None), authorization: Optional[str] = Header(None),
):
    """
    Manual rollback. Body: {"filepath": "path/to/file.py"}
    """
    _check_auth(x_jarvis_token, authorization)
    filepath = payload.get("filepath", "")
    if not filepath:
        return {"ok": False, "error": "filepath required"}
    try:
        from core.rollback_manager import get_rollback_manager
        rm = get_rollback_manager()
        backups = rm.list_backups(filepath)
        if not backups:
            return {"ok": False, "error": "no_backup_found", "filepath": filepath}
        ok = rm.restore_latest(filepath)
        return {
            "ok": ok,
            "filepath": filepath,
            "restored_from": backups[-1] if ok else None,
            "available_backups": backups,
            "status": "rollback_success" if ok else "rollback_failed",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
