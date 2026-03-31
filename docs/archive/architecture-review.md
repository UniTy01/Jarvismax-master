# JarvisMax — Architecture Review & Target State

**Author:** Jarvis (Architect Supervisor)
**Date:** 2026-03-26
**Status:** ACTIVE — Living document

---

## 1. Current State Assessment

### 1.1 What Exists

**4 orchestration paths** (this is the #1 structural problem):

| System | File | Lines | Status |
|---|---|---|---|
| MissionSystem | `core/mission_system.py` | 1155 | **Active** — sync, 25+ API consumers |
| MetaOrchestrator | `core/meta_orchestrator.py` | 330 | **Active** — async state machine, canonical via `core/__init__.py` |
| WorkflowGraph | `core/workflow_graph.py` | 622 | **Active** — LangGraph HIL with shadow advisor |
| LangGraph Flow | `core/orchestrator_lg/langgraph_flow.py` | 373 | **Dormant** — requires `USE_LANGGRAPH=true` |

**Problem:** WorkflowGraph calls MissionSystem internally. MetaOrchestrator is the canonical export (`core/__init__.py`). The API layer (`control_api.py`) uses MissionSystem directly. Nobody calls MetaOrchestrator from the API. LangGraph Flow is a parallel experiment. These four systems don't share state, don't share status enums (two `MissionStatus` definitions), and can conflict.

**7 local branches** (linear chain, not merged):
```
master → agent-team-init → hardening-batch-a → hardening-phase3
       → introspection-phase4 → capability-intelligence
       → agent-specialization → multi-mission-intelligence
```
All purely additive. No production code modified except 12 `except:pass` → `log.debug()`.

**27 remote `claude/*` branches** — prior work by another agent. Some overlap with our work (tool intelligence, pipeline hardening, agent SOULs).

### 1.2 Enum/Type Duplication

| Concept | Locations | Problem |
|---|---|---|
| `MissionStatus` | `mission_system.py` (8 values), `meta_orchestrator.py` (6 values) | **Different enums, different values.** ANALYZING vs CREATED, PLAN_ONLY has no equivalent |
| `RiskLevel` | `state.py` (LOW/MED/HIGH), `approval_queue.py` (6 values incl. INFRA/DEPLOY) | Incompatible hierarchies |
| `ErrorSeverity` | `contracts.py`, `system_state.py` | Duplicated, different members |
| Priority/Urgency | `goal_manager.py` (GoalPriority int), `multi_mission_intelligence.py` (Urgency str) | Parallel concepts, no bridge |
| Tool registry | `tool_registry.py`, `tool_runner.py` (both define `_MISSION_TOOLS`) | **Duplicated dict with potentially divergent mappings** |

### 1.3 Memory Architecture (Fragmented)

| Layer | Location | Storage |
|---|---|---|
| ImprovementMemory | `core/improvement_memory.py` | Qdrant + JSONL fallback |
| SelfImprovementMemory | `core/self_improvement/improvement_memory.py` | **Different class, same name pattern** |
| KnowledgeMemory | `core/knowledge_memory.py` | Qdrant |
| DecisionMemory | `memory/decision_memory.py` | Qdrant |
| Memory Toolkit (tools) | `core/tools/memory_toolkit.py` | Qdrant (7 functions) |
| ObjectiveStore | `core/objectives/objective_store.py` | Qdrant |
| SystemState | `core/system_state.py` | JSON file |
| Our knowledge | `workspace/knowledge_store.jsonl` | JSONL (13 patterns) |
| Our decisions | `workspace/decisions.jsonl` | JSONL (7 decisions) |

**Problem:** 6+ separate memory systems, no unified query surface, no lifecycle management.

---

## 2. Target Architecture

### 2.1 Canonical Orchestrator

```
                     ┌────────────────────────────┐
                     │      API / Telegram / UI    │
                     └──────────┬─────────────────┘
                                │
                     ┌──────────▼─────────────────┐
                     │    MetaOrchestrator (async) │  ← canonical entry point
                     │    run_mission() / run()    │
                     └──────────┬─────────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                  │
     ┌────────▼──────┐  ┌──────▼──────┐  ┌───────▼──────┐
     │ MissionSystem │  │ WorkflowGraph│  │ AgentRunner  │
     │ (plan+intent) │  │ (HIL+shadow)│  │ (execution)  │
     └───────────────┘  └─────────────┘  └──────────────┘
```

**Rules:**
1. **MetaOrchestrator is the sole entry point.** All API endpoints, all consumers call `get_meta_orchestrator().run_mission()`.
2. **MissionSystem becomes a planning service.** It analyzes intent, builds plans, runs shadow advisor. It does NOT execute. Remove `submit()` as a full-cycle entry point; expose `analyze()` and `plan()`.
3. **WorkflowGraph becomes the execution engine.** Owns the state machine: PLANNING → SHADOW_CHECK → APPROVAL → EXECUTING → DONE.
4. **LangGraph Flow is archived or merged into WorkflowGraph.** Two graph-based systems is one too many.
5. **One MissionStatus enum.** Defined in `core/state.py`. Both systems import from there.

### 2.2 Canonical Mission Lifecycle

```
USER INPUT
    │
    ▼
[1] INTENT DETECTION          (MissionSystem.detect_intent)
    │
    ▼
[2] PLANNING                  (MissionSystem.plan → MissionPlan)
    │
    ▼
[3] RISK ASSESSMENT           (ShadowAdvisor.evaluate)
    │
    ▼
[4] APPROVAL GATE             (ApprovalQueue if risk >= WRITE_HIGH)
    │   │
    │   ├── AUTO-APPROVE (read, write_low)
    │   └── HUMAN-APPROVE (write_high, infra, delete, deploy)
    │
    ▼
[5] EXECUTION                 (AgentRunner → agent steps)
    │
    ▼
[6] VERIFICATION              (ExecutionGuard.guard_*)
    │
    ▼
[7] REVIEW                    (lens-reviewer agent)
    │
    ▼
[8] OUTCOME RECORDING         (MultiMissionIntelligence.record)
    │
    ▼
DONE / FAILED
```

### 2.3 Canonical Approval Pipeline

```
core/approval_queue.py — SINGLE approval authority

RiskLevel hierarchy (from core/state.py):
    READ         → auto-approve, no queue
    WRITE_LOW    → auto-approve, logged
    WRITE_HIGH   → queue, human approval required
    INFRA        → queue, human approval required
    DELETE       → queue, human approval required
    DEPLOY       → queue, human approval required

Queue storage: workspace/approval_queue/pending.json
Approval surfaces: API POST, Telegram inline buttons, CLI
```

**Current gap:** `core/state.py` defines `RiskLevel(LOW/MEDIUM/HIGH)` and `core/approval_queue.py` defines a separate `RiskLevel` with 6 values. These must converge.

### 2.4 Canonical Memory Architecture

```
┌────────────────────────────────────────────────┐
│              MemoryFacade (new)                 │
│   .store(content, type, tags)                  │
│   .search(query, type?, top_k?)                │
│   .get_recent(type, n)                         │
│   .cleanup(older_than?)                        │
└──────────────┬─────────────────────────────────┘
               │
    ┌──────────┼──────────┬──────────┐
    ▼          ▼          ▼          ▼
 Qdrant    JSONL       SQLite    SystemState
 (vector)  (fallback)  (struct)  (runtime)
```

**Types:** solution, error, patch, decision, pattern, objective, mission_outcome
**Lifecycle:** TTL-based expiry (memory_toolkit already has this), dedup (exists), summarization (batch)

### 2.5 Canonical Agent Structure

```
agents/
├── crew.py                    # AgentCrew registry
├── registry.py                # Agent metadata
├── jarvis_team/               # Meta-level agents (our work)
│   ├── base.py                # JarvisTeamAgent
│   ├── tools.py               # 33 tools + access matrix
│   ├── architect.py
│   ├── coder.py
│   ├── reviewer.py
│   ├── qa.py
│   ├── devops.py
│   └── watcher.py
├── autonomous/                # Autonomous operation agents
├── shadow_advisor/            # Risk evaluation
└── [operational agents]       # scout, forge, lens, vault, pulse, etc.
```

**Rule:** Every agent must:
1. Have a registered name in `AgentCrew`
2. Define `ROLE`, `ALLOWED_TOOLS` from the access matrix
3. Return structured output via `core/contracts.AgentResult`
4. Handle failures gracefully (never crash the pipeline)

### 2.6 Canonical UI Contract

```
API (api/) serves:
    GET  /api/v2/missions              → list missions
    POST /api/v2/missions              → submit new mission
    GET  /api/v2/missions/{id}         → mission detail
    POST /api/v2/missions/{id}/approve → approve
    POST /api/v2/missions/{id}/reject  → reject
    WS   /ws/stream                    → real-time events

Response schema (api/schemas.py):
    { "status": "ok"|"error", "data": {...} }

Event stream (api/event_emitter.py + ws_hub.py):
    mission.created, mission.planned, mission.approved,
    mission.step_started, mission.step_completed,
    mission.done, mission.failed
```

---

## 3. Branch Review — Verdicts

### 3.1 `jarvis/agent-team-init` — ✅ APPROVE

**+2,279 lines** | 2 commits | 13 files

Adds 6 meta-agents with tool access matrix. Clean isolation. No production changes.

**Issues:** None structural.
**Risk:** Low. Purely additive.
**Action:** Merge first (foundation for other branches).

### 3.2 `jarvis/hardening-batch-a` — ✅ APPROVE

**+2,318 lines on top of agent-team** | 4 commits | 15 new files

Tests for 9 untested modules. Observability helpers. Env validator. Static analysis.

**Issues:**
- `core/static_analysis.py` partially overlaps with `claude/pipeline-hardening` (which has `core/tool_intelligence/` with similar code analysis)
- Tests use `ast.parse()` only, not runtime pytest (sandbox limitation)

**Risk:** Low. Test-only + utility modules.
**Action:** Merge after agent-team-init.

### 3.3 `jarvis/hardening-phase3` — ✅ APPROVE

**+498 lines on top of batch-a** | 4 commits

12 `except:pass` → `log.debug()`. Edge case tests. Docstrings. Knowledge extraction.

**Issues:** None. Surgical changes to production code, all verified.
**Risk:** Minimal. The except:pass changes are the only production modifications across all 7 branches.
**Action:** Merge after hardening-batch-a.

### 3.4 `jarvis/introspection-phase4` — ✅ APPROVE

**+1,187 lines** | 1 commit | 2 new files

Runtime self-awareness. Tool health checks. Error classification.

**Issues:**
- `classify_error()` has 16 categories. `core/system_state.py` has its own `ErrorSeverity`. `core/contracts.py` has `RootCauseType`. Three parallel error taxonomies.
- **Recommendation:** Future work should define a single `core/error_taxonomy.py`.

**Risk:** Low. Standalone module, no imports from production code (except lazy `tool_registry`).
**Action:** Merge after phase3.

### 3.5 `jarvis/capability-intelligence` — ✅ APPROVE (with note)

**+3,039 lines** | 2 commits

Tool profiling, capability graph, auto-discovery, reliability tracking.

**Issues:**
- ⚠️ **Overlap with `claude/tool-intelligence-v1`** — that remote branch has `TOOL_INTELLIGENCE_REPORT.md`, `core/tool_intelligence/tool_scorer.py`, `tool_observer.py`, `planner_hints.py`. Our `capability_intelligence.py` covers similar ground (tool scoring, reliability) but with different data structures. **These must not both be active.**
- Tool profiles are hardcoded (64 tools). If tool registry changes, profiles go stale.

**Risk:** Medium — overlap risk with remote branch.
**Action:** Merge, but document that `claude/tool-intelligence-v1` is **superseded** by this work. Do not merge both.

### 3.6 `jarvis/agent-specialization` — ✅ APPROVE

**+2,615 lines** | 2 commits

Task clustering, agent archetypes, specialization heuristics.

**Issues:**
- Agent archetype list is static. If new agents are added, archetypes go stale.
- Config templates define `model_tier` but there's no model tier system in the codebase yet.

**Risk:** Low. Observational only.
**Action:** Merge after capability-intelligence.

### 3.7 `jarvis/multi-mission-intelligence` — ✅ APPROVE (with note)

**+1,634 lines** | 1 commit

Priority scoring, parallel safety, resource conflicts, queue intelligence, outcome memory.

**Issues:**
- ⚠️ `Urgency` enum in this module vs `GoalPriority` in `goal_manager.py` — parallel priority systems.
- Write-exclusive tool list is hardcoded (12 tools). Must stay in sync with tool registry.
- Outcome memory is in-memory only. Restarts lose all history.

**Risk:** Low. No execution changes.
**Action:** Merge last.

---

## 4. Overlap & Conflict Detection

### 4.1 Internal Overlaps (between jarvis/* branches)

| Overlap | Severity | Detail |
|---|---|---|
| Tool profiling | LOW | `capability_intelligence.py` profiles tools, `agent_specialization.py` maps tools to archetypes. Complementary, not conflicting. |
| Error classification | LOW | `runtime_introspection.py` classifies errors (16 cats), `observability_helpers.py` has `categorize_error()` (6 cats). Introspection is the superset. |
| Knowledge storage | NONE | All branches append to same JSONL files. Additive. |

**Verdict:** No blocking conflicts between jarvis/* branches. Linear merge is safe.

### 4.2 Conflicts with Remote `claude/*` Branches

| Branch | Conflict | Severity | Action |
|---|---|---|---|
| `claude/tool-intelligence-v1` | **Overlaps `capability-intelligence`** — both profile and score tools | **HIGH** | Mark superseded. Do NOT merge both. |
| `claude/pipeline-hardening` | Modifies `core/planner.py`, adds `core/tool_intelligence/`. Our work doesn't touch planner. | MEDIUM | Review before merging; planner changes may conflict with future convergence. |
| `claude/self-improvement-loop` | Adds self-improvement v1. Our `capability_intelligence` and `agent_specialization` inform but don't overlap. | LOW | Can coexist. |
| Other `claude/*` branches | Various experiments, mostly on master base. | LOW | Evaluate individually if merge is planned. |

### 4.3 Structural Debt

| Debt | Severity | Impact |
|---|---|---|
| **4 orchestration systems** | 🔴 CRITICAL | No clear authority. API uses MissionSystem, `__init__` exports MetaOrchestrator, WorkflowGraph wraps both, LangGraph is dormant. |
| **2 MissionStatus enums** | 🔴 HIGH | State transitions can't be validated across systems. |
| **2 RiskLevel enums** | 🟡 MEDIUM | Approval pipeline uses different risk model than session state. |
| **6+ memory systems** | 🟡 MEDIUM | No unified query. No lifecycle. No dedup across systems. |
| **2 _MISSION_TOOLS dicts** | 🟡 MEDIUM | `tool_registry.py` and `tool_runner.py` can diverge silently. |
| **204 except:pass blocks** | 🟡 MEDIUM | Only 12 hardened. Failure blindness in 192 locations. |
| **108 print statements** | 🟢 LOW | Should be structlog, but not critical. |

---

## 5. Merge Roadmap — Optimal Order

### Phase A: Foundation (sequential, no conflicts)

```
1. jarvis/agent-team-init        → master   (foundation)
2. jarvis/hardening-batch-a      → master   (tests + utilities)
3. jarvis/hardening-phase3       → master   (production hardening)
```

**These are safe to merge now.** Linear chain, each builds on previous.

### Phase B: Intelligence (sequential, depends on Phase A)

```
4. jarvis/introspection-phase4     → master   (self-awareness)
5. jarvis/capability-intelligence  → master   (tool understanding)
6. jarvis/agent-specialization     → master   (agent matching)
7. jarvis/multi-mission-intelligence → master (concurrent missions)
```

**These are safe after Phase A.** No production changes. Mark `claude/tool-intelligence-v1` as superseded before merging step 5.

### Phase C: Convergence (requires design, NOT YET SAFE)

```
8. Unify MissionStatus enums          → core/state.py
9. Unify RiskLevel enums              → core/state.py
10. MissionSystem → planning-only      → core/mission_system.py (PROTECTED)
11. MetaOrchestrator → sole entry      → API + consumers
12. Archive/merge LangGraph Flow       → core/orchestrator_lg/
13. Memory facade                      → core/memory_facade.py (new)
```

**Phase C modifies protected files.** Requires explicit Max approval per change. Design docs must precede implementation.

### Can Parallelize

- Phase A steps 1-3: **Sequential** (linear chain)
- Phase B steps 4-7: **Sequential** (linear chain)
- Phase C steps 8-9: **Parallel** (different files)
- Phase C steps 10-11: **Sequential** (10 before 11)
- Phase C step 13: **Parallel** with everything (new file)

---

## 6. Stability Validation Checklist (Pre-Merge)

Before any merge to master:

- [ ] `python3 -c "import ast; ast.parse(open(f).read())"` on every changed `.py`
- [ ] No new imports of protected modules
- [ ] No modification of protected files (unless Phase C with approval)
- [ ] All new modules have `try/except ImportError` for structlog
- [ ] All public functions have docstrings
- [ ] All new test files parse cleanly
- [ ] `git diff --stat` confirms expected file count
- [ ] No circular imports introduced (check with `python3 -c "from core.X import Y"`)

---

## 7. Decisions Log

| # | Decision | Rationale |
|---|---|---|
| D1 | Approve all 7 jarvis/* branches for merge | All purely additive, no production changes except 12 except:pass hardening |
| D2 | Mark `claude/tool-intelligence-v1` as superseded | Our capability-intelligence is more comprehensive (1075 vs scattered files) |
| D3 | Do NOT attempt orchestrator convergence yet | Requires modifying protected files, needs design doc + approval |
| D4 | Linear merge order (not squash) | Preserves commit history for auditing |
| D5 | Phase C requires per-file Max approval | Protected files = protected for a reason |

---

*This document is maintained by Jarvis in architect-supervisor role. Updated as work progresses.*
