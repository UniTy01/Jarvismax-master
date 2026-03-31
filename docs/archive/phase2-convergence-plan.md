# Phase 2 — Orchestrator Convergence Plan

## Status: PROPOSED (awaiting approval)

## Current State

Two parallel systems manage missions independently:

| System | File | Role |
|---|---|---|
| `MissionSystem` | `core/mission_system.py` | Sync plan builder, risk scoring, advisory, action queue, approval flow |
| `MetaOrchestrator` | `core/meta_orchestrator.py` | Async state machine (CREATED→PLANNED→RUNNING→REVIEW→DONE), delegates to JarvisOrchestrator |

### Problem
- `MissionSystem.submit()` and `MetaOrchestrator.run_mission()` are **independent entry points**
- API routes (`api/main.py`, `api/routes/mission_control.py`) call `MissionSystem` directly
- The bot/orchestrator path goes through `MetaOrchestrator` → `JarvisOrchestrator`
- No shared state between the two — a mission submitted via API doesn't go through MetaOrchestrator's state machine

### Dependency Map (MissionSystem consumers)
- `api/main.py` — 10+ call sites via `_get_mission_system()`
- `api/routes/mission_control.py` — 6 call sites
- `api/routes/monitoring.py` — 2 call sites
- `api/control_api.py` — 3 call sites
- `core/workflow_graph.py` — 2 call sites (detect_intent, get_mission_system)
- `core/action_executor.py` — 2 call sites
- `core/mission_repair.py` — 1 call site
- `executor/handlers.py` — 1 call site
- `agents/monitoring_agent.py` — 1 call site
- `agents/crew.py` — 1 call site (is_capability_query)
- `self_improvement/failure_collector.py` — 1 call site
- Tests: `test_control_layer.py`, `test_improvements.py`

### Dependency Map (MetaOrchestrator consumers)
- `core/__init__.py` — canonical re-export
- `core/orchestrator_lg/langgraph_flow.py` — executor_node
- `core/orchestrator.py` — deprecation header
- `core/orchestrator_v2.py` — deprecation header

## Convergence Goal

**MissionSystem becomes a thin wrapper that delegates to MetaOrchestrator.**

MissionSystem keeps its public API surface (`submit()`, `approve()`, `complete()`, `reject()`, `get()`, `list_missions()`, `stats()`) — but internally it:
1. Creates a `MissionContext` in MetaOrchestrator
2. Maps its own statuses to MetaOrchestrator's state machine
3. Delegates execution to MetaOrchestrator

## Constraints (from Max)
- **Stability first** — no breaking changes
- **Small diffs** — incremental steps
- **No behavior change** — external API surface stays identical

## Phased Approach

### Step 1: Bridge MissionSystem → MetaOrchestrator (this PR)
- Add `_meta` field to `MissionSystem.__init__()` (lazy MetaOrchestrator ref)
- In `MissionSystem.submit()`, after building the plan and running advisory:
  - Register the mission in MetaOrchestrator's `_missions` dict as a `MissionContext`
  - Map MissionSystem statuses → MetaOrchestrator statuses
- In `complete()` / `reject()` / `approve()`: update MetaOrchestrator state too
- **No behavior change** — existing logic stays, MetaOrchestrator is notified as a side effect
- **Fail-open** — if MetaOrchestrator fails, MissionSystem continues as before

### Step 2: Shared status view (future PR)
- `MetaOrchestrator.get_status()` includes MissionSystem missions
- API `/status` endpoint shows unified view

### Step 3: Execution delegation (future PR)  
- `MissionSystem.submit()` delegates actual agent execution to `MetaOrchestrator.run_mission()`
- MissionSystem becomes purely a plan+approval layer

### Step 4: Consolidate models (future PR)
- Unify `MissionResult` ↔ `MissionContext` into a single model
- MissionSystem's `MissionResult` wraps or extends `MissionContext`

## Status Mapping

| MissionSystem | MetaOrchestrator |
|---|---|
| ANALYZING | CREATED |
| PENDING_VALIDATION | PLANNED |
| APPROVED | PLANNED (approved, ready to run) |
| EXECUTING | RUNNING |
| DONE | DONE |
| REJECTED | FAILED |
| BLOCKED | FAILED |
| PLAN_ONLY | DONE (metadata: plan_only=true) |

## Risk Assessment
- **Risk score:** 2/10 (LOW)
- Step 1 is purely additive — no existing behavior changes
- All MetaOrchestrator calls wrapped in try/except (fail-open)
- Existing tests continue to pass unchanged
- Rollback = revert the single commit
