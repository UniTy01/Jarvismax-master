# MOBILE_CONTRACT.md — Jarvis Max
_Last updated: 2026-04-03 — Cycle 19: approval migrated to v3, APK built, Cycle 18 mobile layer documented_

Mobile app: Flutter (`jarvismax_app/`).
Backend: FastAPI (`api/`).

---

## Current Mobile/Backend Path

The mobile app uses **canonical v3 endpoints** for all operations as of Cycle 19.

| Operation | Mobile calls | Backend handler |
|-----------|-------------|----------------|
| Submit mission | `POST /api/v3/missions` ✅ | Canonical v3 → MetaOrchestrator |
| List missions | `GET /api/v3/missions` ✅ | Canonical v3 → MetaOrchestrator |
| Mission detail | `GET /api/v3/missions/{id}` ✅ | Canonical v3 → MetaOrchestrator |
| Auth/login | `POST /auth/token` | JWT auth ✅ |
| Health | `GET /health` | API health ✅ |
| Readiness | `GET /api/v3/system/readiness` | Canonical v3 ✅ |
| Metrics | `GET /api/v3/metrics/summary` | Canonical v3 ✅ |
| Approve action | `POST /api/v3/missions/{id}/approve` ✅ | Canonical v3 → bridge (3-step: legacy + MO + SQLite) |
| Reject action | `POST /api/v3/missions/{id}/reject` ✅ | Canonical v3 → bridge (3-step: legacy + MO + SQLite) |

The **canonical proven path** (`/api/v3/missions`) is now used for all mobile operations, backend tests, and `verify_boot.sh`.

**Approval path migration (Cycle 19):** `approveAction()` and `rejectAction()` migrated from `/api/v2/tasks/{id}/approve|reject` to `/api/v3/missions/{id}/approve|reject`. The v3 path calls `bridge.approve_mission()` which does a proper 3-step sequence: legacy MissionSystem + MetaOrchestrator.resolve_approval() + canonical SQLite persist. The v2 path remains valid as a fallback.

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

### Device smoke test pending
- APK debug build complete (Cycle 19): `app-debug.apk` ~90 MB, zero compile errors
- Device test requires: Android device or emulator + running Jarvis server
- See `SMOKE_TEST_RESULT.md` for the full test checklist (7 sections, 30+ test cases)

### Cycle 18 mobile layer (fully shipped)
- French-first UI: all tab labels, screens, buttons, errors in French ✅
- Task type selector: 17 chips (Libre + 16 business skills), prefixes goal with `[skill_key]` ✅
- Admin panel (`AdminPanelScreen`): hits `/api/v3/metrics/summary`, shows health, stats, cost, alerts ✅
- Result copy button in mission detail: copies result to clipboard with "Résultat copié" snackbar ✅

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

## Device Smoke Test (APK built — Cycle 19)

**APK status:** Built and ready — `jarvismax_app/build/app/outputs/flutter-apk/app-debug.apk` (~90 MB).
See `SMOKE_TEST_RESULT.md` for the complete 7-section checklist.

**Setup:**
```bash
# 1. Start server (production or local)
# Production: https://jarvis.jarvismaxapp.co.uk (default in app)
# Local: set host + port in Paramètres → Serveur

# 2. Install APK
adb install jarvismax_app/build/app/outputs/flutter-apk/app-debug.apk
# Or transfer directly to device
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
