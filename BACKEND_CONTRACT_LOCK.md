# BACKEND CONTRACT LOCK 🔒
_Locked: 2026-04-03 — Cycle 18. Backend frozen. All frontend/mobile/product work builds on this._

> This document is the single source of truth for the backend API contract.
> Frontend, mobile, admin, and product work MUST use only what is listed here.
> Do NOT modify backend endpoints without updating this document.

---

## Summary

The Jarvis backend is frozen at Cycle 18. It supports:
- Multi-agent mission execution (submit goal → structured result)
- JWT authentication (single admin + API token)
- Mission persistence (SQLite, survives restart)
- Human approval gate with webhook output
- WebSocket + SSE real-time events
- Model routing (Anthropic / OpenRouter fallback)

---

## 1. AUTH

### Login
```
POST /auth/token
Content-Type: application/x-www-form-urlencoded

username=admin&password=<JARVIS_ADMIN_PASSWORD>
```

Response:
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 3600
}
```

All subsequent requests must include:
```
Authorization: Bearer <jwt>
```

### Token validation (health check path used by mobile autoLogin)
```
GET /api/v2/agents  →  200 = valid, 401 = expired
```

---

## 2. MISSIONS (canonical v3)

### Submit
```
POST /api/v3/missions
Content-Type: application/json

{"goal": "Identify 3 business opportunities for AI consulting in France"}
```

Response:
```json
{
  "data": {
    "mission_id": "abc123",
    "task_id": "abc123",
    "status": "CREATED"
  }
}
```

### List
```
GET /api/v3/missions
```

Response:
```json
{
  "data": {
    "missions": [
      {
        "mission_id": "abc123",
        "status": "COMPLETED",
        "goal": "...",
        "result": "...",
        "agents": ["scout", "builder"],
        "source_system": "meta_orchestrator",
        "plan_summary": "...",
        "error": null
      }
    ]
  }
}
```

### Detail
```
GET /api/v3/missions/{mission_id}
```

Response: same shape as single mission object above, wrapped in `{"data": {...}}`.

---

## 3. APPROVAL / REJECT

> These use the v2 task path — functional and stable. Migration to v3 is deferred.

### Approve
```
POST /api/v2/tasks/{task_id}/approve
```

### Reject
```
POST /api/v2/tasks/{task_id}/reject
Content-Type: application/json

{"note": "Optional reason"}
```

### List pending approvals
```
GET /api/v2/tasks
```

Response contains a list of pending actions with `status: "WAITING_APPROVAL"`.

---

## 4. STATUS VOCABULARY

| Backend value | Meaning | Terminal? |
|---|---|---|
| `CREATED` | Submitted, not yet planned | No |
| `PLANNED` | Plan generated | No |
| `RUNNING` | Agents executing | No |
| `WAITING_APPROVAL` | Paused — needs human gate | No |
| `APPROVED` | Gate passed, resuming | No |
| `COMPLETED` | Success — result available | ✅ Yes |
| `FAILED` | Error — see `error` field | ✅ Yes |
| `REJECTED` | Rejected at approval gate | ✅ Yes |
| `CANCELLED` | Aborted | ✅ Yes |

**Flutter normalization** (in `mission.dart`):
- `COMPLETED` → `DONE` (for `isDone` check)
- `CANCELLED` → `FAILED`

---

## 5. SYSTEM / HEALTH

```
GET /health                        →  {"status": "ok"}  (no auth)
GET /api/v3/system/readiness       →  providers, strategy, model info
GET /api/v2/status                 →  missions by status, mode, totals
```

---

## 6. REAL-TIME

### WebSocket (global events)
```
ws://{host}:{port}/ws/stream?token=<jwt>
```

Event types:
- `mission_update` — status changed
- `mission_done` — terminal success
- `mission_failed` — terminal failure
- `action_pending` — new approval needed
- `task_progress` — execution progress

### SSE (per-mission stream)
```
GET /api/v1/missions/{mission_id}/stream
Accept: text/event-stream
```

---

## 7. DEPRECATED ENDPOINTS (do not use in new code)

| Old path | Replacement |
|---|---|
| `POST /api/mission` | `POST /api/v3/missions` |
| `POST /api/v2/task` | `POST /api/v3/missions` |
| `POST /api/v2/missions/submit` | `POST /api/v3/missions` |
| `GET /api/missions` | `GET /api/v3/missions` |
| `GET /api/v2/missions` | `GET /api/v3/missions` |
| `GET /api/v2/missions/{id}` | `GET /api/v3/missions/{id}` |

---

## 8. ADMIN-ONLY ENDPOINTS (not for mobile users)

These exist and are functional. Admin role = same JWT as standard user (single-user model).
Admin distinction is handled in the frontend, not the backend.

| Category | Prefix | Purpose |
|---|---|---|
| Debug | `/api/v2/debug/*` | Internal state inspection |
| Metrics | `/api/v2/metrics/*` | Performance + cost data |
| Models | `/api/v3/models/*` | Model catalog, scoring |
| Self-improvement | `/api/v2/self-improvement/*` | SI suggestions (gated by JARVIS_ENABLE_SI) |
| Modules | `/api/v3/modules/*` | Agent module management |
| AIOS | `/aios/*` | AI OS dashboard data |

---

## 9. ENVIRONMENT VARIABLES REQUIRED (production)

```bash
ANTHROPIC_API_KEY=sk-ant-...          # or OPENROUTER_API_KEY
JARVIS_SECRET_KEY=$(openssl rand -hex 32)
JARVIS_ADMIN_PASSWORD=<strong_password>
JARVIS_PRODUCTION=1                   # enforces secrets, disables SI
```

Optional:
```bash
QDRANT_HOST=localhost                  # vector memory (degrades gracefully if absent)
REDIS_HOST=localhost                   # rate limiter (falls back to in-memory)
JARVIS_ENABLE_SI=1                     # enable self-improvement (requires docker socket)
```

---

## 10. WHAT IS NOT IN THIS CONTRACT

These exist in the codebase but are NOT part of the frozen product contract:

- WorkflowGraph execution path (alternative to MetaOrchestrator — not live-tested)
- MemoryLayer abstraction (implemented but not wired to agents — see KL-011)
- git binary in runtime image (deferred removal — see KL-010)
- Multi-user auth (single admin only — multi-user is a Track 3 feature)
- Voice, browser automation, venture, economic routes (exist but not product-facing)

---

_This document supersedes `docs/API_CONTRACT_V1.md` for operational purposes._
_The old V1 doc has been corrected but this lock is the authoritative product reference._
