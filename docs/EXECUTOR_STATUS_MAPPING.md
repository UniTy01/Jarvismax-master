# Executor Status Mapping

## Terminal guard in action_executor.py

### Before (legacy only)
```python
if status in ("DONE", "REJECTED", "BLOCKED"):
    return  # skip already-done
```

### After (canonical + legacy)
```python
if status in ("DONE", "REJECTED", "BLOCKED", "COMPLETED", "FAILED", "CANCELLED"):
    return  # skip already-done
```

## Why this matters
Without canonical states in the guard, a mission marked COMPLETED (canonical)
would NOT be recognized as terminal by the executor. This could cause:
- Executor re-processing completed missions
- Duplicate agent invocations
- Infinite completion loops

## Action terminal states (separate from mission)
```python
terminal = {"EXECUTED", "FAILED", "REJECTED"}
```
These are ACTION statuses (not mission statuses) and are correct as-is.

## Legacy → Canonical mapping
| Legacy | Canonical | Used by |
|---|---|---|
| DONE | COMPLETED | mission_system, API |
| REJECTED | CANCELLED | mission_system, API |
| BLOCKED | FAILED | mission_system, API |
