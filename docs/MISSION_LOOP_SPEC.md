# Mission Loop Specification v1

## Canonical Flow

```
1. INPUT          → User submits goal via API
2. CLASSIFY       → mission_classifier: type, urgency, complexity, risk
3. ASSEMBLE       → context_assembler: skills + memory + failures + health
4. PLAN           → Approach selection + context injection into goal
5. APPROVAL GATE  → If risk >= medium: pause for human approval
6. EXECUTE        → execution_supervisor → delegate.run(enriched_goal)
7. SUPERVISE      → Retry transient / abort permanent / escalate risky
8. RESULT         → Structured outcome (success/error/duration/trace)
9. WRITEBACK      → store_outcome() or store_failure() via MemoryFacade
10. LEARN         → SkillService.record_outcome() (maybe create skill)
11. TRACE         → Full decision trace saved to workspace/traces/
```

## Entry Point

`MetaOrchestrator.run_mission(goal, mode, mission_id, callback, use_budget)`

## State Machine

```
CREATED → PLANNED → RUNNING → REVIEW → DONE
                                     ↘ FAILED
                           (or RUNNING + awaiting_approval)
```

## Context Assembly (before execution)

| Source | Method | Purpose |
|--------|--------|---------|
| Skills | SkillService.retrieve_for_mission() | Prior procedures |
| Memory | MemoryFacade.search() | Relevant knowledge |
| Failures | MemoryFacade.search("failure") | Avoid repeating |
| Health | MonitoringAgent.health_sync() | System readiness |

Assembled context is:
1. Stored in `ctx.metadata["context"]`
2. Formatted via `planning_prompt_context()`
3. Injected into the goal sent to the execution delegate

## Execution Supervision

| Error Type | Action | Max Retries |
|------------|--------|-------------|
| Timeout | Retry with backoff | 2 |
| Connection error | Retry | 2 |
| Rate limit | Retry | 2 |
| LLM error | Retry once | 1 |
| Permission denied | Abort | 0 |
| Invalid input | Abort | 0 |
| High risk + any error | Escalate | 0 |

## Memory Writeback

| Outcome | Method | Content Type |
|---------|--------|-------------|
| Success | store_outcome() | mission_outcome |
| Failure | store_failure() | failure |

## Skill Learning

After DONE: `SkillService.record_outcome()` evaluates:
- Result length >= 80 chars
- Confidence >= 0.4
- Not a duplicate (cosine < 0.75)
- Creates or merges skill if warranted

## Decision Trace

Every mission produces `workspace/traces/{mission_id}.jsonl` with entries:
- classify, retrieve, plan, execute, complete, store

## Approval Gate

| Risk | Behavior |
|------|----------|
| low | Execute directly |
| medium+ | Submit to approval_queue → pause |
| Approved | Resume execution |
| Denied | Abort with error |

## Contracts

- Input: goal (str), mode (str)
- Output: MissionContext with status, result, error, metadata, decision_trace
- Execution: ExecutionOutcome with success, retries, duration_ms, decision_trace
- Skill: Skill dataclass with confidence, use_count, steps
