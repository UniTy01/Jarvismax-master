"""
plugins/plugin_health.py — Plugin health monitoring.
"""
from __future__ import annotations
import asyncio
import structlog
from plugins.plugin_registry import get_plugin_registry

log = structlog.get_logger("plugins.health")


async def check_plugin_health(plugin_id: str) -> str:
    """
    Run health_check() on a single plugin.
    Returns "ok", "degraded", or "unavailable".
    """
    registry = get_plugin_registry()
    plugin = registry.get(plugin_id)
    if plugin is None:
        return "unavailable"

    try:
        if asyncio.iscoroutinefunction(getattr(plugin, "health_check", None)):
            status = await plugin.health_check()
        elif callable(getattr(plugin, "health_check", None)):
            status = plugin.health_check()
        else:
            status = "ok"  # No health_check → assume ok
        status = str(status) if status in ("ok", "degraded", "unavailable") else "degraded"
    except Exception as exc:
        log.warning("plugin_health_check_failed",
                    plugin_id=plugin_id, error=str(exc)[:80])
        status = "unavailable"

    registry.update_status(plugin_id, status)
    return status


async def check_all_plugins() -> dict:
    """Health-check all registered plugins. Returns {plugin_id: status}."""
    registry = get_plugin_registry()
    results = {}
    for meta in registry.list_all():
        pid = meta["metadata"]["plugin_id"]
        results[pid] = await check_plugin_health(pid)
    if results:
        log.info("plugin_health_sweep", results=results)
    return results
