"""
integrations/mcp — MCP (Model Context Protocol) adapter layer.

Provides:
- MCPRegistry: register and query MCP servers + tools
- MCPAdapter: invoke MCP tools through canonical execution contract
- MCPHealth: check server availability

Integration rules:
- MCP tools flow through executor.capability_dispatch, not directly
- High-risk MCP actions obey normal approval/risk rules
- MCP failure returns structured CapabilityResult, never raises
"""
from integrations.mcp.mcp_registry import MCPRegistry, get_mcp_registry
from integrations.mcp.mcp_models import MCPServer, MCPTool

__all__ = ["MCPRegistry", "get_mcp_registry", "MCPServer", "MCPTool"]
