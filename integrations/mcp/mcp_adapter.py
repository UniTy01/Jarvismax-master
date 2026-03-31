"""
integrations/mcp/mcp_adapter.py — MCP tool invocation adapter.

Invokes MCP tools via HTTP (or stdio stub).
Always returns structured dict {ok, result, error}.
Never raises — failure is returned as structured error.

Integration: called by executor.capability_dispatch, not directly.
"""
from __future__ import annotations
import time
import asyncio
from typing import Any, Optional
import structlog

from integrations.mcp.mcp_registry import get_mcp_registry
from integrations.mcp.mcp_models import MCPTool, MCPServer

log = structlog.get_logger("mcp.adapter")

_HTTP_TIMEOUT = 10.0  # seconds


class MCPAdapter:
    """
    Invokes MCP tools.

    Resolves tool_id → server endpoint via MCPRegistry,
    then dispatches HTTP POST to the MCP server.
    """

    def __init__(self, registry=None):
        self._registry = registry or get_mcp_registry()

    async def invoke_tool(
        self,
        tool_id: str,
        params: dict,
        context: Optional[dict] = None,
    ) -> dict:
        """
        Invoke an MCP tool by ID.

        Returns:
            {ok: bool, result: Any, error: str|None, tool_id: str, ms: int}
        """
        t0 = time.monotonic()
        context = context or {}

        tool = self._registry.get_tool(tool_id)
        if tool is None:
            return self._error(tool_id, "Tool not found in MCP registry", t0)

        server = self._registry.get_server(tool.server_id)
        if server is None:
            return self._error(tool_id, f"Server {tool.server_id!r} not found", t0)

        if server.health_status == "unavailable":
            return self._error(tool_id, f"Server {server.name!r} is unavailable", t0)

        # Dispatch by transport
        if server.transport == "http":
            return await self._invoke_http(tool, server, params, context, t0)
        else:
            return self._error(
                tool_id,
                f"Unsupported MCP transport: {server.transport!r}",
                t0
            )

    async def _invoke_http(
        self,
        tool: MCPTool,
        server: MCPServer,
        params: dict,
        context: dict,
        t0: float,
    ) -> dict:
        """HTTP invocation of MCP tool."""
        try:
            import httpx
            url = f"{server.endpoint.rstrip('/')}/invoke"
            payload = {
                "tool": tool.name,
                "params": params,
                "context": context,
            }
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
            ms = int((time.monotonic() - t0) * 1000)
            log.info("mcp_tool_invoked",
                     tool_id=tool.tool_id, status="ok", ms=ms)
            return {"ok": True, "result": data, "error": None,
                    "tool_id": tool.tool_id, "ms": ms}
        except Exception as exc:
            err = f"{type(exc).__name__}: {exc}"
            # Mark server degraded on connection errors
            if "Connect" in type(exc).__name__ or "Timeout" in type(exc).__name__:
                self._registry.update_health(server.server_id, "degraded")
            return self._error(tool.tool_id, err, t0)

    async def check_health(self, server_id: str) -> str:
        """
        Ping MCP server health endpoint.
        Returns "ok", "degraded", or "unavailable".
        """
        server = self._registry.get_server(server_id)
        if server is None:
            return "unavailable"
        try:
            import httpx
            url = f"{server.endpoint.rstrip('/')}/health"
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(url)
                status = "ok" if resp.status_code == 200 else "degraded"
        except Exception:
            status = "unavailable"
        self._registry.update_health(server_id, status)
        return status

    @staticmethod
    def _error(tool_id: str, msg: str, t0: float) -> dict:
        ms = int((time.monotonic() - t0) * 1000)
        log.warning("mcp_tool_failed", tool_id=tool_id, error=msg, ms=ms)
        return {"ok": False, "result": None, "error": msg,
                "tool_id": tool_id, "ms": ms}
