# MOBILE_CONTRACT.md — Jarvis Max
_Last updated: 2026-04-01 — Cycle 12: static audit complete, device test pending_

Mobile app: Flutter (`jarvismax_app/`).
Backend: FastAPI (`api/`).

---

## Current Mobile/Backend Path

The mobile app uses **canonical v3 endpoints** for mission operations as of 2026-04-01.

| Operation | Mobile calls | Backend handler |
|-----------|-------------|----------------|
| Submit mission | `POST /api/v3/missions` ✅ | Canonical v3 → MetaOrchestrator |
| List missions | `GET /api/v3/missions` ✅ | Canonical v3 → MetaOrchestrator |
| Mission detail | `GET /api/v3/missions/{id}` ✅ | Canonical v3 → MetaOrchestrator |
| Auth/login | `POST /auth/token` | JWT auth ✅ |
| Health | `GET /health` | API health ✅ |
| Readiness | `GET /api/v3/system/readiness` | Canonical v3 ✅ |
| Metrics | `GET /api/v3/metrics/...` | Canonical v3 ✅ |
| Approve action | `POST /api/v2/tasks/{id}/approve` | Legacy v2 (still valid) |
| Reject action | `POST /api/v2/tasks/{id}/reject` | Legacy v2 (still valid) |

The **canonical proven path** (`/api/v3/missions`) is now used by the mobile app, backend tests, and `verify_boot.sh`.

---

## Fixed Contract Mismatches (2026-04-01)

### Status vocabulary mismatch — FIXED in `mission.dart`
- **Root cause:** Canonical v3 returns `"COMPLETED"`, but mobile `isDone` checked `status == 'DONE'`
- **Fix:** Added `_normalizeStatus()` in `Mission.fromJson()`:
  - `"COMPLETED"` → normalized to `"DONE"`
  - `"CANCELLED"` → normalized to `"FAILED"`
- **Impact:** If mobile ever receives v3 responses, completed missions now display correctly

### Field name aliasing — FIXED in `mission.dart`
- `userInput`: reads `j['user_input'] ?? j['goal']` (v3 uses `goal`)
- `finalOutput`: reads `j['final_output'] ?? j['result'] ?? j['output']` (v3 uses `result`)
- `selectedAgents`: reads `j['agents_selected'] ?? j['agents']` (v3 uses `agents`)
- `finalOutputSource`: reads `j['final_output_source'] ?? j['source_system']`

---

## Remaining Gaps

### Approval/Reject endpoints (non-blocking)
- `approveAction()` and `rejectAction()` still call `/api/v2/tasks/$id/approve|reject`
- These legacy endpoints remain functional and are not on the ghost-DONE path
- v3 equivalents exist (`/api/v3/missions/$id/approve|reject`) but migration is low priority

### Device smoke test pending
- Mobile v3 migration has not been device-tested yet (requires live server + physical device or emulator)
- See checklist below

---

## Static Audit Results (Cycle 12 — 2026-04-01)

### Field contract verification (no device needed)

| API field (`to_dict()`) | app reads (`fromJson`) | Status |
|------------------------|------------------------|--------|
| `mission_id` | `j['id'] ?? j['mission_id']` | ✅ correct |
| `goal` | `j['user_input'] ?? j['goal']` | ✅ correct |
| `status` (e.g. `'COMPLETED'`) | `_normalizeStatus(j['status'])` → `'DONE'` | ✅ normalized |
| `result` | `j['final_output'] ?? j['result'] ?? j['output']` | ✅ correct |
| `agents` (list) | `j['agents_selected'] ?? j['agents']` | ✅ correct |
| `source_system` | `j['final_output_source'] ?? j['source_system']` | ✅ correct |
| `plan_summary` | `j['plan_summary']` | ✅ correct |
| `error` | `j['error']` | ✅ present in to_dict() |

### UI logic verification

| Check | Result |
|-------|--------|
| `isDone` checks `status == 'DONE'` after normalization | ✅ correct |
| `isFailed` checks `status == 'FAILED'` | ✅ correct |
| `isTerminal` covers DONE/FAILED/REJECTED | ✅ correct |
| `finalOutput` displays `result` from v3 response | ✅ correct |
| Approve/reject path: `/api/v2/tasks/$id/approve|reject` still exists in API | ✅ valid |

### No remaining schema drift found. All contract mismatches resolved.

---

## Device Smoke Test Checklist (one remaining external step)

Run on Android emulator or physical device against a live backend:

**Setup:**
```bash
# 1. Start server
export ANTHROPIC_API_KEY=sk-ant-...
export QDRANT_HOST=localhost QDRANT_PORT=6333
python main.py &

# 2. Get server IP (for Android emulator, use 10.0.2.2)
# 3. Build app
cd jarvismax_app
flutter run --dart-define=API_BASE=http://10.0.2.2:8000
```

**Test sequence (in order):**
- [ ] **Login**: Enter admin credentials → JWT token stored, main screen loads
- [ ] **Submit mission**: Type "Return only the number 42" → mission_id returned, status card appears
- [ ] **Poll RUNNING**: Status transitions from CREATED → PLANNED → RUNNING shown
- [ ] **Show COMPLETED**: Status card shows "DONE", result content visible (not empty, not ghost)
- [ ] **Show FAILED** (with invalid key): `ANTHROPIC_API_KEY=sk-invalid` → app shows failure, not success
- [ ] **Readiness screen**: Health screen shows `providers=['anthropic'] strategy=anthropic` (not just "ok")
- [ ] **Persistence**: Kill server, restart, reopen app → previous COMPLETED mission still listed
- [ ] **Approve/reject**: Trigger a MEDIUM risk mission → approval card appears → approve → continues

**Pass criteria:** All 8 steps pass with no ghost-success and correct status display.

---

## Mobile v3 Migration — COMPLETE (2026-04-01)

All three critical endpoint migrations were applied to `api_service.dart`:

1. ✅ `submitMission()`: `POST /api/mission` `{'input':...}` → `POST /api/v3/missions` `{'goal':...}`
2. ✅ `_loadMissions()`: `GET /api/v2/missions` → `GET /api/v3/missions`
3. ✅ `fetchMissionDetail()`: `GET /api/v2/missions/$id` → `GET /api/v3/missions/$id`
4. ✅ `mission.dart` model handles v3 field names (`goal`, `result`, `COMPLETED`) via aliases + `_normalizeStatus()`

**What this unlocks for mobile users:**
- Ghost-DONE fix applies: invalid LLM key → app shows FAILED (not ghost-success)
- Mission persistence applies: missions survive server restart, shown correctly on next app open
- Model catalog + scoring applies: best available model selected per mission
- Readiness probe observable: health screen shows active LLM provider + strategy
