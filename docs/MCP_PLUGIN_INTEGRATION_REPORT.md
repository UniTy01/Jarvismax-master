# MCP + Plugin Integration Report

## Current State (before this work)

- MCP: NOT IMPLEMENTED
- Plugins: NOT IMPLEMENTED
- Capability contracts: NOT IMPLEMENTED

## Integration Model

### MCP

```
integrations/mcp/
├── mcp_models.py     — MCPServer, MCPTool dataclasses
├── mcp_registry.py   — In-memory registry (thread-safe)
├── mcp_adapter.py    — HTTP invocation, structured errors
└── mcp_health.py     — Async health sweep
```

MCP is NOT wired to live servers by default.
To activate: call `get_mcp_registry().register_server(...)` at startup.

### Plugins

```
plugins/
├── plugin_models.py    — PluginMetadata, PluginStatus
├── plugin_registry.py  — Explicit registration, no auto-discovery
└── plugin_health.py    — Per-plugin health check
```

### Capability Contracts

```
executor/
├── capability_contracts.py  — CapabilityRequest, CapabilityResult, CapabilityType
└── capability_dispatch.py   — Single dispatcher: native / plugin / MCP
```

## Runtime Behavior

All invocations return `CapabilityResult(ok, result, error)`.
No path through the dispatcher raises an exception.

MCP failure → `CapabilityResult(ok=False, error="connection refused")`
Plugin failure → `CapabilityResult(ok=False, error="intentional failure")`
Unknown capability → `CapabilityResult(ok=False, error="not registered")`

## Risks Still Present

1. No MCP servers registered at startup — MCP is ready but empty
2. No plugins registered at startup — plugin system ready but empty
3. MCP transport: HTTP only. stdio not implemented.
4. No approval gate enforcement in dispatcher yet (flag present, gate not wired)
5. CapabilityDispatcher not yet wired into MetaOrchestrator directly
