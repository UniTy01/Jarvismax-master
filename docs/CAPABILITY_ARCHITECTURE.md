# Capability Architecture

## Overview

JarvisMax exposes three capability types, all unified under one dispatch model.

```
MetaOrchestrator
       │
       ▼
CapabilityDispatcher  (executor/capability_dispatch.py)
       │
       ├── NATIVE_TOOL ──→ registered handler function
       ├── PLUGIN       ──→ PluginRegistry → plugin.invoke()
       └── MCP_TOOL     ──→ MCPAdapter → HTTP → MCP server
```

All paths return `CapabilityResult`. Never raises.

## Contracts

```python
# Request
CapabilityRequest(
    capability_type = CapabilityType.PLUGIN,
    capability_id   = "my_plugin",
    action          = "run",
    params          = {...},
    risk_level      = "low",
)

# Result (always returned)
CapabilityResult(
    ok              = True / False,
    capability_type = ...,
    capability_id   = ...,
    result          = <any>,
    error           = <str | None>,
    execution_ms    = 42,
)
```

## Risk Model

| risk_level | behavior |
|---|---|
| low | execute directly |
| medium | log + execute |
| high | requires `requires_approval=True` → approval gate |

## Skill Integration

After successful execution, MetaOrchestrator may record a skill:
```
mission success → SkillService.record_outcome() → maybe create Skill
future mission → SkillService.retrieve_for_mission() → inject context
```

Skills may reference which capability_id solved the problem (via tags).

## Observability

All dispatch events are structured-logged:
- `native_tool_registered`
- `plugin_registered_via_dispatcher`
- `mcp_adapter_attached`
- `mcp_tool_invoked` / `mcp_tool_failed`
- `plugin_invoke_failed`
- `capability_dispatch_error`

## Extension Points

To add a new capability type:
1. Add entry to `CapabilityType` enum
2. Add `_dispatch_<type>()` method in `CapabilityDispatcher`
3. Register the backend via `register_*()` methods
4. Add tests in `tests/test_capability_contracts.py`

Do NOT create a new dispatcher. Extend this one.
