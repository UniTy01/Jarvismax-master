"""
api/routes/connectors.py — Connector management API.

Endpoints:
  GET  /api/v3/connectors           — list all connectors with status
  GET  /api/v3/connectors/{name}    — get connector detail
  POST /api/v3/connectors/{name}/execute — execute a connector action
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

try:
    from api._deps import require_auth
except ImportError:
    require_auth = None

router = APIRouter(prefix="/api/v3/connectors", tags=["connectors"])


class ConnectorActionRequest(BaseModel):
    action: str
    params: dict = {}


def _get_registry():
    from connectors.base import get_connector_registry
    from connectors.github_connector import GitHubConnector
    from connectors.filesystem_connector import FilesystemConnector
    from connectors.http_connector import HttpConnector

    reg = get_connector_registry()
    # Register built-in connectors if not already registered
    if not reg.get("github"):
        reg.register(GitHubConnector())
    if not reg.get("filesystem"):
        reg.register(FilesystemConnector())
    if not reg.get("http"):
        reg.register(HttpConnector())
    return reg


@router.get("")
async def list_connectors(user=Depends(require_auth)):
    """List all connectors with status."""
    reg = _get_registry()
    return {
        "ok": True,
        "connectors": reg.list_all(),
        "enabled_count": len(reg.get_enabled()),
    }


@router.get("/{name}")
async def get_connector(name: str, user=Depends(require_auth)):
    """Get connector detail."""
    reg = _get_registry()
    c = reg.get(name)
    if not c:
        return {"ok": False, "error": f"Connector '{name}' not found"}
    return {"ok": True, "connector": c.get_status()}


@router.post("/{name}/execute")
async def execute_connector(
    name: str, req: ConnectorActionRequest, user=Depends(require_auth)
):
    """Execute a connector action."""
    reg = _get_registry()
    result = reg.execute(name, req.action, req.params)
    return {"ok": result.success, "result": result.to_dict()}
