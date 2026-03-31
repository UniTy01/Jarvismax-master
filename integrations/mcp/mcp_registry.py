"""
integrations/mcp/mcp_registry.py — In-memory MCP server + tool registry.

Lifecycle:
1. On startup, register known MCP servers via register_server()
2. MCPAdapter queries registry to resolve tool_id → server endpoint
3. Health monitor calls update_health() periodically
"""
from __future__ import annotations
import threading
from typing import Optional
import structlog

from integrations.mcp.mcp_models import MCPServer, MCPTool

log = structlog.get_logger("mcp.registry")


class MCPRegistry:
    """
    Central registry for MCP servers and their exposed tools.

    Thread-safe. In-memory only — re-populated on each startup
    from config or explicit register() calls.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._servers: dict[str, MCPServer] = {}
        self._tools: dict[str, MCPTool] = {}   # tool_id → MCPTool

    # ── Servers ──────────────────────────────────────────────

    def register_server(self, server: MCPServer) -> None:
        with self._lock:
            self._servers[server.server_id] = server
        log.info("mcp_server_registered",
                 server_id=server.server_id,
                 name=server.name,
                 endpoint=server.endpoint)

    def unregister_server(self, server_id: str) -> bool:
        with self._lock:
            if server_id in self._servers:
                del self._servers[server_id]
                # Remove associated tools
                stale = [tid for tid, t in self._tools.items()
                         if t.server_id == server_id]
                for tid in stale:
                    del self._tools[tid]
                log.info("mcp_server_unregistered", server_id=server_id)
                return True
        return False

    def get_server(self, server_id: str) -> Optional[MCPServer]:
        return self._servers.get(server_id)

    def list_servers(self, healthy_only: bool = False) -> list[MCPServer]:
        servers = list(self._servers.values())
        if healthy_only:
            servers = [s for s in servers if s.health_status == "ok"]
        return servers

    def update_health(self, server_id: str, status: str) -> None:
        with self._lock:
            if server_id in self._servers:
                self._servers[server_id].health_status = status
        log.debug("mcp_health_updated", server_id=server_id, status=status)

    # ── Tools ─────────────────────────────────────────────────

    def register_tool(self, tool: MCPTool) -> None:
        with self._lock:
            self._tools[tool.tool_id] = tool
        log.debug("mcp_tool_registered",
                  tool_id=tool.tool_id, server_id=tool.server_id)

    def get_tool(self, tool_id: str) -> Optional[MCPTool]:
        return self._tools.get(tool_id)

    def list_tools(self, server_id: Optional[str] = None) -> list[MCPTool]:
        tools = list(self._tools.values())
        if server_id:
            tools = [t for t in tools if t.server_id == server_id]
        return tools

    def find_tools_by_tag(self, tag: str) -> list[MCPTool]:
        return [t for t in self._tools.values()
                if tag.lower() in [x.lower() for x in t.tags]]

    # ── Stats ─────────────────────────────────────────────────

    def stats(self) -> dict:
        servers = list(self._servers.values())
        return {
            "servers": len(servers),
            "tools": len(self._tools),
            "healthy_servers": sum(1 for s in servers if s.health_status == "ok"),
        }


# ── Singleton ─────────────────────────────────────────────────

_registry: Optional[MCPRegistry] = None
_registry_lock = threading.Lock()


def get_mcp_registry() -> MCPRegistry:
    global _registry
    with _registry_lock:
        if _registry is None:
            _registry = MCPRegistry()
    return _registry
