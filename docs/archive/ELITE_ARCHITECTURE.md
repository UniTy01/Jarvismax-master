# Elite Architecture — JarvisMax Three Pillars

## Overview

JarvisMax is built on three pillars that work together as a coherent agent OS:

```
                    ┌─────────────────────┐
                    │   MetaOrchestrator   │ ← Brain
                    │ (classify → plan →  │
                    │  supervise → learn)  │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
    ┌─────────▼─────────┐  ┌──▼──────────┐  ┌──▼──────────┐
    │     Executor       │  │   Memory    │  │   Skills    │
    │ (contract-driven,  │  │ (selective, │  │ (procedural │
    │  retry-aware,      │  │  ranked,    │  │  learning)  │
    │  brutally honest)  │  │  compacted) │  │             │
    └───────────────────┘  └─────────────┘  └─────────────┘
```

## Mission Lifecycle

1. **Intake** → MetaOrchestrator receives goal
2. **Classify** → mission_classifier determines type, risk, complexity, urgency
3. **Assemble** → context_assembler gathers skills, memory, failures, health
4. **Plan** → decide direct vs multi-step based on classification
5. **Execute** → execution_supervisor runs with retry/recovery logic
6. **Supervise** → detect failures, retry transient, abort permanent
7. **Record** → store outcome in memory, evaluate for skill creation
8. **Trace** → every decision recorded in decision_trace JSONL

## Pillar 1: MetaOrchestrator

| Module | Purpose |
|--------|---------|
| meta_orchestrator.py | Central lifecycle coordinator |
| orchestration/mission_classifier.py | Type, risk, complexity classification |
| orchestration/context_assembler.py | Rich context from memory + skills + health |
| orchestration/execution_supervisor.py | Supervised execution with retry/recovery |
| orchestration/decision_trace.py | Full decision audit trail |

## Pillar 2: Executor

| Module | Purpose |
|--------|---------|
| executor/contracts.py | ExecutionResult + ErrorClass + classify_error |
| executor/task_queue.py | Task state management |
| executor/retry_policy.py | Retry configuration |
| core/action_executor.py | Action daemon (poll + execute) |
| core/tool_executor.py | Tool-level execution |

## Pillar 3: Memory

| Module | Purpose |
|--------|---------|
| memory/memory_models.py | MemoryItem + MemoryType (4 layers) |
| memory/memory_ranker.py | Relevance scoring with recency + confidence |
| memory/memory_compactor.py | Prune old/empty/low-confidence entries |
| core/memory_facade.py | Unified entry point for all memory ops |
| core/skills/ | Procedural memory (skill system) |

## Design Principles

1. **No parallel systems** — one orchestrator, one executor, one memory
2. **Non-critical extensions** — all new features wrapped in try/except
3. **Contract-driven** — ExecutionResult is the universal execution contract
4. **Brutally honest** — never fake success, classify every error
5. **Explainable** — every decision has a trace entry
6. **Selective memory** — prune noise, rank by relevance, not volume
