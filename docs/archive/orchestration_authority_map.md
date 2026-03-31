# Orchestration Authority Map

**Phase C.1 — Who Owns What Today**
**Date:** 2026-03-26

---

## Authority Matrix

| Responsibility | MissionSystem | MetaOrchestrator | WorkflowGraph | LangGraph Flow |
|---|---|---|---|---|
| **Creates missions** | ✅ `submit()` — generates ID, plan, advisory | ✅ `run_mission()` — generates ID, MissionContext | ✅ `run_mission()` — generates ID via graph | ❌ Dormant |
| **Updates status** | ✅ Own enum (8 values) | ✅ Own enum (6 values) | ✅ Own enum (WorkflowStage, 6 values) | ❌ |
| **Routes tasks** | ✅ `detect_intent()` + `domain_router` + `AgentSelector` | ❌ Delegates to JarvisOrchestrator | ✅ `_plan_node()` calls `detect_intent` + `TaskRouter` | ❌ |
| **Requests approval** | ✅ `evaluate_approval()` → PENDING_VALIDATION | ❌ No approval concept | ✅ `interrupt()` → human-in-loop | ✅ `approval_gate_node` (dormant) |
| **Stores memory** | ❌ | ❌ | ❌ | ✅ `memory_read_node` + `memory_write_node` (dormant) |
| **Handles retries** | ❌ | ❌ (delegates to JarvisOrchestrator) | ❌ | ❌ |
| **Handles failure** | ✅ Sets BLOCKED/REJECTED | ✅ Transitions to FAILED | ✅ Sets FAILED stage | ❌ |
| **Signals completion** | ✅ Sets DONE | ✅ Transitions REVIEW → DONE | ✅ Sets DONE stage | ❌ |

## Call Graph (Who Calls Whom)

```
API Layer:
  POST /api/mission        → MissionSystem.submit()      [DIRECT]
  GET  /api/missions       → MissionSystem.list_missions() [DIRECT]
  POST /api/v2/missions    → WorkflowGraph.run_mission()  [DIRECT]
  POST /api/v2/.../approve → WorkflowGraph.approve()      [DIRECT]

Internal:
  core/__init__.py         → exports MetaOrchestrator     [CANONICAL]
  WorkflowGraph._execute   → MissionSystem.submit()       [CIRCULAR]
  action_executor          → MissionSystem.get/submit      [DIRECT]
  mission_repair           → MissionSystem.get             [DIRECT]

Never called from API:
  MetaOrchestrator.run_mission()  ← exported but NOT used by API
```

## Critical Contradictions

### 1. MetaOrchestrator is canonical but unused
`core/__init__.py` exports it. The docstring says "TOUJOURS utiliser MetaOrchestrator".
But `control_api.py` calls `get_mission_system()` directly. No API endpoint uses MetaOrchestrator.

### 2. WorkflowGraph creates a circular dependency
`WorkflowGraph._execute_node()` calls `MissionSystem.submit()` — so WorkflowGraph
wraps MissionSystem, but MissionSystem also runs independently. Two mission IDs
could be created for the same user intent.

### 3. Three separate status machines with incompatible states
- MissionSystem: ANALYZING → PENDING_VALIDATION → APPROVED → EXECUTING → DONE
- MetaOrchestrator: CREATED → PLANNED → RUNNING → REVIEW → DONE
- WorkflowGraph: PLANNING → SHADOW_CHECK → AWAITING_APPROVAL → EXECUTING → DONE

No mapping exists between them. A mission in MissionSystem's "APPROVED" has no
equivalent in MetaOrchestrator's states.

### 4. Approval lives in three places
- `core/approval_queue.py` — generic action approval (file-based queue)
- `MissionSystem.evaluate_approval()` — inline approval logic (mode-based)
- `WorkflowGraph._approval_gate_node()` — LangGraph interrupt (graph-based)

### 5. Two independent `_MISSION_TOOLS` dictionaries
- `core/tool_registry.py:94` and `core/tool_runner.py:12`
  Both map mission_type → tool lists. No shared source. Can diverge silently.

## Current Production Path (What Actually Runs)

```
User (Telegram/API)
  │
  ▼
POST /api/mission
  │
  ▼
MissionSystem.submit()
  ├─ detect_intent()
  ├─ domain_router.route()
  ├─ _build_plan()
  ├─ compute_risk_score()
  ├─ AgentSelector.select_agents()
  ├─ ShadowAdvisor._evaluate_advisory()
  ├─ ShadowGate.check_advisory()
  ├─ _create_actions() → ActionQueue
  ├─ evaluate_approval()
  └─ → PENDING_VALIDATION or APPROVED
       │
       ▼
  ActionQueue.execute() or human approve
       │
       ▼
  action_executor → agent_runner → agents
       │
       ▼
  MissionSystem: status → DONE
```

MetaOrchestrator and WorkflowGraph are **not in the active production path**.
The v2 API exists but is secondary to v1.

## Memory Authority

| System | Write | Read | Storage |
|---|---|---|---|
| `memory/memory_bus.py` (MemoryBus) | ✅ `remember()` | ✅ `search()` | Routes to store/vector/patches/failures |
| `core/tools/memory_toolkit.py` | ✅ 7 functions | ✅ search | Direct Qdrant |
| `core/improvement_memory.py` | ✅ | ✅ | Qdrant + JSONL |
| `core/knowledge_memory.py` | ✅ | ✅ | Qdrant |
| `memory/decision_memory.py` | ✅ | ✅ | Qdrant |
| `core/memory.py` (MemoryBank) | ✅ | ✅ | JSON file |
| `core/system_state.py` | ✅ | ✅ | JSON file |

**MemoryBus already exists** as a partial unified interface but is not used by the orchestrator or API.
