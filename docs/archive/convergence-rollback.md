# Convergence Rollback Playbook

## Feature Flags (kill switches)

| Flag | Controls | Default | Rollback |
|------|----------|---------|----------|
| `JARVIS_USE_CANONICAL_ORCHESTRATOR` | v3 API → MetaOrchestrator routing | OFF | `unset` → all API routes fall through to MissionSystem |
| `ENABLE_PLANNER_V3` / `PLANNER_VERSION` | Hierarchical planner | OFF/2 | `unset` → legacy Planner used |
| `ENABLE_KNOWLEDGE_GRAPH` | Pre-plan intelligence | OFF | `unset` → planner runs without graph context |
| `ENABLE_TOOL_EVOLUTION` | Tool improvement cycle | OFF | `unset` → no tool analysis |
| `ENABLE_LONG_HORIZON` | Multi-hour missions | OFF | `unset` → standard missions only |
| `ENABLE_AUTO_EVAL` | Output quality evaluation | OFF | `unset` → no evaluation |

## Rollback Scenarios

### R1: v3 API returns errors
```bash
# Disable canonical orchestrator — all /api/v3/ routes fall back to MissionSystem
unset JARVIS_USE_CANONICAL_ORCHESTRATOR
# Cockpit auto-falls back to /api/ legacy endpoints
```

### R2: Planning regression
```bash
unset ENABLE_PLANNER_V3
unset PLANNER_VERSION
# PlannerV3.plan() returns None → legacy Planner used
```

### R3: Full rollback (all convergence)
```bash
# Kill all feature flags
unset JARVIS_USE_CANONICAL_ORCHESTRATOR
unset ENABLE_PLANNER_V3
unset ENABLE_KNOWLEDGE_GRAPH
unset ENABLE_TOOL_EVOLUTION
unset ENABLE_LONG_HORIZON
unset ENABLE_AUTO_EVAL
unset PLANNER_VERSION
# System reverts to pre-convergence behavior
# No data migration needed — all new modules use separate stores
```

### R4: Revert git changes
```bash
# All convergence changes are on jarvis/* branches
# Master is untouched
# To fully revert: just don't merge the branches
git checkout master
```

## Architecture Guarantees

1. **No existing files modified** — all changes are new files
2. **No import side effects** — new modules only import when feature flags are ON
3. **No database schema changes** — all new storage is JSONL/JSON files
4. **No API contract changes** — v1/v2 routes preserved exactly as-is
5. **Cockpit fallback chain** — v3 → v2 → v1 for every API call

## Verification Checklist

After rollback, verify:
- [ ] `POST /api/mission` still works (MissionSystem.submit)
- [ ] `GET /api/missions` returns missions
- [ ] `POST /api/v2/missions/{id}/approve` works
- [ ] WebSocket `/api/v3/mission/{id}/stream` still connects
- [ ] Cockpit UI loads and functions (auto-fallback)
- [ ] No new error logs from disabled modules
