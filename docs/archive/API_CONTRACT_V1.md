# API Contract — FROZEN 🔒
_Last updated: 2026-04-03 — Cycle 18 post-wave: contract realigned with actual runtime._

> This contract is frozen. Changes require a version discussion.
> The Flutter mobile app uses the canonical v3 endpoints listed below.
> Previous v1 doc was incorrect — `/api/v3/*` are canonical, NOT internal.

---

## Authentication

All endpoints (except `/health`) require one of:
- `Authorization: Bearer <token>` header
- `X-Jarvis-Token: <token>` header

Token obtained via `POST /auth/token` (form-encoded).

In `ENV=production`, startup FAILS if `JARVIS_SECRET_KEY` and `JARVIS_ADMIN_PASSWORD` are absent.

---

## CANONICAL ENDPOINTS (active, mobile-facing)

These are the ONLY endpoints the Flutter app and external integrations should use.

### Auth

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/token` | Login → returns `access_token` (JWT) |

### Missions

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v3/missions` | Submit mission — body: `{"goal": "..."}` |
| GET | `/api/v3/missions` | List all missions |
| GET | `/api/v3/missions/{id}` | Mission detail |

**Submit response shape:**
```json
{
  "data": {
    "mission_id": "abc123",
    "task_id": "abc123",
    "status": "CREATED"
  }
}
```

**Mission object shape:**
```json
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
```

### Approval / Reject (functional legacy — v2 path, still active)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v2/tasks/{id}/approve` | Approve a pending action |
| POST | `/api/v2/tasks/{id}/reject` | Reject a pending action — body: `{"note": "..."}` |

> These are the working paths used by the Flutter app. v3 equivalents are not yet exposed.

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check (no auth required) |
| GET | `/api/v3/system/readiness` | Full readiness probe (providers, strategy) |
| GET | `/api/v2/status` | Runtime stats (missions by status, mode) |

### Real-time

| Protocol | Endpoint | Description |
|----------|----------|-------------|
| WebSocket | `/ws/stream?token=<jwt>` | Live mission events |
| SSE | `/api/v1/missions/{id}/stream` | Per-mission event stream |

---

## STATUS VOCABULARY (canonical)

| Backend value | Meaning | Mobile display |
|---------------|---------|----------------|
| `CREATED` | Just submitted | Loading |
| `PLANNED` | Plan generated | In progress |
| `RUNNING` | Agents executing | In progress |
| `COMPLETED` | Success | DONE (normalized) |
| `FAILED` | Error | FAILED |
| `WAITING_APPROVAL` | Needs human gate | Approval required |
| `APPROVED` | Gate passed | In progress |
| `REJECTED` | Gate rejected | REJECTED |
| `CANCELLED` | Aborted | FAILED (normalized) |

**Flutter normalization** (in `mission.dart`):
- `COMPLETED` → `DONE`
- `CANCELLED` → `FAILED`

---

## DEPRECATED ENDPOINTS (exist, do not use in new code)

| Deprecated | Canonical replacement |
|---|---|
| `POST /api/mission` | `POST /api/v3/missions` |
| `GET /api/missions` | `GET /api/v3/missions` |
| `POST /api/v2/task` | `POST /api/v3/missions` |
| `GET /api/v2/missions` | `GET /api/v3/missions` |
| `GET /api/v2/missions/{id}` | `GET /api/v3/missions/{id}` |
| `POST /api/v2/missions/submit` | `POST /api/v3/missions` |

---

## INTERNAL / ADMIN ENDPOINTS

These serve admin/debug purposes. Not part of the mobile contract.

| Category | Prefix |
|---|---|
| Admin debug | `/api/v2/debug/*` |
| Metrics | `/api/v2/metrics/*` |
| Logs | `/api/v2/logs/*` |
| Learning | `/api/v2/learning/*` |
| Skills | `/api/v2/skills/*` |
| Self-improvement | `/api/v2/self-improvement/*` |
| Models | `/api/v3/models/*` |
| Modules | `/api/v3/modules/*` |
| AIOS dashboard | `/aios/*` |

---

## VERSIONING POLICY

- Bug fixes: allowed in-place
- New optional response fields: allowed
- Breaking field renames: NOT ALLOWED, requires migration path
- Endpoint removal: NOT ALLOWED without explicit deprecation + 1 cycle notice
