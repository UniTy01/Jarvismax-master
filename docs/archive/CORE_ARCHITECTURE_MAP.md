# Core Architecture Map — Pre-Hardening

## Executor Landscape (4,400 lines across 12 files)

### Duplications Found

| Concept | Location 1 | Location 2 | Location 3 |
|---------|-----------|-----------|-----------|
| ExecutionResult | executor/contracts.py | executor/task_model.py | — |
| is_retryable() | executor/contracts.py | executor/retry_policy.py | executor/retry_engine.py |
| Retry engine | executor/retry_engine.py | executor/retry_policy.py | execution_supervisor.py |
| Error classification | executor/contracts.py | core/tool_executor.py | — |
| Execution pipeline | executor/execution_engine.py | executor/supervised_executor.py | core/action_executor.py |

### Canonical vs Legacy

| File | Role | Status |
|------|------|--------|
| executor/contracts.py | **CANONICAL** result model | Keep |
| executor/execution_engine.py | Full pipeline (542 lines) | **CANONICAL** pipeline |
| executor/retry_policy.py | Policy config | Keep (used by engine) |
| executor/retry_engine.py | Async retry wrapper | **OVERLAPS** with execution_engine |
| executor/task_model.py | OLD result model (132 lines) | **SUPERSEDED** by contracts.py |
| executor/supervised_executor.py | Legacy supervision | **SUPERSEDED** by execution_supervisor |
| executor/runner.py | Legacy runner | **NEEDS REVIEW** |
| executor/handlers.py | Action handlers | Keep |
| executor/risk_engine.py | Stub (15 lines) | **DEAD CODE** |
| executor/task_queue.py | Task state machine | Keep |
| core/action_executor.py | Daemon poller | Keep |
| core/tool_executor.py | Tool-level execution | Keep |

## Memory Landscape (5,239 lines across 16 files)

### Entry Points (should be 1)

1. core/memory_facade.py — **CANONICAL** (608 lines)
2. memory/memory_bus.py — parallel entry (801 lines)
3. memory/decision_memory.py — direct use by routes
4. memory/vault_memory.py — direct use by learning

### Duplicated Retrieval

| Concept | Location 1 | Location 2 |
|---------|-----------|-----------|
| Search | MemoryFacade.search() | MemoryBus.search() |
| Store | MemoryFacade.store() | MemoryBus.store() |
| Ranking | memory/memory_ranker.py | MemoryBus internal |

## Orchestrator Landscape (2,818 lines)

### Hierarchy

```
MetaOrchestrator (417 lines) — CANONICAL
    ├── JarvisOrchestrator (1,055 lines) — delegate for standard missions
    ├── OrchestratorV2 (714 lines) — delegate for budget/DAG missions
    └── orchestration/ (632 lines) — classifier, context, supervisor, trace
```

### Ambiguity: MetaOrchestrator delegates to JarvisOrchestrator.run() which has
its OWN planning and agent dispatch. MetaOrchestrator classification/context
is assembled but not fully utilized by the delegate.
