# Patch Note — HTTP 500 Mission Execution (2026-03-27)

## Commits
- `861735d` — fix: missions.py — use Annotated[str, Header()] to fix PEP 563 Header injection
- `1d60c51` — fix: missions.py — pass authorization to submit_task in submit_mission

## Files Touched
- `api/routes/missions.py`

## Patch 1 — Fix Header injection (commit 861735d)

**Changed**: `from typing import Any, Optional` → `from typing import Annotated, Any, Optional`

**Changed** (×13, replace_all): all `Optional[str] = Header(None)` → `Annotated[Optional[str], Header()] = None`

The `Annotated` form places the `Header()` marker inside the type annotation itself rather than as a default value. FastAPI explicitly supports `Annotated` with PEP 563 — it extracts the `Header()` from the annotation metadata before string-evaluation occurs, so the resolved string value is always injected correctly.

```python
# Before (broken with from __future__ import annotations):
x_jarvis_token: Optional[str] = Header(None), authorization: Optional[str] = Header(None)

# After (PEP 563 compatible):
x_jarvis_token: Annotated[Optional[str], Header()] = None, authorization: Annotated[Optional[str], Header()] = None
```

## Patch 2 — Pass authorization through submit_mission (commit 1d60c51)

**Changed**: In `submit_mission`, the call to `submit_task` now passes both auth parameters.

```python
# Before:
return await submit_task(task_req, background_tasks, x_jarvis_token)

# After:
return await submit_task(task_req, background_tasks, x_jarvis_token, authorization)
```

This ensures `_check_auth` inside `submit_task` receives the actual token when called internally from `submit_mission`.

## Why minimal
No restructuring. No new abstractions. Two targeted one-liner changes (plus the import) fixing the exact failure path.
