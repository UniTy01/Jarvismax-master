# Canonical Action Model — ENFORCED 🔒

## Status: OFFICIAL LIFECYCLE

`core/actions/action_model.py` is the single source of truth for execution lifecycle.

## Canonical Statuses

```
PENDING → APPROVAL_REQUIRED → APPROVED → RUNNING → COMPLETED
                                                  → FAILED
                                                  → CANCELLED
```

| Status | Meaning | Terminal |
|--------|---------|---------|
| PENDING | Created, awaiting processing | No |
| APPROVAL_REQUIRED | Needs human approval | No |
| APPROVED | Approved, awaiting execution | No |
| RUNNING | Currently executing | No |
| COMPLETED | Finished successfully | **Yes** |
| FAILED | Execution failed | **Yes** |
| CANCELLED | Cancelled or rejected | **Yes** |

## Terminal State Invariant

Once an action reaches COMPLETED, FAILED, or CANCELLED, NO further state transition is allowed. This is enforced in code:

```python
def complete(self, ...):
    if self.status in ("RUNNING", "APPROVED", "PENDING"):  # guard
        self.status = "COMPLETED"

def fail(self, ...):
    if self.status not in ("COMPLETED", "CANCELLED"):  # guard
        self.status = "FAILED"
```

## Legacy Queue Mapping

### action_queue.py → CanonicalAction

| action_queue.ActionStatus | CanonicalAction.status |
|---------------------------|----------------------|
| PENDING | PENDING |
| APPROVED | APPROVED |
| REJECTED | CANCELLED |
| EXECUTED | COMPLETED |
| FAILED | FAILED |

### task_queue.py → CanonicalAction

| task_queue.TaskState | CanonicalAction.status |
|---------------------|----------------------|
| pending | PENDING |
| running | RUNNING |
| done | COMPLETED |
| failed | FAILED |
| cancelled | CANCELLED |

## Legacy Module Status

| Module | Status | Replacement |
|--------|--------|-------------|
| core/action_queue.py | **DEPRECATED** | CanonicalAction |
| core/task_queue.py | **DEPRECATED** | CanonicalAction |
| core/approval_queue.py | **DEPRECATED** | CanonicalAction.request_approval() |

These modules remain for backward compatibility with existing integrations.
**New code MUST use CanonicalAction only.**

## Event Emission

Every state transition emits an event via EventCollector:

| Transition | Event |
|-----------|-------|
| → APPROVAL_REQUIRED | approval_requested |
| → APPROVED | action_approved |
| → RUNNING | action_started |
| → COMPLETED | action_completed |
| → FAILED | action_failed |
| → CANCELLED | action_cancelled |

## Facade

`get_canonical_actions(mission_id)` merges both legacy queues into a unified canonical view.

## Test Coverage

14 tests in `test_action_model.py`:
- Lifecycle happy path, approval flow, failure, cancellation
- Terminal state enforcement
- Legacy mapping (both queues)
- Event emission verification
