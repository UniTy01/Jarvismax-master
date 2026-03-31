# Mission Status Invariant

## Terminal States — LOCKED ✅

### Canonical (must NEVER be removed)
- `COMPLETED` — mission succeeded
- `FAILED` — mission failed (error, timeout, blocked)
- `CANCELLED` — mission rejected by user or system

### Legacy (must remain for backward compatibility)
- `DONE` → maps to COMPLETED
- `REJECTED` → maps to CANCELLED
- `BLOCKED` → maps to FAILED

### Invariant enforcement
- `test_terminal_statuses_cover_all`: asserts all 6 states present
- `test_terminal_states_are_stable`: asserts minimum set never shrinks
- Both fail loudly with CRITICAL message if violated

### Where terminal states matter
- `_TERMINAL_STATUSES` in `api/routes/mission_control.py` — SSE stream termination
- `_maybe_complete_mission()` in `core/action_executor.py` — skip already-done missions
- `core/mission_system.py` — mission lifecycle transitions
