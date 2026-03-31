"""
kernel/adapters/capability_adapter.py — Bridge between core capability routing and kernel registry.

Syncs the kernel capability registry with the live runtime's ProviderRegistry,
making the kernel the authoritative source that runtime queries.
"""
from __future__ import annotations

import structlog

log = structlog.get_logger("kernel.adapters.capability")


def sync_kernel_from_runtime() -> dict:
    """
    Populate the kernel capability registry from the existing runtime ProviderRegistry.

    Called during convergence boot — makes kernel registry authoritative
    by importing all live capabilities from core/capability_routing/.

    Returns: {"synced": int, "kernel_total": int, "sources": dict}
    """
    from kernel.capabilities.registry import (
        get_capability_registry, Capability,
    )
    registry = get_capability_registry()

    synced = 0
    sources = {}

    # Source 1: Core ProviderRegistry (primary)
    try:
        from core.capability_routing.registry import ProviderRegistry
        pr = ProviderRegistry()
        counts = pr.populate()
        sources["provider_registry"] = counts

        # Import each capability_id → providers into kernel
        for cap_id, providers in pr._providers.items():
            provider_ids = [p.id for p in providers]
            risk = "low"
            needs_approval = False
            for p in providers:
                if getattr(p, "requires_approval", False):
                    needs_approval = True
                if getattr(p, "risk_level", "low") in ("high", "critical"):
                    risk = getattr(p, "risk_level", "low")

            # Only add if not already a kernel capability (don't overwrite built-ins)
            existing = registry.get(cap_id)
            if existing is None:
                registry.register(Capability(
                    id=cap_id,
                    name=cap_id.replace(".", " ").replace("_", " ").title(),
                    description=f"Runtime capability: {cap_id}",
                    category=_infer_category(cap_id),
                    providers=provider_ids,
                    risk_level=risk,
                    requires_approval=needs_approval,
                ))
                synced += 1
            else:
                # Merge providers from runtime into existing kernel capability
                merged = list(set(existing.providers + provider_ids))
                existing.providers = merged

    except Exception as e:
        log.debug("sync_provider_registry_failed", err=str(e)[:80])
        sources["provider_registry"] = {"error": str(e)[:80]}

    # Source 2: Capability Graph (secondary)
    try:
        from core.capability_graph import get_capability_graph
        graph = get_capability_graph()
        for cap_id, providers in graph._capabilities.items():
            existing = registry.get(cap_id)
            if existing is None:
                registry.register(Capability(
                    id=cap_id,
                    name=cap_id.replace(".", " ").replace("_", " ").title(),
                    category=_infer_category(cap_id),
                    providers=[p.get("id", "") for p in providers] if isinstance(providers, list) else [],
                ))
                synced += 1
    except Exception as e:
        log.debug("sync_capability_graph_failed", err=str(e)[:80])
        sources["capability_graph"] = {"error": str(e)[:80]}

    stats = registry.stats()
    result = {
        "synced": synced,
        "kernel_total": stats["total"],
        "sources": sources,
    }
    log.info("kernel_capabilities_synced", **result)
    return result


def _infer_category(cap_id: str) -> str:
    """Infer capability category from ID."""
    if any(kw in cap_id for kw in ("plan", "architect", "design")):
        return "planning"
    if any(kw in cap_id for kw in ("code", "engineer", "build", "shell", "python")):
        return "execution"
    if any(kw in cap_id for kw in ("analy", "research", "persona", "market")):
        return "execution"
    if any(kw in cap_id for kw in ("memory", "knowledge", "rag")):
        return "memory"
    if any(kw in cap_id for kw in ("policy", "risk", "approval", "guard")):
        return "policy"
    if any(kw in cap_id for kw in ("mcp", "github", "fetch", "sqlite")):
        return "execution"
    return "execution"
