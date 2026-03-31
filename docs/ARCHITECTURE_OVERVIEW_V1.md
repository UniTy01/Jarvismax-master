# Architecture Overview v1 — FROZEN 🔒

## Conceptual Grouping

The codebase is organized into clear domains. No file moves planned for v1.

```
core/
├── orchestration/          (conceptual — not a directory)
│   ├── meta_orchestrator.py    ← CANONICAL runtime (12-phase pipeline)
│   ├── orchestrator.py         ← DEPRECATED delegate
│   ├── mission_system.py       ← mission lifecycle + state machine
│   └── planner.py              ← mission planning
│
├── execution/              (conceptual)
│   ├── action_executor.py      ← agent execution loop
│   ├── tool_executor.py        ← tool dispatch + capability check
│   └── tool_registry.py        ← tool registration
│
├── schemas/
│   └── final_output.py         ← FinalOutput, AgentOutput, OutputMetrics
│
├── actions/
│   └── action_model.py         ← CanonicalAction (official lifecycle)
│
├── capabilities/
│   ├── schema.py               ← Capability dataclass
│   └── registry.py             ← 10 core tools, risk check, permissions
│
├── observability/
│   └── event_envelope.py       ← EventEnvelope, trace_id, EventCollector
│
├── security/
│   └── startup_guard.py        ← production startup checks
│
├── skills/                 (5 modules)
│   ├── skill_manager.py        ← CRUD operations
│   ├── skill_retriever.py      ← cosine similarity search
│   ├── skill_storage.py        ← JSONL persistence
│   ├── skill_detector.py       ← duplicate detection
│   └── skill_models.py         ← data models
│
├── memory/                 (conceptual)
│   ├── memory_facade.py        ← CANONICAL public interface
│   ├── memory_bus.py           ← event routing
│   └── memory_models.py        ← memory data models
│
├── self_improvement/       (14 modules)
│   ├── safe_executor.py        ← sandboxed execution
│   ├── failure_collector.py    ← auto-collect from missions
│   └── ...                     ← improvement pipeline
│
├── deprecated/             (conceptual — stay in core/)
│   ├── orchestrator.py         ← → MetaOrchestrator
│   ├── action_queue.py         ← → CanonicalAction
│   ├── task_queue.py           ← → CanonicalAction
│   ├── approval_queue.py       ← → CanonicalAction
│   └── legacy_compat.py        ← compat bridge
│
└── result_aggregator.py        ← mission result → FinalOutput envelope

api/
├── main.py                     ← FastAPI app, router mounts, startup
├── _deps.py                    ← shared auth + getters
├── routes/                     ← 21 route modules
│   ├── missions.py             ← main mission CRUD
│   ├── mission_control.py      ← v1 approve/reject/cancel
│   ├── trace.py                ← v1 trace endpoint
│   └── ...                     ← 18 other route files
└── mission_store.py            ← MissionStateStore
```

## Pipeline (MetaOrchestrator — 12 phases)

```
1. classify      → mission type detection
2. assemble      → context assembly
3. pre-assess    → confidence + tool health
4. plan          → strategy selection
5. approve       → risk-based approval gate
6. execute       → agent execution
7. validate      → output validation
8. format        → output formatting
9. reflect       → mission reflection
10. learn        → learning loop
11. record       → memory + skill refinement
12. trace        → decision trace
```

## Singleton Access Pattern

| Component | Getter |
|-----------|--------|
| MetaOrchestrator | `get_meta_orchestrator()` |
| MissionSystem | `get_mission_system()` |
| MemoryFacade | `get_memory_facade()` |
| ToolExecutor | `ToolExecutor()` (instantiated) |
| EventCollector | `get_event_collector()` |
| CapabilityRegistry | `get_capability_registry()` |
| ActionQueue | `get_action_queue()` **(DEPRECATED)** |
| TaskQueue | `get_core_task_queue()` **(DEPRECATED)** |

## Data Flow

```
Flutter App
    │
    ▼
POST /api/v1/mission/run ──→ MissionSystem.submit()
    │                              │
    │                              ├── generate_trace_id()
    │                              ├── set_trace(trace_id, mission_id)
    │                              └── decision_trace.trace_id = trace_id
    │
POST /approve ──→ MissionSystem → ActionExecutor
    │                                    │
    │                              ├── tool_executor (emit tool_call events)
    │                              ├── capability_registry.check_permission()
    │                              └── result_aggregator.aggregate_mission_result()
    │                                         │
    │                                   ├── FinalOutput (markdown → final_output)
    │                                   └── Envelope (JSON → decision_trace.result_envelope)
    │
GET /missions/{id} ──→ { final_output, result_envelope }
GET /trace/{id} ──→ EventCollector.get_trace()
```

## Module Count

| Category | Count |
|----------|-------|
| core/*.py (flat) | 94 |
| core/skills/ | 7 |
| core/schemas/ | 2 |
| core/capabilities/ | 3 |
| core/observability/ | 2 |
| core/security/ | 2 |
| core/actions/ | 2 |
| core/self_improvement/ | 14 |
| api/routes/ | 21 |
| tests/ | 19+ |
| **Total core** | **~147** |
