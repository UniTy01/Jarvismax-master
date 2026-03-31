"""
core/capability_routing/ — Capability-first mission routing.

Step 3: instead of "which agent?", ask "which capability?" then select
the best provider (agent / tool / MCP / module / connector).

Public API:
    from core.capability_routing import route_mission, get_provider_registry, get_routing_history
"""
from core.capability_routing.router import route_mission
from core.capability_routing.registry import get_provider_registry
from core.capability_routing.feedback import get_routing_history

__all__ = ["route_mission", "get_provider_registry", "get_routing_history"]
