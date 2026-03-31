# Orchestration Authority Map

Canonical source: `core/legacy_compat.py::AUTHORITY_MAP`

## Mission Lifecycle
- **Canonical**: MetaOrchestrator
- **Active API**: MissionSystem
- **Convergence**: OrchestrationBridge mediates
- **Flag**: `JARVIS_USE_CANONICAL_ORCHESTRATOR`

## Risk Assessment
- **Canonical**: `core.state.RiskLevel`
- **Action Level**: `core.approval_queue.RiskLevel`
- Note: Both valid — different abstraction levels

## Planning
- **Canonical**: `core.planner.Planner`
- **V3**: `core.planning.planner_v3.PlannerV3`
- **Convergence**: PlannerV3 wraps legacy when `PLANNER_VERSION < 3`
- **Flag**: `PLANNER_VERSION`

## Memory
- **Systems**: MemoryBus, MemoryToolkit, KnowledgeMemory, DecisionMemory
- **Canonical**: `core.memory_facade.MemoryFacade`
- Note: Facade wraps all; not yet wired to API

## Tool Registry
- **Registries**: `core.tool_registry._MISSION_TOOLS`, `core.tool_runner._MISSION_TOOLS`
- Note: Two dicts can diverge. Canonical should be tool_registry.
