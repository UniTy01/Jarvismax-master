# Plugin System

## Architecture

```
MetaOrchestrator
    └── CapabilityDispatcher
            └── PluginRegistry → plugin.invoke(action, params, context)
```

## Modules

| File | Purpose |
|---|---|
| `plugins/plugin_models.py` | PluginMetadata + PluginStatus dataclasses |
| `plugins/plugin_registry.py` | In-memory registry, explicit registration |
| `plugins/plugin_health.py` | Health monitoring |

## Writing a Plugin

```python
from plugins.plugin_models import PluginMetadata

class MyPlugin:
    metadata = PluginMetadata(
        plugin_id="my_plugin",
        name="My Plugin",
        description="Does something useful",
        capability_type="tool",   # tool / data_source / integration / notification
        risk_level="low",
        tags=["search", "web"],
    )

    async def invoke(self, action: str, params: dict, context: dict) -> dict:
        if action == "run":
            return {"result": "done", "input": params}
        raise ValueError(f"Unknown action: {action}")

    async def health_check(self) -> str:
        return "ok"  # or "degraded" / "unavailable"
```

## Registering a Plugin

```python
from plugins.plugin_registry import get_plugin_registry
registry = get_plugin_registry()
registry.register(MyPlugin())
```

## Invoking via CapabilityDispatcher

```python
from executor.capability_dispatch import get_capability_dispatcher
from executor.capability_contracts import CapabilityRequest, CapabilityType

result = await get_capability_dispatcher().dispatch(CapabilityRequest(
    capability_type=CapabilityType.PLUGIN,
    capability_id="my_plugin",
    action="run",
    params={"key": "value"},
))
```

## Rules

- NO auto-discovery — all plugins registered explicitly
- Plugins must implement `metadata`, `invoke()`, optionally `health_check()`
- Plugin failure → structured `CapabilityResult(ok=False)`, never raises
- Disable a plugin: `registry.disable("my_plugin")`
- High-risk plugins: set `requires_approval=True` in metadata
