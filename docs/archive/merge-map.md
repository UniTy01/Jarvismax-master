# JarvisMax Branch Merge Map

Generated: 2026-03-26

## Branch Classification

### ✅ MERGE NOW (jarvis/* — linear chain, no conflicts)

| # | Branch | Commits | Lines | Key Files | Depends On |
|---|--------|---------|-------|-----------|------------|
| 1 | `jarvis/agent-team-init` | 2 | +1,913 | agents/jarvis_team/* (8 files) | master |
| 2 | `jarvis/hardening-batch-a` | 4 | +2,684 | tests/*, core/observability_helpers, env_validator, static_analysis | #1 |
| 3 | `jarvis/hardening-phase3` | 4 | +498 | tests/*, core/planner.py (except:pass→log) | #2 |
| 4 | `jarvis/introspection-phase4` | 1 | +1,187 | core/runtime_introspection.py | #3 |
| 5 | `jarvis/capability-intelligence` | 2 | +3,039 | core/capability_intelligence.py | #4 |
| 6 | `jarvis/agent-specialization` | 2 | +2,615 | core/agent_specialization.py | #5 |
| 7 | `jarvis/multi-mission-intelligence` | 1 | +1,634 | core/multi_mission_intelligence.py | #6 |

### ✅ MERGE NOW (jarvis/* — post-chain, independent new files)

| # | Branch | Commits | Lines | Key Files | Based On |
|---|--------|---------|-------|-----------|----------|
| 8 | `jarvis/orchestration-convergence` | 1 | +1,930 | core/canonical_types, orchestration_bridge, memory_facade | #7 |
| 9 | `jarvis/self-improvement-v2` | 1 | +1,944 | core/self_improvement_engine_v2.py | #8 |
| 10 | `jarvis/tool-builder-layer` | 1 | +1,494 | core/tool_builder_layer.py | #9 |
| 11 | `jarvis/app-cockpit` | 1 | +1,141 | static/cockpit.html, api/routes/cockpit.py | #10 |
| 12 | `jarvis/agent-workflow-advanced` | 1 | +1,750 | core/agent_workflow.py | #11 |
| 13 | `jarvis/observability-intelligence` | 1 | +1,102 | core/observability_intelligence.py | #12 |

### ✅ MERGE NOW (jarvis/* — expansion, independent new files)

| # | Branch | Commits | Lines | Key Files | Based On |
|---|--------|---------|-------|-----------|----------|
| 14 | `jarvis/planning-intelligence-v3` | 1 | +1,900 | core/planning/planner_v3.py | #13 |
| 15 | `jarvis/knowledge-graph-memory` | 1 | +1,243 | core/memory/knowledge_graph.py | #14 |
| 16 | `jarvis/tool-evolution-engine` | 1 | +1,334 | core/tools/evolution_engine.py | #15 |
| 17 | `jarvis/long-horizon-missions` | 1 | +1,276 | core/missions/long_horizon.py | #16 |
| 18 | `jarvis/auto-evaluator` | 1 | +981 | core/evaluation/auto_evaluator.py | #17 |
| 19 | `jarvis/capability-expansion-integration` | 1 | +633 | core/capability_expansion.py, docs/ | #18 |
| 20 | `jarvis/final-convergence` | 3 | +2,460 | api/routes/convergence.py, core/intelligence_hooks, legacy_compat, docs/ | #8 (orch-convergence) |

### ⚠️ MERGE LATER (claude/* — need review)

| Branch | Commits | Lines | Conflict Risk | Notes |
|--------|---------|-------|---------------|-------|
| `claude/jolly-villani` | 5 | +248 | LOW — only `api/main.py` overlap, different sections | Accumulated fixes: dashboard, approval, night_worker |
| `claude/naughty-einstein` | 1 | +420 | NONE — all new files in `core/knowledge_expansion/` | Knowledge expansion guards |
| `claude/romantic-euclid` | 1 | +125 | LOW — touches `api/main.py`, `agents/parallel_executor.py` | Workspace cleaner |
| `claude/competent-haibt` | 1 | +30 | NONE — all new files in `self_improvement/` | Deployment gate |
| `claude/vigilant-matsumoto` | 1 | +286 | NONE — single doc file | Foundation audit |

### 🚫 SUPERSEDED (do NOT merge)

| Branch | Superseded By | Reason |
|--------|---------------|--------|
| `claude/tool-intelligence-v1` | `jarvis/capability-intelligence` | 0 actual commits; our module is +3,039 lines with 38 tests |
| `claude/pipeline-hardening` | `jarvis/hardening-batch-a` + `jarvis/hardening-phase3` | 0 actual commits; our modules are +3,182 lines with 168 tests |
| `claude/self-improvement-loop` | `jarvis/self-improvement-v2` | 0 actual commits; our module is +1,944 lines with 26 tests |
| `claude/langgraph-integration` | N/A (archive candidate) | 0 actual commits; dormant experiment |

### 🗑️ OBSOLETE (24 empty claude/* branches)

All remaining `claude/*` branches have 0 commits ahead of master. Safe to delete:
`awesome-agnesi`, `cool-perlman`, `cranky-volhard`, `crazy-bhabha`, `determined-feistel`,
`ecstatic-hypatia`, `elegant-shamir`, `epic-chatelet`, `festive-morse`,
`intelligent-swanson`, `laughing-lehmann`, `mystifying-tharp`, `naughty-mcnulty`,
`nice-payne`, `objective-dewdney`, `practical-perlman`, `tender-jennings`,
`vigorous-beaver`, `xenodochial-lamarr`, plus the 4 superseded above.

## Merge Order (Recommended)

### Phase A — Foundation (sequential merge, linear chain)
```
master ← agent-team-init ← hardening-batch-a ← hardening-phase3
       ← introspection-phase4 ← capability-intelligence
       ← agent-specialization ← multi-mission-intelligence
```
**7 merges, fast-forward safe, zero conflict risk.**

### Phase B — Infrastructure (sequential, each adds new files)
```
← orchestration-convergence ← self-improvement-v2 ← tool-builder-layer
← app-cockpit ← agent-workflow-advanced ← observability-intelligence
```
**6 merges, fast-forward safe.**

### Phase C — Expansion (sequential, all new files)
```
← planning-intelligence-v3 ← knowledge-graph-memory ← tool-evolution-engine
← long-horizon-missions ← auto-evaluator ← capability-expansion-integration
```
**6 merges, fast-forward safe.**

### Phase D — Convergence
```
← final-convergence
```
**1 merge. Based on orchestration-convergence, may need rebase onto Phase C tip.**

### Phase E — Claude cleanup (after jarvis merged)
```
← claude/jolly-villani (review needed — accumulated fixes)
← claude/naughty-einstein (review — knowledge expansion)
← claude/romantic-euclid (review — workspace cleaner)
← claude/competent-haibt (review — deployment gate)
```
**4 merges, each needs review. Low conflict risk.**

## Conflict Analysis

| File | jarvis/ changes | claude/ changes | Risk |
|------|----------------|-----------------|------|
| `api/main.py` | Line 773: except:pass→log.debug | Lines 125-470: monitoring dedup + execution_trace | LOW — different sections |
| All other files | New files only | New files only | NONE |
