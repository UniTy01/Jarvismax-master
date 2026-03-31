# Self-Improvement Architecture v1

## Status: CONTROLLED 🔒

Self-improvement is a **guardrailed extension** of the v1 baseline.
It does NOT replace MetaOrchestrator, modify canonical schemas, or bypass production auth.

---

## Loop

```
  ┌─────────────────────────────────────────────────────┐
  │                IMPROVEMENT LOOP                      │
  │                                                      │
  │  1. DETECT     ← WeaknessDetector + FailureCollector │
  │  2. PROPOSE    ← CandidateGenerator + Planner        │
  │  3. SCORE      ← ImprovementScorer                   │
  │  4. BENCHMARK  ← BenchmarkSuite (8 scenarios)        │
  │  5. COMPARE    ← Baseline vs Candidate               │
  │  6. CRITIQUE   ← ImprovementCritic (adversarial)     │
  │  7. DECIDE     ← AdoptionGate                        │
  │  8. ADOPT/REJECT                                     │
  │  9. RECORD     ← ImprovementEntry (memory)           │
  └─────────────────────────────────────────────────────┘
```

## Modules

### Existing (reused from core/self_improvement/)
| Module | Role |
|--------|------|
| failure_collector.py | Collects failure patterns from missions |
| weakness_detector.py | Identifies capability weaknesses |
| candidate_generator.py | Proposes small candidate improvements |
| improvement_planner.py | Rule-based improvement proposals |
| improvement_scorer.py | Scores candidates by gain×risk×novelty |
| safe_executor.py | Atomic file writes with rollback |
| deployment_gate.py | Mode-based deployment checks |
| validation_runner.py | HTTP test suite against VPS |
| improvement_memory.py | JSONL persistence |
| protected_paths.py | Files that cannot be auto-modified |

### New (added this session)
| Module | Role |
|--------|------|
| goal_registry.py | 8 measurable improvement goals |
| benchmark_suite.py | 8 benchmark scenarios with pass/fail rules |
| improvement_loop.py | Full evaluation pipeline + Critic + AdoptionGate |

## Safety Invariants

1. **No direct production modification** — all changes go through safe_executor with rollback
2. **Protected files** — meta_orchestrator, tool_executor, schemas, security = NEVER touched
3. **Anti-loop guard** — MAX_IMPROVEMENTS_PER_RUN = 1
4. **Critic adversarial review** — independent validation before adoption
5. **Auto-adopt only for LOW risk** — everything else requires human review
6. **PolicyEngine respected** — improvement experiments follow cost/budget rules

## Critic Checks

| Check | Hard Reject? |
|-------|-------------|
| Schema integrity violated | YES |
| Safety regression | YES |
| Trace integrity broken | NO (concern) |
| Cost inflation >20% | NO (concern) |
| More regressions than improvements | NO (concern) |
| Benchmark gaming (100% from <80%) | NO (concern) |
| Touches high-risk module | NO (concern) |

## Adoption Outcomes

| Outcome | When | Human Required |
|---------|------|---------------|
| AUTO_ADOPT | Low-risk, all pass, critic accepts (≥70% confidence) | No |
| APPROVE_FOR_REVIEW | Improvement found but non-trivial | Yes |
| ARCHIVE | Inconclusive results | No |
| REJECT | Safety/schema/security regression | No |

## Goals (8 registered)

| Goal | Direction | Importance |
|------|-----------|-----------|
| reduce_mission_cost | ↓ | HIGH |
| reduce_mission_latency | ↓ | HIGH |
| reduce_executor_failures | ↓ | HIGH |
| improve_success_rate | ↑ | CRITICAL |
| reduce_unnecessary_llm_calls | ↓ | MEDIUM |
| reduce_schema_violations | ↓ | CRITICAL |
| reduce_policy_false_blocks | ↓ | MEDIUM |
| improve_trace_completeness | ↑ | HIGH |
