# Legacy Paths Status — Isolated 🔒

## Purpose

Legacy modules are kept for backward compatibility but MUST NOT be extended.
New code MUST use canonical replacements.

---

## Legacy Modules

| Module | Lines | Status | Canonical Replacement | Active Dependents |
|--------|-------|--------|----------------------|-------------------|
| core/orchestrator.py | 1,055 | **DEPRECATED** | MetaOrchestrator | meta_orchestrator.py (delegate) |
| core/orchestrator_v2.py | ~200 | **DEPRECATED** | MetaOrchestrator | convergence routes |
| core/action_queue.py | ~400 | **DEPRECATED** | CanonicalAction | action_executor, mission_system, result_aggregator, API routes |
| core/task_queue.py | ~250 | **DEPRECATED** | CanonicalAction | background_dispatcher, API routes |
| core/approval_queue.py | ~150 | **DEPRECATED** | CanonicalAction.request_approval() | approval routes |
| core/legacy_compat.py | ~100 | **DEPRECATED** | N/A (compat bridge) | convergence routes |

## Legacy API Aliases

| Endpoint | Canonical Replacement | Notes |
|----------|----------------------|-------|
| POST /api/mission | POST /api/v1/mission/run | Legacy v0 |
| GET /api/missions | GET /api/v1/missions | Legacy v0 |
| GET /api/stats | GET /api/v2/system/health | Legacy v0 |
| POST /api/v2/missions/submit | POST /api/v1/mission/run | v2 alias |
| POST /api/v2/task | — | Task queue model (deprecated) |
| POST /api/v2/tasks/{id}/approve | POST /api/v1/missions/{id}/approve | v2 alias |

## Isolation Rules

1. **DO NOT** add new features to deprecated modules
2. **DO NOT** create new imports of deprecated modules
3. **DO** use `CanonicalAction.from_legacy_action()` to bridge existing code
4. **DO** use `get_canonical_actions(mission_id)` for unified view
5. Legacy modules will be absorbed in a future major version

## Dependency Analysis

### core/action_queue.py (most coupled)
```
core/improve_bridge.py      → get_action_queue()
core/background_dispatcher.py → (indirect)
core/mission_repair.py      → get_action_queue()
core/result_aggregator.py   → get_action_queue()
core/action_executor.py     → get_action_queue() [3 callsites]
core/mission_system.py      → get_action_queue()
api/routes/missions.py      → get_action_queue() [2 callsites]
api/routes/mission_control.py → get_action_queue()
```

### core/orchestrator.py (delegate bridge)
```
core/meta_orchestrator.py   → delegates some phases
api/routes/convergence.py   → fallback path
```

## Migration Plan (Future)

1. Replace `action_queue` callsites with `CanonicalAction` + `get_canonical_actions()`
2. Replace `task_queue` callsites with `CanonicalAction`
3. Inline `orchestrator.py` delegate methods into `meta_orchestrator.py`
4. Remove `legacy_compat.py` after convergence routes cleanup
5. Remove empty modules

**NOT scheduled for v1. Planned for v2.**
