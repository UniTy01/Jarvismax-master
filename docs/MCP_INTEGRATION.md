# MCP Integration

## Architecture

MCP (Model Context Protocol) tools are integrated as a controlled capability layer.

```
MetaOrchestrator
    └── CapabilityDispatcher
            └── MCPAdapter
                    └── MCPRegistry → MCPServer → HTTP endpoint
```

## Modules

| File | Purpose |
|---|---|
| `integrations/mcp/mcp_models.py` | MCPServer + MCPTool dataclasses |
| `integrations/mcp/mcp_registry.py` | In-memory server + tool registry |
| `integrations/mcp/mcp_adapter.py` | HTTP invocation, structured errors |
| `integrations/mcp/mcp_health.py` | Periodic health monitoring |

## Registering an MCP Server

```python
from integrations.mcp import get_mcp_registry, MCPServer, MCPTool

registry = get_mcp_registry()
registry.register_server(MCPServer(
    server_id="my_mcp",
    name="My MCP Server",
    endpoint="http://localhost:3000",
    transport="http",
    risk_level="low",
))
registry.register_tool(MCPTool(
    tool_id="my_mcp.search",
    server_id="my_mcp",
    name="search",
    description="Search for information",
    tags=["search", "web"],
))
```

## Invoking via CapabilityDispatcher

```python
from executor.capability_dispatch import get_capability_dispatcher
from executor.capability_contracts import CapabilityRequest, CapabilityType

dispatcher = get_capability_dispatcher()
result = await dispatcher.dispatch(CapabilityRequest(
    capability_type=CapabilityType.MCP_TOOL,
    capability_id="my_mcp.search",
    params={"query": "something"},
    context={"mission_id": "m123"},
))
if result.ok:
    print(result.result)
else:
    print("MCP error:", result.error)  # Never raises
```

## Failure Handling

- Connection error → server marked `degraded`
- Tool not found → immediate `CapabilityResult(ok=False)`
- Server unavailable → immediate `CapabilityResult(ok=False)`
- Never raises through the dispatcher

## Health Monitoring

```python
from integrations.mcp.mcp_health import check_all_servers
statuses = await check_all_servers()
# {"my_mcp": "ok"}
```

## Constraints

- Transport: HTTP only (stdio stub planned)
- No auto-discovery — servers registered explicitly at startup
- High-risk actions → set `requires_approval=True` on MCPTool
