# Approval Gate Report

## Where Approval Is Enforced

```
MetaOrchestrator.run_mission()
    → classify → needs_approval flag
    → execution_supervisor.supervise()
        → _needs_approval(risk_level, requires_approval)
        → _request_approval() → core/approval_queue
```

Single enforcement point: `execution_supervisor.supervise()`.
No side channels. No bypass.

## How Execution Pauses

1. `_needs_approval()` checks: risk ∈ {medium, high, critical} OR explicit flag
2. `_request_approval()` submits to `core/approval_queue`
3. Queue returns `{approved: false, pending: true, item_id: "..."}`
4. Supervisor returns `ExecutionOutcome(error_class="awaiting_approval")`
5. MetaOrchestrator keeps mission in RUNNING state with `approval_item_id` in metadata
6. Decision trace records the approval gate event

## How Execution Resumes

1. Human approves via API: `POST /approval/approve/{item_id}`
2. Flutter app or API client re-triggers mission execution
3. On retry, `is_approved(item_id)` returns true
4. Execution proceeds normally

## Risk Level Behavior

| Risk | Approval | Behavior |
|------|----------|----------|
| low | Not required | Direct execution |
| low + explicit flag | Required (elevated to medium) | Pauses for approval |
| medium | Required | Pauses for approval |
| high | Required | Pauses for approval, fail-closed on errors |
| critical | Required | Pauses for approval, fail-closed on errors |

## Auto-Approval

Low-risk actions (RiskLevel.READ, WRITE_LOW) are auto-approved by the queue.
Medium+ risk actions require explicit human approval.

## Fail Behavior

- Approval gate error + low risk → fail-open (execute anyway)
- Approval gate error + high/critical risk → fail-closed (abort)

## Decision Trace

Every approval decision is recorded:
```json
{"step": "approval_gate", "risk_level": "high", "approved": false, "pending": true}
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /approval/pending | List pending approvals |
| POST | /approval/approve/{id} | Approve an action |
| POST | /approval/reject/{id} | Reject an action |
| POST | /api/v2/tasks/{id}/approve | Flutter-compatible approve |
| POST | /api/v2/tasks/{id}/reject | Flutter-compatible reject |

## Tests: 21 pass
- 6 approval decision logic tests
- 5 approval queue CRUD tests
- 5 supervisor gate integration tests
- 3 classifier flag tests
- 2 MetaOrchestrator source verification tests
