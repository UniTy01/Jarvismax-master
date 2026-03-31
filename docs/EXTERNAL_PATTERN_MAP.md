# External Pattern Map — JarvisMax Full Upgrade Reference

## Methodology
For each Jarvis brick: current state → best external pattern → import/adapt/improve/reject.

---

## 1. MetaOrchestrator

**Current**: Keyword-based classifier + context assembly + supervised execution + decision trace + reflection + learning loop.

**Best patterns**:
- **LangGraph**: Stateful graph-based execution with checkpoints, conditional branching
- **ARC research**: Abstraction-first reasoning, generalize from examples

| Pattern | Decision | Justification |
|---------|----------|---------------|
| State checkpointing | ADAPTED TO JARVIS | Via reflection + decision trace (not full graph state) |
| Conditional branching | ADAPTED TO JARVIS | Mission classifier routes to execution strategies |
| Observation-action-reflection loop | IMPORTED + IMPROVED | Added reflection.py with heuristic scoring (no LLM call needed) |
| Graph DSL | REJECTED | Linear pipeline sufficient, graph adds complexity without value |
| ARC program synthesis | REJECTED | Research-grade, not production-ready |

---

## 2. Executor

**Current**: ExecutionResult contract + ErrorClass taxonomy + retry policy + execution engine.

**Best patterns**:
- **OpenHands**: Observation→Action→Observation loop, sandboxed execution, budget tracking
- **LangGraph**: Durable execution with replay

| Pattern | Decision | Justification |
|---------|----------|---------------|
| Structured Observation | IMPORTED | observation.py — typed, cost-tracked, provenance-tagged |
| Execution Budget | IMPORTED + IMPROVED | Token/cost/step limits with multi-dimensional enforcement |
| Output Validation | IMPORTED + IMPROVED | Secret leak detection + error masking + JSON format validation |
| Docker sandbox model | REJECTED | We have our own container model |
| Full execution replay | REJECTED | JSONL traces sufficient for debugging |

---

## 3. Memory

**Current**: MemoryFacade + ranker + compactor + decay + working memory.

**Best patterns**:
- **Hermes**: 4-layer memory (curated, searchable archive, skills, user model). Bounded context.
- **ARC**: Learning efficiency through abstraction and generalization

| Pattern | Decision | Justification |
|---------|----------|---------------|
| Bounded working memory | IMPORTED + IMPROVED | working_memory.py — token-budget-capped, relevance-ranked |
| Memory decay | IMPORTED | memory_decay.py — confidence decay for unused items |
| Memory linking | IMPROVED BEYOND REFERENCE | memory_linker.py — graph linking missions↔skills↔failures |
| Session archive (FTS5) | REJECTED | Our JSONL + cosine retrieval is simpler and sufficient |
| Honcho user modeling | REJECTED | Different product concept |

---

## 4. Skill System

**Current**: JSONL skills + cosine retriever + builder + dedup + service + refinement.

**Best patterns**:
- **Hermes/Voyager**: Skills as reusable procedures, improved on each use, versioned

| Pattern | Decision | Justification |
|---------|----------|---------------|
| Skill refinement on reuse | IMPORTED | refine_skill() boosts/degrades confidence |
| Skill versioning | ADAPTED TO JARVIS | Via use_count + confidence tracking (not full version history) |
| Problem-type matching | IMPROVED BEYOND REFERENCE | Retriever now boosts +0.15 for same problem_type |
| Markdown skill files | REJECTED | JSONL model is more machine-friendly |

---

## 5. Capability Layer

**Current**: CapabilityRequest/Result contracts + CapabilityDispatcher (native/plugin/MCP).

**Best patterns**:
- **OpenHands**: Unified tool interface, all capabilities return same contract
- **Hermes**: MCP as first-class capability

| Pattern | Decision | Justification |
|---------|----------|---------------|
| Unified capability contract | ALREADY IMPLEMENTED | CapabilityRequest/Result in contracts.py |
| Capability health tracking | IMPORTED + IMPROVED | capability_health.py — success rate, unhealthy detection |
| MCP as first-class | ALREADY IMPLEMENTED | MCP_TOOL in CapabilityType |
| Plugin auto-discovery | REJECTED | Explicit registration preferred for safety |

---

## 6. Mission Loop

**Current**: classify → assemble → plan → approve → execute → reflect → learn → record → refine → trace.

**Best patterns**:
- **LangGraph**: Plan → Execute → Observe → Reflect → Replan
- **ARC**: Abstract → Hypothesize → Test → Generalize

| Pattern | Decision | Justification |
|---------|----------|---------------|
| Reflection step | IMPORTED + IMPROVED | Pure heuristics, no LLM call needed |
| Learning loop | IMPORTED | Lesson extraction from failures/low-confidence |
| Replan capability | DEFERRED | Requires multi-step execution first |

---

## 7. Approval / Safety

**Current**: Risk-based gating in execution_supervisor, approval_queue, fail-closed for high/critical.

**Best patterns**:
- Enterprise agent safety: non-bypassable gates, audit trail, denial handling

| Pattern | Decision | Justification |
|---------|----------|---------------|
| Risk gating | ALREADY IMPLEMENTED | approval_queue + execution_supervisor |
| Output validation | IMPORTED | output_validator.py — secret leak detection |
| Audit trail | ALREADY IMPLEMENTED | DecisionTrace JSONL |
| Side-channel bypass prevention | ALREADY IMPLEMENTED | Single point in supervisor |

---

## 8. Observability

**Best patterns**:
- **LangSmith**: Structured traces with token counts, latencies, costs per step

| Pattern | Decision | Justification |
|---------|----------|---------------|
| Cost tracking per mission | IMPORTED | DecisionTrace.record_cost() |
| Capability health dashboard | IMPORTED | capability_health.py stats |
| Memory link graph | IMPROVED BEYOND REFERENCE | memory_linker.py for cross-entity queries |

---

## 9. Self-Improvement

**Current**: Full pipeline — analyze → detect → propose → sandbox-test → promote.

**Best patterns**:
- **Hermes**: Skills improve during use, agent nudges itself to persist knowledge
- **ARC**: Refinement loops with validation

| Pattern | Decision | Justification |
|---------|----------|---------------|
| Skills improve on reuse | IMPORTED | refine_skill() in skill_service.py |
| Post-mission lessons | IMPORTED | learning_loop.py — structured lesson extraction |
| Patch scope control | ALREADY IMPLEMENTED | protected_paths.py + safe_executor.py |
| Rollback awareness | DEFERRED | Requires git integration in self-improvement |
