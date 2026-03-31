# Capability Unification Report

## Unified Model

All three capability types (native tools, plugins, MCP) use identical contracts.

```python
# Caller always does:
result = await dispatcher.dispatch(CapabilityRequest(
    capability_type=CapabilityType.PLUGIN,  # or NATIVE_TOOL or MCP_TOOL
    capability_id="...",
    params={...},
))
if result.ok:
    use(result.result)
else:
    handle(result.error)
```

## MetaOrchestrator Interaction

MetaOrchestrator can use CapabilityDispatcher to invoke extended capabilities:
```python
from executor.capability_dispatch import get_capability_dispatcher
dispatcher = get_capability_dispatcher()
caps = dispatcher.list_capabilities()
# {"native_tools": [...], "plugins": [...], "mcp_tools": [...]}
```

Skill retrieval already provides context about which tools were used historically.

## Executor Interaction

SupervisedExecutor handles core execution (bash, python, files).
CapabilityDispatcher handles extended capabilities (plugins, MCP).
They are parallel paths, not competing — no overlap.

## Risk Model (uniform)

| capability_type | risk_level | requires_approval |
|---|---|---|
| NATIVE_TOOL | caller-declared | False (default) |
| PLUGIN | from PluginMetadata | from PluginMetadata |
| MCP_TOOL | from MCPTool | from MCPTool |

## Observability Model (uniform)

All paths emit structlog events with:
- `capability_type`, `capability_id`
- `ok`, `error`, `ms` (execution time)

## What Remains Intentionally Simple

- No event bus / pub-sub for capability results
- No capability versioning
- No capability dependency graph
- No hot-reload of plugins

These are intentionally deferred to avoid premature complexity.
