"""
kernel/routing/ — Kernel Capability Routing
============================================
The kernel routes every mission to the best available capability provider.

Routing feeds into:
  - kernel/capabilities/performance.py  (provider reliability tracking)
  - core/meta_orchestrator.py           (Phase 0c routing hint)

KERNEL RULE: Zero imports from core/.

Usage:
  from kernel.routing import get_router, KernelRouteDecision
  decisions = get_router().route(goal, classification=clf.to_dict())
  primary   = get_router().primary(goal, classification=clf.to_dict())
"""
from kernel.routing.router import (
    KernelCapabilityRouter,
    _KernelHeuristicDecision,
    get_router,
    register_core_router,
)

__all__ = [
    "KernelCapabilityRouter",
    "_KernelHeuristicDecision",
    "get_router",
    "register_core_router",
]
