# Self-Improvement Readiness Audit

## Date: 2026-03-27
## Auditor: Architecture review of core/self_improvement/

---

## EXISTING COMPONENTS (14 modules, ~85K chars)

| Module | Role | Status | Reusable |
|--------|------|--------|----------|
| failure_collector.py | Collects FailureEntry from MissionStateStore | ✅ Working | YES |
| improvement_planner.py | Rule-based ImprovementProposal from failures | ✅ Working | YES |
| candidate_generator.py | Generates ImprovementCandidate from Weakness list | ✅ Working | YES |
| weakness_detector.py | Detects weaknesses from capability scores, patterns | ✅ Working | YES |
| improvement_scorer.py | Scores/ranks candidates by gain×risk×novelty | ✅ Working | YES |
| safe_executor.py | Applies ONE candidate safely, atomic writes, rollback | ✅ Working | YES |
| deployment_gate.py | GateDecision: approve/reject based on mode, risk, protected files | ✅ Working | YES |
| validation_runner.py | HTTP-based test suite against VPS | ✅ Working | YES |
| improvement_memory.py | JSONL persistence of improvement history | ✅ Working | YES |
| patch_builder.py | Transforms ImprovementProposal → PatchCandidate | ✅ Working | YES |
| protected_paths.py | Frozen sets of files that cannot be auto-modified | ✅ Working | YES |
| engine.py | Facade (currently minimal — collects + plans) | ⚠️ Partial | EXTEND |
| __init__.py | Anti-loop guards (MAX_IMPROVEMENTS_PER_RUN=1) | ✅ Working | YES |
| legacy_adapter.py | Adapter shim | ⚠️ Minimal | SKIP |

## EXISTING v1 INFRASTRUCTURE

| Component | Integration Point | Self-improvement relevance |
|-----------|------------------|---------------------------|
| MetaOrchestrator | 12-phase pipeline | Can schedule improvement after phase 12 |
| PolicyEngine | cost/ROI evaluation | Can evaluate improvement cost vs. benefit |
| CanonicalAction | lifecycle model | Improvements tracked as actions |
| EventEnvelope | trace_id lifecycle | Improvement runs get trace_ids |
| BudgetTracker | per-mission cost | Limit improvement experiment cost |
| Capability Registry | tool permissions | Sandbox can restrict tool access |
| Result Envelope | FinalOutput | Improvement reports use same format |
| Startup Guard | production safety | Block unsafe self-improvement in production |
| 103 invariant tests | regression detection | Benchmark baseline for improvements |

## MISSING COMPONENTS

| Component | Needed For | Priority | Build From |
|-----------|-----------|----------|------------|
| **ImprovementGoalRegistry** | Measurable goals | HIGH | New module |
| **BenchmarkSuite** | Baseline evaluation | HIGH | Extend validation_runner.py |
| **ExperimentRunner** | Isolated experiment execution | HIGH | Combine safe_executor + validation_runner |
| **BaselineComparator** | Before/after comparison | HIGH | New module |
| **CriticReviewer** | Independent validation | MEDIUM | New module |
| **AdoptionGate** | Structured accept/reject | MEDIUM | Extend deployment_gate.py |
| **ImprovementReport** | Human-readable output | MEDIUM | New module |

## SAFEST INTEGRATION POINTS

1. **engine.py** — currently a minimal facade, perfect to extend into full orchestrator
2. **After MetaOrchestrator phase 12** — improvement detection can happen post-mission
3. **PolicyEngine.evaluate()** — already wired into tool_executor, improvement experiments respect it
4. **EventCollector** — improvement runs emit trace events naturally
5. **validation_runner.py** — already runs HTTP benchmarks, extend with more scenarios

## WHAT NOT TO TOUCH

- MetaOrchestrator internals (phases 1-12)
- CanonicalAction schema
- FinalOutput schema
- API endpoint contracts
- Startup guard
- Protected paths (core architecture files)

---

## IMPLEMENTATION PLAN

### Strategy: EXTEND existing modules, add missing ones, wire through engine.py

**Round 1 (core infrastructure):**
1. ImprovementGoalRegistry — measurable goals with metrics
2. BenchmarkSuite — extend validation_runner with scenario-based benchmarks
3. BaselineComparator — structured before/after comparison

**Round 2 (evaluation loop):**
4. CriticReviewer — independent validation layer
5. AdoptionGate — extend deployment_gate with structured decisions
6. ImprovementReport — human-readable reports

**Round 3 (wiring):**
7. Extend engine.py into full ImprovementLoop orchestrator
8. Wire observability (trace events for improvement runs)
9. Final integration tests

**Estimated: ~800-1000 new lines, 3 new modules, 2 extended modules**
