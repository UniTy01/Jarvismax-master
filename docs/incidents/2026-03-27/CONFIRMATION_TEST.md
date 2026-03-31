# Confirmation Test — HTTP 500 Mission Execution (2026-03-27)

## Test Command
```bash
curl -s -w "\nHTTP_STATUS:%{http_code}" \
  -X POST http://localhost:8000/api/v2/missions/submit \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer B7Ev_6fVfWXx-9JhtdL1P-422sWF4Eqb7n2nI-ktdLE" \
  -d '{"goal": "Analyse le marche belge et propose 3 services IA simples vendables aux PME locales"}'
```

## Output
```json
{"ok":true,"data":{"task_id":"882c392b-99f","mission_id":"882c392b-99f","status":"PENDING_VALIDATION","mode":"auto","created_at":1774627117.5658076}}
HTTP_STATUS:201
```

## Evidence
- **HTTP 201** — endpoint accepted the request (was HTTP 500 before fix)
- **mission_id**: `882c392b-99f`
- **status**: `PENDING_VALIDATION` — mission is queued for execution
- **Authorization: Bearer** header correctly resolved and validated (no 401, no AttributeError)

## Before Fix (from live logs)
```
AttributeError: 'Header' object has no attribute 'startswith'
File "/app/api/_deps.py", line 33, in _check_auth
    if authorization.startswith("Bearer "):
```
