# SMOKE_TEST_RESULT.md — Jarvis Max Mobile
_Cycle 19 — Week 3 device validation_
_APK built: 2026-04-03 — app-debug.apk (~90 MB)_

---

## Server-side bug fixes (2026-04-03)

Three blocking bugs found and fixed during real-device smoke test on VPS `jarvis.jarvismaxapp.co.uk`.

### Bug 1 — Admin auth always 401 Unauthorized ✅ FIXED

| | |
|---|---|
| **Symptom** | Admin panel + Jarvis Health returned 401 even with correct credentials |
| **Root cause** | `api/routes/extensions.py:_require_admin()` read `request.state.token_info` but middleware sets `request.state.user` (never set `token_info`). Also used `"name"`/`"sub"` key instead of `"username"` |
| **Fix** | Changed to `getattr(request.state, "user", None)` + actor key to `"username"` |
| **File** | `api/routes/extensions.py` lines 42–48 |
| **Retest** | `GET /api/v3/extensions/agents` → HTTP 200 ✅ |

### Bug 2 — Modules tabs HTTP 500 ✅ FIXED

| | |
|---|---|
| **Symptom** | Agents / Skills / Connectors / MCP tabs all returned HTTP 500 |
| **Root cause** | `ModuleManager.__init__` calls `mkdir(data/modules)` but `/app` volume-mounted root-owned — `jarvis` user (non-root) can't create `data/` directory |
| **Fix** | `mkdir -p data/modules data/mcp data/skills data/tools && chmod -R 777 data` on VPS |
| **Retest** | All 4 endpoints HTTP 200 ✅ |
| **Permanent fix needed** | Add `data/` dir creation in entrypoint or Dockerfile (workaround survives restart but not full redeploy) |

### Bug 3 — Missions always FAILED, never COMPLETED ✅ FIXED

| | |
|---|---|
| **Symptom** | Every submitted mission reached FAILED status. Error: `all_agents_failed: 0/3 agents produced output` |
| **Root cause (primary)** | OpenRouter API key in `.env` was invalid — returned `401 "User not found"`. LLM factory builds ChatOpenAI object successfully (key passes `_is_valid_key()`), but runtime calls fail. No automatic runtime fallback to Ollama. |
| **Root cause (secondary)** | `learning/learning_loop.py:305` — `(text + " " + context).lower()` raises `TypeError: can only concatenate str (not "dict") to str` because `action_executor.py` passes `context={"action_id":..., "description":...}` (dict) instead of str. Error is caught silently but pollutes logs. |
| **Fix 1** | Updated OpenRouter key to valid `sk-or-v1-e314...` in `/root/Jarvismax/.env` + restarted `jarvis_core` |
| **Fix 2** | `learning/learning_loop.py:305` — changed `+ context` to `+ str(context)` |
| **Files** | `.env` (VPS only), `learning/learning_loop.py` line 305 |
| **Retest** | Mission `724836ee-568` submitted → status `DONE` in <6s ✅ |

---

## Round 3 backend incident fixes (2026-04-04)

Critical backend incident: all v3 missions FAILED on device, admin metrics stuck at 0.

### Bug 7 — Missions always FAILED (OpenRouter key rotation) ✅ FIXED

| | |
|---|---|
| **Symptom** | Every v3 mission reached FAILED status on device. Score advisory UNKNOWN 0.0/10. Health showed `"llm": {"status": "degraded", "error": "Error code: 401 - {'error': {'message': 'User not found.', 'code': 401}}"}` |
| **Root cause** | OpenRouter key `sk-or-v1-e314...` (injected previous session) became invalid. All LLM calls returned 401 → `outcome.success=False` → `MissionStatus.FAILED`. Note: `docker compose restart` does NOT reload env vars — needed `docker compose up -d` to pick up new `.env`. |
| **Fix** | Injected new key `sk-or-v1-706a...` via `sed -i` on VPS `.env`, then `docker compose up -d jarvis` (not just `restart`). |
| **Files** | `/root/Jarvismax/.env` (VPS only) |
| **Verified** | `GET /api/v2/health` → `"llm": {"status": "ok"}` ✅ |
| **Test mission** | `31a39aba-e72` "What is 2+2?" → status `COMPLETED`, result 737 chars ✅ |

### Bug 8 — Admin metrics always show 0 submitted / 0 completed / 0 failed ✅ FIXED

| | |
|---|---|
| **Symptom** | `GET /api/v3/metrics/summary` returns `missions: {submitted: 0, completed: 0, failed: 0}` even after missions execute |
| **Root cause** | The v3 canonical path (MetaOrchestrator via OrchestrationBridge) never called `emit_mission_submitted/completed/failed` from `core.metrics_store`. The `emit_mission_*` calls in `meta_orchestrator.py` go only to `cognitive_events.emitter` (event journal), not to the metrics counters. |
| **Fix** | Added 3 try/except blocks calling `core.metrics_store` emitters: (1) `convergence.py` after successful `bridge_submit()`, (2) `meta_orchestrator.py` after DONE transition, (3) `meta_orchestrator.py` after FAILED transition. Each aliased to avoid name conflict with cognitive events imports. |
| **Files** | `api/routes/convergence.py`, `core/meta_orchestrator.py` |
| **Verified** | After next test mission: `GET /api/v3/metrics/summary` → `missions: {submitted: 2, completed: 2, failed: 0}` ✅ |

---

## Round 2 smoke test fixes (2026-04-03)

Second device smoke pass revealed 3 additional blocking issues.

### Bug 4 — Admin panel + Jarvis Health Unauthorized on device (with static token login) ✅ FIXED

| | |
|---|---|
| **Symptom** | Admin panel and Jarvis Health screens show Unauthorized on device even after valid login |
| **Root cause** | `api/routes/metrics_mobile.py:_auth()` checks `X-Jarvis-Token` header against static API token, then extracts Bearer value and tries `_verify_jwt()`. JWT verification rejects the static API token (it's not a JWT). The `Authorization: Bearer {static_token}` path was never checked against `JARVIS_API_TOKEN`. |
| **Fix** | Added `if t and jwt_token == t: return` before `_verify_jwt()` call — accepts static token sent as Bearer |
| **File** | `api/routes/metrics_mobile.py` lines 42–48 |
| **Retest** | `GET /api/v3/metrics/summary` with `Authorization: Bearer {static_token}` → HTTP 200 ✅ |

### Bug 5 — AI OS overview shows all cards as error / N/A ✅ FIXED (requires APK rebuild)

| | |
|---|---|
| **Symptom** | AI OS dashboard shows every data card as "N/A" / error state |
| **Root cause** | `getAiosStatus()` returns `raw["data"]` (already extracted inner object). But `_buildDashboard()` does `_status?['data']` — double-unwrapping a key that doesn't exist → `data = {}` → all card builders receive `null` → show error |
| **Fix** | Changed `final data = _status?['data'] ?? {};` to `final data = _status ?? {};` |
| **File** | `jarvismax_app/lib/screens/aios_dashboard_screen.dart` line 59 |
| **Retest** | Needs APK rebuild + device install ⏳ |

### Bug 6 — Missions always FAILED (OpenRouter key + str+dict bug) ✅ FIXED

Already documented as Bug 3 above. Confirmed working on server: mission `724836ee-568` → DONE in <6s.

---

## Current smoke status: PARTIAL

| # | Issue | Status |
|---|-------|--------|
| 1 | Valid token login works | ✅ PASS |
| 2 | Server connected + WebSocket active | ✅ PASS |
| 3 | Mission submission works | ✅ PASS |
| 4 | FAILED mission path renders correctly | ✅ PASS |
| 5 | Mission detail screen works | ✅ PASS |
| 6 | Capabilities screen loads | ✅ PASS |
| 7 | Modules health tab loads | ✅ PASS |
| 8 | Admin panel Unauthorized | ✅ FIXED (server-side, live) |
| 9 | Jarvis Health Unauthorized | ✅ FIXED (server-side, live) |
| 10 | AI OS overview broken state | ✅ FIXED in code, needs APK rebuild |
| 11 | COMPLETED mission path — server | ✅ CONFIRMED (test mission `31a39aba-e72` → COMPLETED, result 737 chars) |
| 12 | Admin metrics showing counts | ✅ FIXED (submitted/completed/failed now increment) |
| 13 | COMPLETED mission path on device | ⏳ Not yet proven on real device (needs APK rebuild with new key) |
| 14 | Copy-result action | ⏳ Not yet proven (needs COMPLETED mission on device) |
| 15 | Approval/reject flow | ⏳ Not yet proven (no pending approvals currently) |

**Overall: PARTIAL — core mission execution confirmed working server-side. LLM healthy. Metrics syncing. APK rebuild required for device validation.**

---

## Build status

| Step | Result |
|------|--------|
| `flutter build apk --debug` | ✅ SUCCESS |
| APK path | `jarvismax_app/build/app/outputs/flutter-apk/app-debug.apk` |
| APK size | ~90 MB (debug) |
| Compilation errors | None |
| gradle.properties fix | Removed Linux-only `org.gradle.java.home` — now cross-platform |

---

## Device test checklist

> Fill in results after installing the APK on a real Android device or emulator.
> Server target: `https://jarvis.jarvismaxapp.co.uk` (production, default)
> Or use Tailscale `100.109.1.124:8000` for local VPN access.

### 1. Auth

| Test | Expected | Result |
|------|----------|--------|
| App opens → Login screen shows | French UI: "Entrez votre token d'accès…" | ⬜ |
| Enter invalid token → error | "Token invalide. Vérifiez et réessayez." | ⬜ |
| Enter valid token → Home screen | Tab bar: Accueil / Missions / Approbations / Historique / Paramètres | ⬜ |
| "Se souvenir de moi" checked → reopen app | Auto-login, skips login screen | ⬜ |

### 2. Home screen — task type selector

| Test | Expected | Result |
|------|----------|--------|
| Chip bar visible below greeting | 17 chips: Libre + 16 business types | ⬜ |
| Tap "Recherche marché" | Chip highlights blue, composer shows badge "Recherche marché" | ⬜ |
| Tap active chip again | Chip deselects, badge disappears | ⬜ |
| System status shown | "En ligne" / "Hors ligne" with correct color | ⬜ |
| Recent missions list renders | Shows last missions with status pills | ⬜ |

### 3. Mission submission

| Test | Expected | Result |
|------|----------|--------|
| Select "Recherche marché" + enter "Marché des outils IA en France" + tap Lancer | `[market_research] Marché des outils IA en France` sent to backend | ⬜ |
| Mission appears in list with status "En cours" | Spinner / pending state visible | ⬜ |
| Mission reaches COMPLETED | Status pill turns green "Terminé" | ⬜ |
| "Libre" mode: plain text goal sent without prefix | Goal text not prefixed with `[...]` | ⬜ |

### 4. Mission detail + result export

| Test | Expected | Result |
|------|----------|--------|
| Tap completed mission → detail screen | Full result text visible | ⬜ |
| Tap "Copier" button next to "Réponse de Jarvis" | Snackbar "Résultat copié" — clipboard contains result | ⬜ |
| Long result renders without overflow | Scrollable, no truncation | ⬜ |

### 5. Approbations tab

| Test | Expected | Result |
|------|----------|--------|
| Submit a mission that triggers approval gate | Appears in Approbations tab as "EN ATTENTE" | ⬜ |
| Tap "Approuver" | Snackbar "Approuvé", card moves to resolved | ⬜ |
| Tap "Refuser" | Snackbar "Refusé", card moves to resolved | ⬜ |
| No pending approvals → empty state | "Tout est bon" message | ⬜ |

### 6. Paramètres → Panneau Admin

| Test | Expected | Result |
|------|----------|--------|
| Tap Paramètres tab | French labels: Serveur / WebSocket / Adresse | ⬜ |
| Tap "Panneau Admin" | Admin panel loads | ⬜ |
| Health banner shows | Green = "Système OK", amber = "Dégradé", red = "Critique" | ⬜ |
| Mission stats show | Soumises / Réussies / Échouées counts | ⬜ |
| Cost today shows | USD cost with color coding | ⬜ |
| Refresh button works | Data reloads without error | ⬜ |

### 7. WebSocket real-time updates

| Test | Expected | Result |
|------|----------|--------|
| Submit mission → stay on Home | Mission list updates automatically when status changes | ⬜ |
| WebSocket status in Paramètres | "Actif" (green) when connected | ⬜ |

---

## Issues found

> Record any bugs, unexpected behavior, or UX friction here.

| # | Screen | Description | Severity |
|---|--------|-------------|----------|
| — | — | — | — |

---

## Sign-off

| | |
|---|---|
| Tested by | |
| Device | |
| Android version | |
| Server | production / tailscale / local |
| Date | |
| Overall result | ⬜ PASS  ⬜ FAIL  ⬜ PARTIAL |

---

_Next after passing: first internal user session (founder feedback)._
