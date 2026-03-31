# Production Auth Policy

## Status: ENFORCED 🔒

---

## Rules

### Startup Checks (core/security/startup_guard.py)

In production mode (ENV=production):
1. **JARVIS_API_TOKEN** must exist and be ≥16 characters
2. **JARVIS_SECRET_KEY** must exist (for JWT signing)
3. Token must NOT be a default/test value
4. Startup FAILS HARD if any check fails

In development mode:
- Checks run but only emit warnings
- Auth is disabled if token is not set (fail-open for dev convenience)

### HTTP Auth (api/_deps.py)

- Dual header support: `X-Jarvis-Token` + `Authorization: Bearer`
- Per-endpoint or per-router `Depends(_auth)`
- 401 Unauthorized on mismatch

### Open Endpoints (no auth)

Only these endpoints may be accessed without auth:
- `GET /api/health` — health check
- `GET /api/v2/health` — health check alias
- `GET /cockpit` — dashboard HTML (read-only)

### WebSocket Auth

- Token via query parameter: `?token=<jwt>`
- Must match JARVIS_SECRET_KEY for JWT validation
- **Known issue**: Flutter WebSocket reads from SharedPreferences, ApiService stores in FlutterSecureStorage — alignment needed

---

## Auth Coverage by Router

| Router | Auth Method | Status |
|--------|-------------|--------|
| mission_control | Router-level `Depends(_auth)` | ✅ |
| missions | Per-endpoint `_check_auth` | ✅ |
| monitoring | Per-endpoint `_check_auth` | ✅ |
| admin | Per-endpoint `_check_auth` | ✅ |
| system | Per-endpoint `_check_auth` | ✅ |
| memory | Per-endpoint `_check_auth` | ✅ |
| trace | Router-level `Depends(_auth)` | ✅ |
| approval | Router-level `Depends(_auth)` | ✅ |
| cockpit | Router-level `Depends(_auth)` | ✅ |
| dashboard | Router-level `Depends(_auth)` | ✅ |
| objectives | Router-level `Depends(_auth)` | ✅ |
| performance | Router-level `Depends(_auth)` | ✅ |
| self_improvement | Router-level `Depends(_auth)` | ✅ |
| skills | Router-level `Depends(_auth)` | ✅ |
| agent_builder | **Needs auth enforcement** | ⚠️ |
| browser | **Needs auth enforcement** | ⚠️ |
| convergence | **Needs auth enforcement** | ⚠️ |
| learning | **Needs auth enforcement** | ⚠️ |
| multimodal | **Needs auth enforcement** | ⚠️ |
| rag | **Needs auth enforcement** | ⚠️ |
| voice | **Needs auth enforcement** | ⚠️ |

---

## No Fail-Open in Production

The `_check_auth()` function currently returns early if `JARVIS_API_TOKEN` is empty.
The startup guard prevents this scenario in production by refusing to start.
This is defense-in-depth: the guard catches it at startup, auth catches it at runtime.
