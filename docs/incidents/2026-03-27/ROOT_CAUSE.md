# Root Cause — HTTP 500 Mission Execution (2026-03-27)

## Component
`api/routes/missions.py` — all auth-protected endpoints

## Error
```
AttributeError: 'Header' object has no attribute 'startswith'
  File "/app/api/routes/missions.py", line 62, in submit_task
      _check_auth(x_jarvis_token, authorization)
  File "/app/api/_deps.py", line 33, in _check_auth
      if authorization.startswith("Bearer "):
```

## Root Cause

**Two bugs, same file:**

### Bug 1 — PEP 563 breaks FastAPI Header injection
`missions.py` has `from __future__ import annotations` (PEP 563 deferred annotation evaluation).
With PEP 563, Python stores all type annotations as strings instead of evaluating them at class/function definition time. FastAPI uses `get_type_hints()` to resolve annotations for dependency injection, but when a `Header()` is passed as a default value alongside a stringified annotation, FastAPI's resolver can return the raw `Header` FieldInfo object instead of the resolved string value.

Result: when the Flutter app sends `Authorization: Bearer <token>`, `authorization` received by the endpoint function was the `Header(None)` FieldInfo object, not the string `"Bearer <token>"`. Calling `.startswith()` on a `FieldInfo` object raises `AttributeError`.

**Affected**: all 13 endpoints in missions.py that used `Optional[str] = Header(None)`.

### Bug 2 — submit_mission drops authorization before calling submit_task
`submit_mission` (the `/api/v2/missions/submit` Flutter endpoint) called `submit_task` passing only `x_jarvis_token` but not `authorization`. Since `submit_task` is called as a plain Python function (not via HTTP), FastAPI does not inject headers. The call becomes `_check_auth(None, None)` → raises HTTP 401.

This meant even after fixing Bug 1, a Flutter client using `Authorization: Bearer` would get 401 on the `/missions/submit` route specifically.
